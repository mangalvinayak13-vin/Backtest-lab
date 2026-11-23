import math
from dataclasses import dataclass, replace
from datetime import datetime

import numpy as np

from backtestlab.engine import EngineResult
from backtestlab.pricewarnings import indexDays
from backtestlab.settings import Settings
from backtestlab.trades import RoundTrip

TINY = 1e-12
DAYSPERYEAR = 365.25


# the numbers that describe one run, with None where a number can't be worked out
@dataclass(frozen=True)
class Metrics:
    startingValue: float
    finalValue: float
    totalReturn: float
    annualisedReturn: float | None
    annualisedVolatility: float | None
    sharpeRatio: float | None
    maxDrawdown: float
    drawdownPeak: datetime | None
    drawdownTrough: datetime | None
    timeInMarket: float | None = None
    completedTrades: int | None = None
    winRate: float | None = None
    costsPaid: float | None = None
    slippageCost: float | None = None


# the daily returns of a list of equity values
def dailyReturns(equity: list[float]) -> list[float]:
    values = np.array(equity)
    return [float(value) for value in values[1:] / values[:-1] - 1]


# the yearly growth rate that would turn the first value into the last over these dates
def annualisedReturn(equity: list[float], days: list[datetime]) -> float | None:
    years = (days[-1] - days[0]).days / DAYSPERYEAR
    ratio = equity[-1] / equity[0]
    if ratio <= 0:
        return -1.0
    growth = math.log(ratio) / years
    return math.exp(growth) - 1 if growth < 700 else None


# the sample standard deviation of the daily returns, or None with fewer than two returns
def returnSpread(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    return float(np.std(np.array(returns), ddof=1))


# the volatility and Sharpe ratio, each None when they can't be worked out
def riskFigures(returns: list[float], settings: Settings) -> tuple[float | None, float | None]:
    spread = returnSpread(returns)
    if spread is None:
        return None, None
    periods = settings.tradingDaysPerYear
    volatility = spread * math.sqrt(periods)
    if spread <= TINY:
        return volatility, None
    riskFreeDaily = (1 + settings.riskFreeRate) ** (1 / periods) - 1
    sharpe = (float(np.mean(returns)) - riskFreeDaily) / spread * math.sqrt(periods)
    return volatility, sharpe


# the biggest fall from an earlier peak, with the peak and trough positions
def drawdown(equity: list[float]) -> tuple[float, int, int]:
    values = np.array(equity)
    falls = values / np.maximum.accumulate(values) - 1
    trough = int(np.argmin(falls))
    peak = int(np.argmax(values[: trough + 1]))
    return float(falls[trough]), peak, trough


# the numbers that only need the equity values and their dates
def curveMetrics(days: list[datetime], equity: list[float], settings: Settings) -> Metrics:
    worst, peak, trough = drawdown(equity)
    volatility, sharpe = riskFigures(dailyReturns(equity), settings)
    return Metrics(
        startingValue=equity[0],
        finalValue=equity[-1],
        totalReturn=equity[-1] / equity[0] - 1,
        annualisedReturn=annualisedReturn(equity, days),
        annualisedVolatility=volatility,
        sharpeRatio=sharpe,
        maxDrawdown=worst,
        drawdownPeak=days[peak] if worst < 0 else None,
        drawdownTrough=days[trough] if worst < 0 else None,
    )


# the share of completed round trips that made a profit, or None when there are none
def winRate(trips: list[RoundTrip]) -> float | None:
    done = [trip for trip in trips if not trip.isOpen]
    if not done:
        return None
    return sum(1 for trip in done if trip.profit > 0) / len(done)


# all the numbers for a run of the engine, including the ones about trading
def runMetrics(result: EngineResult, trips: list[RoundTrip], settings: Settings) -> Metrics:
    equity = [float(value) for value in result.bars["equity"].values]
    held = [float(value) > 0 for value in result.bars["shares"].values[1:]]
    base = curveMetrics(indexDays(result.bars), equity, settings)
    return replace(
        base,
        timeInMarket=sum(held) / len(held),
        completedTrades=sum(1 for trip in trips if not trip.isOpen),
        winRate=winRate(trips),
        costsPaid=sum(fill.costs.total for fill in result.fills),
        slippageCost=sum(
            abs(fill.fillPrice - fill.openPrice) * fill.shares for fill in result.fills
        ),
    )
