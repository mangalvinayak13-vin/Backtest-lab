from dataclasses import dataclass

from backtestlab.settings import CostModel


# every charge on one order, kept apart so the report can show where the money went
@dataclass(frozen=True)
class CostBreakdown:
    brokerage: float
    exchange: float
    taxOnFees: float
    sideTax: float
    fixed: float

    # all the charges added up
    @property
    def total(self) -> float:
        return self.brokerage + self.exchange + self.taxOnFees + self.sideTax + self.fixed


# the charges on an order worth value, for a buy or a sell
def orderCosts(model: CostModel, value: float, isBuy: bool) -> CostBreakdown:
    brokerage = model.brokerageRate * value
    if model.brokerageCap is not None:
        brokerage = min(brokerage, model.brokerageCap)
    exchange = model.exchangeFeeRate * value
    taxOnFees = model.taxOnFeesRate * (brokerage + exchange)
    sideTax = (model.buyTaxRate if isBuy else model.sellTaxRate) * value
    fixed = 0.0 if isBuy else model.sellFeePerOrder
    return CostBreakdown(brokerage, exchange, taxOnFees, sideTax, fixed)


# the biggest buy order value that cash can pay for, with all the charges included
def affordableValue(model: CostModel, cash: float) -> float:
    if cash <= 0:
        return 0.0
    gst = 1 + model.taxOnFeesRate
    others = gst * model.exchangeFeeRate + model.buyTaxRate
    uncapped = cash / (1 + gst * model.brokerageRate + others)
    cap = model.brokerageCap
    if cap is None or model.brokerageRate * uncapped <= cap:
        return uncapped
    return (cash - gst * cap) / (1 + others)
