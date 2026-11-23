import textwrap

from backtestlab.backtest import BacktestResult
from backtestlab.formatting import formatDate, formatPercent
from backtestlab.metrics import Metrics
from backtestlab.strategy import strategyLabel
from backtestlab.summary import summarySentences

WIDTH = 88
DISCLAIMER = "For education only. Not investment advice."


# a percentage, or a dash when it is not available
def percentCell(value: float | None) -> str:
    return "-" if value is None else formatPercent(value)


# the five numbers of one column of the results table
def columnCells(metrics: Metrics) -> list[str]:
    trades = metrics.completedTrades
    return [
        formatPercent(metrics.totalReturn),
        percentCell(metrics.annualisedReturn),
        formatPercent(metrics.maxDrawdown),
        "-" if metrics.sharpeRatio is None else f"{metrics.sharpeRatio:.2f}",
        "-" if trades is None else str(trades),
    ]


# the compact results table, with a column for the index when there is one
def resultsTable(result: BacktestResult) -> list[str]:
    names = [
        "Total return",
        "Annualised return",
        "Maximum drawdown",
        "Sharpe ratio",
        "Completed trades",
    ]
    headers = ["Strategy", "Buy and hold"]
    columns = [columnCells(result.strategyRun.metrics), columnCells(result.holdRun.metrics)]
    if result.benchmark is not None:
        headers.append(result.benchmark.label.split(" (")[0])
        columns.append(columnCells(result.benchmark.metrics))
    lines = [" " * 18 + "".join(header.rjust(15) for header in headers)]
    for row, name in enumerate(names):
        lines.append(name.ljust(18) + "".join(column[row].rjust(15) for column in columns))
    return lines


# the header lines that say what was tested
def headerLines(result: BacktestResult, version: str) -> list[str]:
    first, last = result.days[0], result.days[-1]
    data = (
        f"{result.prices.source}, {len(result.days):,} trading days, "
        f"{formatDate(first)} to {formatDate(last)}"
    )
    return [
        f"backtestlab {version}",
        f"Data      {data}",
        f"Strategy  {strategyLabel(result.strategy)}",
    ]


# the warnings as a list, or nothing when there are none
def warningLines(result: BacktestResult) -> list[str]:
    if not result.warnings:
        return []
    lines = ["", "Warnings"]
    for warning in result.warnings:
        wrapped = textwrap.wrap(warning.message, WIDTH - 4)
        lines.append(f"  - {wrapped[0]}")
        lines.extend(f"    {line}" for line in wrapped[1:])
    return lines


# everything printed after a run
def runLines(result: BacktestResult, reportPath: str, resultsPath: str) -> list[str]:
    lines = [*headerLines(result, result.version), "", *resultsTable(result), *warningLines(result)]
    lines += ["", *textwrap.wrap(" ".join(summarySentences(result)), WIDTH), ""]
    return [*lines, f"Report saved to {reportPath} and {resultsPath}", DISCLAIMER]
