import re
from dataclasses import replace
from pathlib import Path

import pytest
from helpers import exampleBars, makePrices, plainSettings, randomPrices

from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.prices import CSVADJUSTED, YAHOOADJUSTED, PriceData
from backtestlab.report import renderReport, writeReport
from backtestlab.strategies import BuyAndHold

SECTIONS = [
    "Warnings",
    "Summary",
    "Key numbers",
    "Charts",
    "Metrics",
    "Robustness",
    "Trades",
    "Settings used",
    "Disclaimer",
]


# the report has every section, in order
def testEverySectionInOrder(sampleResult: BacktestResult) -> None:
    html = renderReport(sampleResult)
    positions = [html.index(f"<h2>{name}</h2>") for name in SECTIONS]
    assert positions == sorted(positions)


# the report has at least five svg charts
def testAtLeastFiveCharts(sampleResult: BacktestResult) -> None:
    assert renderReport(sampleResult).count("<svg") >= 5


# the report has no scripts and loads nothing from outside
def testSelfContained(sampleResult: BacktestResult) -> None:
    html = renderReport(sampleResult).lower()
    assert "<script" not in html
    assert "<link" not in html
    assert "@import" not in html
    assert re.search(r'(src|href)="https?:', html) is None
    assert "url(http" not in html


# rupees use indian grouping in the report
def testIndianMoney(sampleResult: BacktestResult) -> None:
    html = renderReport(sampleResult)
    assert "₹1,00,000" in html
    assert "Checked on 23 Nov 2026" in html


# the default preset uses western grouping with no symbol
def testWesternMoney() -> None:
    result = runBacktest(exampleBars(), BuyAndHold(), plainSettings(startingCash=100000.0))
    html = renderReport(result)
    assert "100,000" in html
    assert "₹" not in html


# names from the user are escaped, so they can't add html
def testNamesAreEscaped() -> None:
    sneaky = PriceData(exampleBars().frame, "<b>EVIL</b>.NS", ())
    html = renderReport(runBacktest(sneaky, BuyAndHold(), plainSettings()))
    assert "<b>EVIL</b>" not in html
    assert "&lt;b&gt;EVIL&lt;/b&gt;" in html


# the command is shown when there is one
def testCommandIsShown(sampleResult: BacktestResult) -> None:
    html = renderReport(sampleResult, "backtestlab run --csv data/sampleprices.csv")
    assert "backtestlab run --csv data/sampleprices.csv" in html


# a short run says the reshuffle was skipped and that no trades were made
def testShortRunWording() -> None:
    result = runBacktest(exampleBars(), BuyAndHold(), plainSettings())
    html = renderReport(replace(result, strategyRun=replace(result.strategyRun, trips=())))
    assert "The reshuffling check was skipped" in html
    assert "The strategy made no trades." in html


# a run with no warnings has no warnings box
def testNoWarningsBox(sampleResult: BacktestResult) -> None:
    html = renderReport(replace(sampleResult, warnings=()))
    assert "<h2>Warnings</h2>" not in html


# at most 500 trades are shown, with a note saying so
def testTradeTableIsCapped(sampleResult: BacktestResult) -> None:
    many = sampleResult.strategyRun.trips[:1] * 501
    html = renderReport(
        replace(sampleResult, strategyRun=replace(sampleResult.strategyRun, trips=many))
    )
    assert "Only the first 500 of 501 round trips are shown." in html


# the report is written into a folder that is made if needed
def testWriteReportMakesTheFolder(sampleResult: BacktestResult, workdir: Path) -> None:
    target = workdir / "out" / "report.html"
    writeReport(sampleResult, target)
    with target.open(encoding="utf-8") as file:
        assert file.read().startswith("<!doctype html>")


# with a benchmark the metrics table has a column for it and a note that it has no costs
def testBenchmarkColumn() -> None:
    prices = randomPrices(2, 80)
    result = runBacktest(prices, BuyAndHold(), plainSettings(), benchmark=randomPrices(3, 80))
    html = renderReport(result)
    assert '<th class="num">test</th>' in html
    assert "The index is only a reference." in html


# a run that never falls shows a drawdown of zero without dates
def testDrawdownWithoutDates() -> None:
    rising = makePrices([(100.0 + step, 101.0 + step) for step in range(5)])
    html = renderReport(runBacktest(rising, BuyAndHold(), plainSettings()))
    assert "0.0%" in html


# a jump warning mentions adjusting, but it is not a record that the prices were adjusted
def testJumpWarningIsNotAnAdjustment() -> None:
    prices = makePrices([(100.0, 100.0), (50.0, 50.0), (50.0, 50.0)])
    result = runBacktest(prices, BuyAndHold(), plainSettings())
    assert "adjusted for" in result.prices.notes[0]
    assert "<td>No adjustment was recorded.</td>" in renderReport(result)


# the note from either loader is shown as the price adjustment
@pytest.mark.parametrize("note", [CSVADJUSTED, YAHOOADJUSTED])
def testAdjustmentNoteIsShown(note: str) -> None:
    prices = replace(exampleBars(), notes=("Dropped 1 rows.", note))
    result = runBacktest(prices, BuyAndHold(), plainSettings())
    assert f"<td>Price adjustment</td><td>{note}</td>" in renderReport(result)
