import pytest

from backtestlab.costs import affordableValue, orderCosts
from backtestlab.presets import INDIA
from backtestlab.settings import CostModel


# worked example 3: a buy of 1,00,000 in rupees on the india preset
def testIndiaBuyOrder() -> None:
    costs = orderCosts(INDIA.costs, 100000.0, True)
    assert costs.brokerage == pytest.approx(20.0, rel=1e-9)
    assert costs.exchange == pytest.approx(3.17, rel=1e-9)
    assert costs.taxOnFees == pytest.approx(4.1706, rel=1e-9)
    assert costs.sideTax == pytest.approx(115.0, rel=1e-9)
    assert costs.fixed == 0.0
    assert costs.total == pytest.approx(142.3406, rel=1e-9)


# worked example 3: a sell of 1,00,000 in rupees on the india preset
def testIndiaSellOrder() -> None:
    costs = orderCosts(INDIA.costs, 100000.0, False)
    assert costs.sideTax == pytest.approx(100.0, rel=1e-9)
    assert costs.fixed == pytest.approx(15.34, rel=1e-9)
    assert costs.total == pytest.approx(142.6806, rel=1e-9)


# brokerage is a percentage of the order below the cap, and the cap above it
def testBrokerageCap() -> None:
    model = CostModel(brokerageRate=0.001, brokerageCap=20.0)
    assert orderCosts(model, 10000.0, True).brokerage == pytest.approx(10.0, rel=1e-9)
    assert orderCosts(model, 50000.0, True).brokerage == 20.0


# without a cap, brokerage keeps growing with the order
def testNoCap() -> None:
    model = CostModel(brokerageRate=0.001, brokerageCap=None)
    assert orderCosts(model, 1000000.0, False).brokerage == pytest.approx(1000.0, rel=1e-9)


# the tax on fees is charged on brokerage plus exchange fees only, not on the other taxes
def testTaxOnFeesBase() -> None:
    model = CostModel(
        brokerageRate=0.01,
        exchangeFeeRate=0.001,
        taxOnFeesRate=0.5,
        buyTaxRate=0.1,
        sellFeePerOrder=7.0,
    )
    costs = orderCosts(model, 1000.0, True)
    assert costs.taxOnFees == pytest.approx(0.5 * (10.0 + 1.0), rel=1e-9)
    assert costs.sideTax == pytest.approx(100.0, rel=1e-9)
    assert costs.fixed == 0.0


# a fixed fee is charged on sells only
def testFixedFeeOnSellsOnly() -> None:
    model = CostModel(brokerageRate=0.0, sellFeePerOrder=7.0)
    assert orderCosts(model, 1000.0, False).total == 7.0
    assert orderCosts(model, 1000.0, True).total == 0.0


# a model with no charges costs nothing
def testNoCosts() -> None:
    assert orderCosts(CostModel(brokerageRate=0.0), 5000.0, True).total == 0.0


# the largest affordable order uses up the cash exactly, including all the charges
@pytest.mark.parametrize("cash", [50.0, 1000.0, 12345.67, 1000000.0])
@pytest.mark.parametrize(
    "model",
    [
        INDIA.costs,
        CostModel(brokerageRate=0.001),
        CostModel(brokerageRate=0.01, brokerageCap=5.0, taxOnFeesRate=0.18, buyTaxRate=0.002),
    ],
)
def testAffordableValueUsesAllTheCash(cash: float, model: CostModel) -> None:
    value = affordableValue(model, cash)
    assert value + orderCosts(model, value, True).total == pytest.approx(cash, rel=1e-9)


# with a cap the affordable value is cash minus the capped brokerage
def testAffordableValueWithCap() -> None:
    model = CostModel(brokerageRate=0.01, brokerageCap=5.0)
    assert affordableValue(model, 1000.0) == pytest.approx(995.0, rel=1e-9)


# with no cash there is nothing to buy
def testAffordableValueWithNoCash() -> None:
    assert affordableValue(CostModel(), 0.0) == 0.0
    assert affordableValue(CostModel(), -5.0) == 0.0
