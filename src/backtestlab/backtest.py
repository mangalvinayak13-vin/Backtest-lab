from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version

from backtestlab.benchmark import alignBenchmark
from backtestlab.diagnostics import buildWarnings
from backtestlab.engine import EngineResult, runEngine
from backtestlab.metrics import Metrics, curveMetrics, dailyReturns, runMetrics
from backtestlab.montecarlo import MonteCarloResult, runMonteCarlo
from backtestlab.presets import DEFAULT
from backtestlab.prices import PriceData
from backtestlab.pricewarnings import indexDays
from backtestlab.runwarning import RunWarning
from backtestlab.sensitivity import SensitivityRow, runSensitivity
from backtestlab.settings import Settings
from backtestlab.strategies import BuyAndHold
from backtestlab.strategy import Strategy
from backtestlab.trades import RoundTrip, buildRoundTrips
from backtestlab.window import Window, chooseWindow


# one run of the engine with its round trips and its numbers
@dataclass(frozen=True)
class RunSummary:
    engine: EngineResult
    trips: tuple[RoundTrip, ...]
    metrics: Metrics

    # the equity at each close, as plain floats
    def equity(self) -> list[float]:
        return [float(value) for value in self.engine.bars["equity"].values]


# a market index lined up with the test, with its numbers
@dataclass(frozen=True)
class BenchmarkSummary:
    label: str
    values: tuple[float, ...]
    metrics: Metrics


# everything the report and the results file need
@dataclass(frozen=True)
class BacktestResult:
    prices: PriceData
    strategy: Strategy
    settings: Settings
    window: Window
    days: tuple[datetime, ...]
    strategyRun: RunSummary
    holdRun: RunSummary
    benchmark: BenchmarkSummary | None
    monteCarlo: MonteCarloResult | None
    sensitivity: tuple[SensitivityRow, ...]
    warnings: tuple[RunWarning, ...]
    version: str


# run one strategy through the engine and work out its round trips and numbers
def summariseRun(
    prices: PriceData, strategy: Strategy, settings: Settings, window: Window
) -> RunSummary:
    engine = runEngine(prices, strategy, settings, window)
    lastDay = indexDays(engine.bars)[-1]
    lastClose = float(prices.frame["close"].iloc[window.last])
    trips = buildRoundTrips(engine.fills, lastDay, lastClose)
    return RunSummary(engine, tuple(trips), runMetrics(engine, trips, settings))


# line the index up with the test dates, giving its summary or the reason it was left out
def compareBenchmark(
    benchmark: PriceData | None, days: list[datetime], settings: Settings
) -> tuple[BenchmarkSummary | None, RunWarning | None]:
    if benchmark is None:
        return None, None
    label = settings.benchmarkLabel or benchmark.source
    aligned = alignBenchmark(benchmark, days, settings.startingCash, label)
    if aligned.warning is not None:
        return None, aligned.warning
    metrics = curveMetrics(days, list(aligned.values), settings)
    return BenchmarkSummary(label, aligned.values, metrics), None


# check everything, run the strategy and buy and hold over the same window, and add the checks
def runBacktest(
    prices: PriceData,
    strategy: Strategy,
    settings: Settings = DEFAULT,
    start: str | None = None,
    end: str | None = None,
    benchmark: PriceData | None = None,
) -> BacktestResult:
    strategy.check()
    settings.check()
    window = chooseWindow(prices, strategy.warmupBars, start, end)
    mine = summariseRun(prices, strategy, settings, window)
    hold = summariseRun(prices, BuyAndHold(), settings, window)
    days = indexDays(mine.engine.bars)
    index, missing = compareBenchmark(benchmark, days, settings)
    reshuffled = runMonteCarlo(
        dailyReturns(mine.equity()),
        dailyReturns(hold.equity()),
        settings.simulations,
        settings.blockLength,
        settings.seed,
    )
    firstPrice = float(prices.frame["close"].iloc[window.first])
    warnings = buildWarnings(
        days,
        settings,
        mine.engine,
        list(mine.trips),
        firstPrice,
        window.warnings,
        missing,
        prices.notes,
    )
    return BacktestResult(
        prices=prices,
        strategy=strategy,
        settings=settings,
        window=window,
        days=tuple(days),
        strategyRun=mine,
        holdRun=hold,
        benchmark=index,
        monteCarlo=reshuffled,
        sensitivity=runSensitivity(prices, strategy, settings, window),
        warnings=tuple(warnings),
        version=version("backtestlab"),
    )
