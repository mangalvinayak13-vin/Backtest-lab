import csv
from datetime import datetime
from pathlib import Path

from measures import (
    Stretch,
    longestInCalendarDays,
    longestInTradingDays,
    outOfMarket,
    stretchContaining,
    timesOutDuring,
    underwaterStretches,
    withInterest,
    yearFall,
)
from plan import Run

from backtestlab.backtest import BacktestResult, RunSummary
from backtestlab.metrics import Metrics

IDLERATE = 0.06

Row = dict[str, str | int | float]


# a fraction as a percentage with four decimals, or blank when it isn't available
def percent(value: float | None) -> float | str:
    return "" if value is None else round(value * 100, 4)


# an amount of money to the paisa
def rupees(value: float) -> float:
    return round(value, 2)


# a date as an ISO string, or blank
def isoDay(value: datetime | None) -> str:
    return "" if value is None else value.date().isoformat()


# the columns that name the run
def runColumns(run: Run, result: BacktestResult) -> Row:
    return {
        "part": run.part,
        "run": run.label(),
        "period": run.period.name,
        "ticker": run.ticker,
        "shortWindow": run.shortWindow,
        "longWindow": run.longWindow,
        "seed": run.seed,
        "firstDate": isoDay(result.days[0]),
        "lastDate": isoDay(result.days[-1]),
        "bars": len(result.days),
        "crashYear": run.period.crashYear,
    }


# final value and total return, and the rest of the numbers when it is a traded series
def metricColumns(prefix: str, metrics: Metrics) -> Row:
    return {
        f"{prefix}FinalRs": rupees(metrics.finalValue),
        f"{prefix}ReturnPct": percent(metrics.totalReturn),
        f"{prefix}AnnualPct": percent(metrics.annualisedReturn),
        f"{prefix}VolatilityPct": percent(metrics.annualisedVolatility),
        f"{prefix}Sharpe": "" if metrics.sharpeRatio is None else round(metrics.sharpeRatio, 4),
        f"{prefix}WorstFallPct": percent(metrics.maxDrawdown),
        f"{prefix}WorstPeak": isoDay(metrics.drawdownPeak),
        f"{prefix}WorstTrough": isoDay(metrics.drawdownTrough),
    }


# the final value and return of the market index, blank if it was left out
def niftyColumns(result: BacktestResult) -> Row:
    if result.benchmark is None:
        return {"niftyFinalRs": "", "niftyReturnPct": ""}
    metrics = result.benchmark.metrics
    return {
        "niftyFinalRs": rupees(metrics.finalValue),
        "niftyReturnPct": percent(metrics.totalReturn),
    }


# the columns that describe one stretch under water
def stretchColumns(name: str, stretch: Stretch | None, days: tuple[datetime, ...]) -> Row:
    if stretch is None:
        return {f"{name}Days": 0, f"{name}From": "", f"{name}To": "", f"{name}Open": ""}
    return {
        f"{name}Days": stretch.tradingDays(),
        f"{name}From": isoDay(days[stretch.peak]),
        f"{name}To": isoDay(days[stretch.last + 1]) if stretch.recovered else "",
        f"{name}Open": "no" if stretch.recovered else "yes",
    }


# the crash-year fall and the time under water for one equity curve
def fallColumns(prefix: str, run: RunSummary, days: tuple[datetime, ...], year: int) -> Row:
    values = run.equity()
    stretches = underwaterStretches(values)
    fall = yearFall(days, values, year)
    crash = None if fall.trough is None else stretchContaining(stretches, days.index(fall.trough))
    return {
        f"{prefix}CrashFallPct": percent(fall.size),
        f"{prefix}CrashPeak": isoDay(fall.peak),
        f"{prefix}CrashTrough": isoDay(fall.trough),
        **stretchColumns(f"{prefix}Underwater", longestInTradingDays(stretches), days),
        f"{prefix}UnderwaterCalendarDays": longestInCalendarDays(stretches, days),
        **stretchColumns(f"{prefix}CrashStretch", crash, days),
    }


# the first time out of the market that overlaps the crash year, and what holding gained meanwhile
def exitColumns(result: BacktestResult, year: int) -> Row:
    found = timesOutDuring(outOfMarket(result), year)
    if not found:
        return {"crashOutFrom": "", "crashOutTo": "", "crashOutHoldGainPct": ""}
    first = found[0]
    return {
        "crashOutFrom": isoDay(first.left),
        "crashOutTo": isoDay(first.back),
        "crashOutHoldGainPct": percent(first.holdGain()),
    }


# how the strategy traded and what it paid
def tradeColumns(metrics: Metrics) -> Row:
    return {
        "timeInMarketPct": percent(metrics.timeInMarket),
        "roundTrips": metrics.completedTrades or 0,
        "winRatePct": percent(metrics.winRate),
        "costsRs": rupees(metrics.costsPaid or 0.0),
        "slippageRs": rupees(metrics.slippageCost or 0.0),
    }


# the chance of beating buy and hold, and the spread of final values, in the reshuffles
def monteCarloColumns(result: BacktestResult) -> Row:
    reshuffled = result.monteCarlo
    if reshuffled is None:
        return {"mcBeatsHoldPct": "", "mcFinalP5Rs": "", "mcFinalP50Rs": "", "mcFinalP95Rs": ""}
    cash = result.settings.startingCash
    spread = reshuffled.strategy.totalReturn
    return {
        "mcBeatsHoldPct": percent(reshuffled.probabilityBeatsHold),
        "mcFinalP5Rs": rupees(cash * (1 + spread.p5)),
        "mcFinalP50Rs": rupees(cash * (1 + spread.p50)),
        "mcFinalP95Rs": rupees(cash * (1 + spread.p95)),
    }


# the strategy with costs times 0, 1 and 2
def costColumns(result: BacktestResult) -> Row:
    columns: Row = {}
    for row in result.sensitivity:
        name = f"costs{int(row.multiplier)}"
        columns[f"{name}ReturnPct"] = percent(row.totalReturn)
        columns[f"{name}AnnualPct"] = percent(row.annualisedReturn)
        columns[f"{name}Sharpe"] = "" if row.sharpeRatio is None else round(row.sharpeRatio, 4)
    return columns


# total return if idle cash had earned 6% a year, an estimate made outside the tool
def idleReturn(run: RunSummary, daysPerYear: int) -> float:
    cash = [float(value) for value in run.engine.bars["cash"].values]
    grown = withInterest(run.equity(), cash, IDLERATE, daysPerYear)
    return grown[-1] / grown[0] - 1


# the idle cash estimate for the strategy and for buy and hold
def idleColumns(result: BacktestResult) -> Row:
    daysPerYear = result.settings.tradingDaysPerYear
    mine = idleReturn(result.strategyRun, daysPerYear)
    hold = idleReturn(result.holdRun, daysPerYear)
    return {
        "idleStrategyReturnPct": percent(mine),
        "idleHoldReturnPct": percent(hold),
        "idleGapPoints": round((mine - hold) * 100, 4),
    }


# every warning the tool gave, codes and messages
def warningColumns(result: BacktestResult) -> Row:
    return {
        "warningCodes": " ".join(warning.code for warning in result.warnings),
        "warnings": " | ".join(warning.message for warning in result.warnings),
    }


# one row of results.csv for one run
def buildRow(run: Run, result: BacktestResult) -> Row:
    mine = result.strategyRun.metrics
    hold = result.holdRun.metrics
    year = run.period.crashYear
    return {
        **runColumns(run, result),
        **metricColumns("strategy", mine),
        **metricColumns("hold", hold),
        **niftyColumns(result),
        "gapPoints": round((mine.totalReturn - hold.totalReturn) * 100, 4),
        **fallColumns("strategy", result.strategyRun, result.days, year),
        **fallColumns("hold", result.holdRun, result.days, year),
        **exitColumns(result, year),
        **tradeColumns(mine),
        **monteCarloColumns(result),
        **costColumns(result),
        **idleColumns(result),
        **warningColumns(result),
    }


# write every row to a csv file, one column per number
def writeRows(rows: list[Row], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(list(rows[0]))
        for row in rows:
            writer.writerow(list(row.values()))
