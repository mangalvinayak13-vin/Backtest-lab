from dataclasses import replace
from pathlib import Path

from helpers import plainSettings, randomPrices

from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.csvsource import loadCsv, saveCsv
from backtestlab.runwarning import RunWarning
from backtestlab.strategies import BuyAndHold
from backtestlab.terminal import resultsTable, runLines, warningLines


# the table has a row for each number and the columns line up
def testResultsTable(sampleResult: BacktestResult) -> None:
    lines = resultsTable(sampleResult)
    assert lines[0].split() == ["Strategy", "Buy", "and", "hold"]
    assert [line[:18].strip() for line in lines[1:]] == [
        "Total return",
        "Annualised return",
        "Maximum drawdown",
        "Sharpe ratio",
        "Completed trades",
    ]
    assert len({len(line) for line in lines}) == 1


# with an index the table gets a third column named by the short label
def testResultsTableWithBenchmark() -> None:
    prices = randomPrices(2, 80)
    result = runBacktest(prices, BuyAndHold(), plainSettings(), benchmark=randomPrices(3, 80))
    lines = resultsTable(result)
    assert lines[0].rstrip().endswith("test")
    assert lines[-1].rstrip().endswith("-")


# long warnings are wrapped and indented, and no warnings means no lines
def testWarningLines(sampleResult: BacktestResult) -> None:
    long = RunWarning("data-note", "word " * 40)
    lines = warningLines(replace(sampleResult, warnings=(long,)))
    assert lines[:2] == ["", "Warnings"]
    assert lines[2].startswith("  - word")
    assert lines[3].startswith("    word")
    assert warningLines(replace(sampleResult, warnings=())) == []


# the printed lines end with where the files went and the disclaimer
def testRunLines(sampleResult: BacktestResult) -> None:
    lines = runLines(sampleResult, "report.html", "report.json")
    assert lines[0].startswith("backtestlab ")
    assert lines[-2] == "Report saved to report.html and report.json"
    assert lines[-1] == "For education only. Not investment advice."


# saved prices can be saved again into a folder that already exists
def testSaveCsvIntoAnExistingFolder(workdir: Path) -> None:
    prices = randomPrices(4, 10)
    saveCsv(prices, workdir / "prices.csv")
    assert loadCsv(workdir / "prices.csv").frame.equals(prices.frame)
