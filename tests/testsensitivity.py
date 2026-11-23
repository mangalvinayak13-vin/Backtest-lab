import pytest
from helpers import randomPrices

from backtestlab.engine import runEngine
from backtestlab.metrics import curveMetrics
from backtestlab.presets import INDIA
from backtestlab.pricewarnings import indexDays
from backtestlab.sensitivity import runSensitivity, scaleCosts, scaleSettings
from backtestlab.settings import CostModel
from backtestlab.strategies import MovingAverageCrossover
from backtestlab.window import chooseWindow


# every charge and the slippage are doubled, but the tax on fees stays the same
def testScaleDoublesEverythingButTaxOnFees() -> None:
    doubled = scaleSettings(INDIA, 2.0)
    assert doubled.costs.brokerageRate == pytest.approx(0.002)
    assert doubled.costs.brokerageCap == pytest.approx(40.0)
    assert doubled.costs.buyTaxRate == pytest.approx(0.0023)
    assert doubled.costs.sellTaxRate == pytest.approx(0.002)
    assert doubled.costs.exchangeFeeRate == pytest.approx(0.0000634)
    assert doubled.costs.sellFeePerOrder == pytest.approx(30.68)
    assert doubled.costs.taxOnFeesRate == 0.18
    assert doubled.slippageRate == pytest.approx(0.001)


# a missing cap stays missing
def testScaleKeepsNoCap() -> None:
    assert scaleCosts(CostModel(brokerageRate=0.001), 2.0).brokerageCap is None


# three rows for costs times 0, 1 and 2; times 1 matches a normal run, and more costs never help
def testSensitivityRows() -> None:
    prices = randomPrices(21, 300)
    strategy = MovingAverageCrossover(5, 20)
    window = chooseWindow(prices, strategy.warmupBars)
    rows = runSensitivity(prices, strategy, INDIA, window)
    assert [row.multiplier for row in rows] == [0.0, 1.0, 2.0]
    normal = runEngine(prices, strategy, INDIA, window)
    equity = [float(value) for value in normal.bars["equity"].values]
    expected = curveMetrics(indexDays(normal.bars), equity, INDIA)
    assert rows[1].totalReturn == pytest.approx(expected.totalReturn, rel=1e-12)
    assert rows[1].sharpeRatio == expected.sharpeRatio
    assert rows[1].annualisedReturn == expected.annualisedReturn
    assert rows[0].totalReturn >= rows[1].totalReturn >= rows[2].totalReturn
