from helpers import exampleBars, plainSettings, randomPrices

from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.charts import allCharts, cleanSvg
from backtestlab.strategies import BuyAndHold


# there are five charts, each a bare svg element
def testFiveSvgCharts(sampleResult: BacktestResult) -> None:
    charts = allCharts(sampleResult)
    assert list(charts) == ["growth", "drawdown", "price", "fan", "histogram"]
    for svg in charts.values():
        assert svg.startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert "<metadata>" not in svg
        assert '<g id="' not in svg


# drawing the same result twice gives exactly the same text
def testChartsAreRepeatable(sampleResult: BacktestResult) -> None:
    assert allCharts(sampleResult) == allCharts(sampleResult)


# the charts still draw when the Monte Carlo check was skipped and with a benchmark missing
def testChartsWithoutMonteCarlo() -> None:
    result = runBacktest(exampleBars(), BuyAndHold(), plainSettings())
    assert result.monteCarlo is None
    assert all(svg.startswith("<svg") for svg in allCharts(result).values())


# the cleaning keeps the drawing and drops the header, the metadata, comments and group names
def testCleanSvg() -> None:
    raw = (
        '<?xml version="1.0"?>\n<svg viewBox="0 0 1 1"><metadata>x</metadata>'
        '<!-- a comment --><g id="figure1"><path id="p1"/></g></svg>'
    )
    assert cleanSvg(raw) == '<svg viewBox="0 0 1 1"><g><path id="p1"/></g></svg>'


# the growth chart draws a third line when there is a benchmark
def testGrowthChartWithBenchmark() -> None:
    plain = runBacktest(randomPrices(2, 80), BuyAndHold(), plainSettings())
    withIndex = runBacktest(
        randomPrices(2, 80), BuyAndHold(), plainSettings(), benchmark=randomPrices(3, 80)
    )
    assert allCharts(withIndex)["growth"].count("<path") > allCharts(plain)["growth"].count("<path")
