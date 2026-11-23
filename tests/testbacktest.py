from dataclasses import replace

import pytest
from helpers import exampleBars, plainSettings, randomPrices

from backtestlab.api import VERSION
from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.engine import runEngine
from backtestlab.errors import SettingsError
from backtestlab.presets import DEFAULT, INDIA
from backtestlab.prices import PriceData
from backtestlab.strategies import BuyAndHold, MovingAverageCrossover


# the strategy and buy and hold use exactly the same window of dates
def testSameWindowForBoth(sampleResult: BacktestResult) -> None:
    mine = sampleResult.strategyRun.engine.bars.index
    held = sampleResult.holdRun.engine.bars.index
    assert list(mine) == list(held)
    assert len(sampleResult.days) == sampleResult.window.last - sampleResult.window.first + 1


# buy and hold in the result is the same as running buy and hold through the engine
def testBuyAndHoldIsTheEngineRun(sampleResult: BacktestResult) -> None:
    alone = runEngine(sampleResult.prices, BuyAndHold(), INDIA, sampleResult.window)
    assert sampleResult.holdRun.equity() == [float(value) for value in alone.bars["equity"].values]


# the result has the checks, the warnings and the version
def testResultHasEverything(sampleResult: BacktestResult) -> None:
    assert sampleResult.monteCarlo is not None
    assert len(sampleResult.sensitivity) == 3
    assert "window-moved" in [warning.code for warning in sampleResult.warnings]
    assert sampleResult.version == VERSION
    assert sampleResult.benchmark is None


# bad settings are caught before anything runs
def testBadSettingsStopTheRun() -> None:
    with pytest.raises(SettingsError, match="Starting cash"):
        runBacktest(exampleBars(), BuyAndHold(), replace(DEFAULT, startingCash=0.0))


# a strategy with bad parameters is caught before anything runs
def testBadStrategyStopsTheRun() -> None:
    with pytest.raises(SettingsError, match="shortWindow"):
        runBacktest(exampleBars(), MovingAverageCrossover(5, 5))


# start and end dates trim the window
def testStartAndEnd() -> None:
    result = runBacktest(
        randomPrices(1, 30), BuyAndHold(), plainSettings(), "2024-01-05", "2024-01-20"
    )
    assert result.days[0].day == 5
    assert result.days[-1].day == 20


# a benchmark is scaled to the starting cash and gets its own numbers
def testBenchmarkIsIncluded() -> None:
    prices = randomPrices(2, 100)
    index = randomPrices(3, 100)
    result = runBacktest(prices, BuyAndHold(), replace(INDIA, simulations=100), benchmark=index)
    assert result.benchmark is not None
    assert result.benchmark.label == "NIFTY 50 (price index, excludes dividends)"
    assert result.benchmark.values[0] == pytest.approx(100000.0)
    assert result.benchmark.metrics.completedTrades is None


# without a label in the settings, the benchmark is named after its source
def testBenchmarkLabelFallsBackToSource() -> None:
    prices = randomPrices(2, 80)
    index = PriceData(randomPrices(3, 80).frame, "^GSPC (Yahoo Finance)", ())
    result = runBacktest(prices, BuyAndHold(), plainSettings(), benchmark=index)
    assert result.benchmark is not None
    assert result.benchmark.label == "^GSPC (Yahoo Finance)"


# a benchmark that starts after the test is left out with a warning
def testLateBenchmarkIsLeftOut() -> None:
    prices = randomPrices(2, 80)
    late = PriceData(randomPrices(3, 80).frame.iloc[10:], "late", ())
    result = runBacktest(prices, BuyAndHold(), plainSettings(), benchmark=late)
    assert result.benchmark is None
    assert "benchmark-missing" in [warning.code for warning in result.warnings]


# a short test skips the Monte Carlo check and says so
def testShortTestSkipsMonteCarlo() -> None:
    result = runBacktest(exampleBars(), BuyAndHold(), plainSettings())
    assert result.monteCarlo is None
    assert "monte-carlo-skipped" in [warning.code for warning in result.warnings]
