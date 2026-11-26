import math
from dataclasses import dataclass

import numpy

from backtestlab.backtest import BacktestResult
from backtestlab.settings import CostModel


# one number worked out by hand next to the tool's own
@dataclass(frozen=True)
class Check:
    ticker: str
    name: str
    byHand: float
    tool: float

    # whether the two agree, to a tiny rounding difference
    def matches(self) -> bool:
        return abs(self.byHand - self.tool) <= 1e-9 * max(1.0, abs(self.tool))


# the india charges on a buy of a given value, written out again from the cost table
def buyCharges(value: float, costs: CostModel) -> float:
    brokerage = costs.brokerageRate * value
    if costs.brokerageCap is not None:
        brokerage = min(brokerage, costs.brokerageCap)
    exchange = costs.exchangeFeeRate * value
    return (
        brokerage
        + exchange
        + costs.taxOnFeesRate * (brokerage + exchange)
        + costs.buyTaxRate * value
    )


# buy and hold from the prices: buy whole shares at the second open, value them at the last close
def holdReturnByHand(result: BacktestResult) -> float:
    frame = result.prices.frame
    settings = result.settings
    cash = settings.startingCash
    fillPrice = float(frame["open"].iloc[result.window.first + 1]) * (1 + settings.slippageRate)
    shares = math.floor(cash / fillPrice)
    while shares * fillPrice + buyCharges(shares * fillPrice, settings.costs) > cash:
        shares -= 1
    left = cash - shares * fillPrice - buyCharges(shares * fillPrice, settings.costs)
    lastClose = float(frame["close"].iloc[result.window.last])
    return (left + shares * lastClose) / cash - 1


# how many times the short average crossed above the long one, from pandas rolling means
def entriesByHand(result: BacktestResult, shortWindow: int, longWindow: int) -> int:
    closes = result.prices.frame["close"]
    above = (closes.rolling(shortWindow).mean() > closes.rolling(longWindow).mean()).values
    entries = 0
    invested = False
    for flag in above[result.window.first : result.window.last]:
        if flag and not invested:
            entries += 1
        invested = bool(flag)
    return entries


# the worst fall straight from the equity curve, with numpy
def worstFallByHand(result: BacktestResult) -> float:
    values = numpy.array(result.strategyRun.equity())
    return float((values / numpy.maximum.accumulate(values) - 1).min())


# the three checks for one run
def checkRun(result: BacktestResult, ticker: str, shortWindow: int, longWindow: int) -> list[Check]:
    buys = sum(1 for fill in result.strategyRun.engine.fills if fill.side == "buy")
    return [
        Check(
            ticker,
            "buy and hold return",
            holdReturnByHand(result),
            result.holdRun.metrics.totalReturn,
        ),
        Check(
            ticker,
            "crossovers into the market",
            entriesByHand(result, shortWindow, longWindow),
            buys,
        ),
        Check(
            ticker, "worst fall", worstFallByHand(result), result.strategyRun.metrics.maxDrawdown
        ),
    ]
