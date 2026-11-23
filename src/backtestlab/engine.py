import math
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from backtestlab.costs import CostBreakdown, affordableValue, orderCosts
from backtestlab.prices import PriceData
from backtestlab.pricewarnings import indexDays
from backtestlab.settings import Settings
from backtestlab.strategy import Strategy, checkTarget, strategyLabel
from backtestlab.window import Window

COSTS = "costs"
UNAFFORDABLE = "unaffordable"


# one trade that happened, with every charge and the cash left afterwards
@dataclass(frozen=True)
class Fill:
    day: datetime
    side: str
    shares: float
    openPrice: float
    fillPrice: float
    orderValue: float
    costs: CostBreakdown
    cashAfter: float
    sharesAfter: float


# an order that was not placed, either because its charges were bigger than its value or
# because not even one share could be paid for
@dataclass(frozen=True)
class SkippedOrder:
    day: datetime
    side: str
    orderValue: float
    totalCosts: float
    reason: str


# what the engine produced: a row per bar, the trades and the skipped orders
@dataclass(frozen=True)
class EngineResult:
    bars: pd.DataFrame
    fills: tuple[Fill, ...]
    skipped: tuple[SkippedOrder, ...]


# the state after the open of one bar, with the trade or the skipped order if there was one
@dataclass(frozen=True)
class Outcome:
    cash: float
    shares: float
    fill: Fill | None
    skipped: SkippedOrder | None


# how many shares the target asks for when the portfolio is worth equity at this price
def desiredShares(target: float, equity: float, price: float, wholeShares: bool) -> float:
    wanted = target * equity / price
    return float(math.floor(wanted)) if wholeShares else wanted


# the most shares the cash can pay for at this fill price, with all the charges included
def maxAffordable(fillPrice: float, cash: float, settings: Settings) -> float:
    shares = affordableValue(settings.costs, cash) / fillPrice
    return float(math.floor(shares)) if settings.wholeShares else shares


# an order that could not be placed because not even one share can be paid for
def unaffordable(
    day: datetime, fillPrice: float, cash: float, shares: float, count: float, settings: Settings
) -> Outcome:
    wished = count * fillPrice
    costs = orderCosts(settings.costs, wished, True)
    return Outcome(cash, shares, None, SkippedOrder(day, "buy", wished, costs.total, UNAFFORDABLE))


# buy up to count shares at the open, or as many as the cash can pay for
def buyAtOpen(
    day: datetime, openPrice: float, cash: float, shares: float, count: float, settings: Settings
) -> Outcome:
    fillPrice = openPrice * (1 + settings.slippageRate)
    bought = min(count, maxAffordable(fillPrice, cash, settings))
    if bought <= 0:
        return unaffordable(day, fillPrice, cash, shares, count, settings)
    value = bought * fillPrice
    costs = orderCosts(settings.costs, value, True)
    if value < costs.total:
        return Outcome(cash, shares, None, SkippedOrder(day, "buy", value, costs.total, COSTS))
    cashAfter = max(cash - value - costs.total, 0.0)
    fill = Fill(day, "buy", bought, openPrice, fillPrice, value, costs, cashAfter, shares + bought)
    return Outcome(cashAfter, shares + bought, fill, None)


# sell count shares at the open
def sellAtOpen(
    day: datetime, openPrice: float, cash: float, shares: float, count: float, settings: Settings
) -> Outcome:
    fillPrice = openPrice * (1 - settings.slippageRate)
    value = count * fillPrice
    costs = orderCosts(settings.costs, value, False)
    if value < costs.total:
        return Outcome(cash, shares, None, SkippedOrder(day, "sell", value, costs.total, COSTS))
    cashAfter = cash + value - costs.total
    fill = Fill(day, "sell", count, openPrice, fillPrice, value, costs, cashAfter, shares - count)
    return Outcome(cashAfter, shares - count, fill, None)


# trade towards the target at the open price of a bar
def tradeAtOpen(
    day: datetime, openPrice: float, cash: float, shares: float, target: float, settings: Settings
) -> Outcome:
    equity = cash + shares * openPrice
    wanted = desiredShares(target, equity, openPrice, settings.wholeShares)
    if wanted > shares:
        return buyAtOpen(day, openPrice, cash, shares, wanted - shares, settings)
    if wanted < shares:
        return sellAtOpen(day, openPrice, cash, shares, shares - wanted, settings)
    fillPrice = openPrice * (1 + settings.slippageRate)
    if target > 0 and shares == 0 and maxAffordable(fillPrice, cash, settings) < 1:
        return unaffordable(day, fillPrice, cash, shares, 1.0, settings)
    return Outcome(cash, shares, None, None)


# replay the window one bar at a time: trade at the open, then value and decide at the close
def runEngine(
    prices: PriceData, strategy: Strategy, settings: Settings, window: Window
) -> EngineResult:
    frame = prices.frame
    days = indexDays(frame)
    opens = [float(price) for price in frame["open"].values]
    closes = [float(price) for price in frame["close"].values]
    cash, shares = settings.startingCash, 0.0
    inForce, pending = 0.0, 0.0
    rows, fills, skipped = [], [], []
    for position in range(window.first, window.last + 1):
        if pending != inForce:
            outcome = tradeAtOpen(days[position], opens[position], cash, shares, pending, settings)
            cash, shares = outcome.cash, outcome.shares
            fills.extend([outcome.fill] if outcome.fill else [])
            skipped.extend([outcome.skipped] if outcome.skipped else [])
            inForce = pending
        equity = cash + shares * closes[position]
        rows.append((days[position], cash, shares, equity, inForce))
        history = frame.iloc[: position + 1].copy()
        pending = checkTarget(
            strategyLabel(strategy), days[position].date().isoformat(), strategy.decide(history)
        )
    index = pd.DatetimeIndex([row[0] for row in rows], name="date")
    table = pd.DataFrame(
        {
            "cash": [row[1] for row in rows],
            "shares": [row[2] for row in rows],
            "equity": [row[3] for row in rows],
            "target": [row[4] for row in rows],
        },
        index=index,
    )
    return EngineResult(table, tuple(fills), tuple(skipped))
