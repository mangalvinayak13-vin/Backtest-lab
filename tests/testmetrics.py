import math
from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from helpers import FIRST, Scripted, exampleBars, plainSettings

from backtestlab.engine import runEngine
from backtestlab.metrics import curveMetrics, dailyReturns, runMetrics, winRate
from backtestlab.presets import DEFAULT
from backtestlab.strategies import BuyAndHold
from backtestlab.trades import RoundTrip, buildRoundTrips
from backtestlab.window import Window

SETTINGS = replace(DEFAULT, tradingDaysPerYear=252, riskFreeRate=0.0)


# consecutive days starting on 1 Jan 2024
def daysFor(count: int) -> list[datetime]:
    return [FIRST + timedelta(days=number) for number in range(count)]


# a round trip with only the profit filled in
def tripWith(profit: float, isOpen: bool = False) -> RoundTrip:
    return RoundTrip(FIRST, FIRST, 0, 100.0, 100.0 + profit, profit, profit / 100.0, isOpen)


# worked example 4: equity 100, 110, 99, 108.9
def testWorkedExampleFourReturnsAndRisk() -> None:
    equity = [100.0, 110.0, 99.0, 108.9]
    assert dailyReturns(equity) == pytest.approx([0.1, -0.1, 0.1], rel=1e-9)
    metrics = curveMetrics(daysFor(4), equity, SETTINGS)
    assert metrics.startingValue == 100.0
    assert metrics.finalValue == 108.9
    assert metrics.totalReturn == pytest.approx(0.089, rel=1e-9)
    assert metrics.maxDrawdown == pytest.approx(-0.1, rel=1e-9)
    assert metrics.drawdownPeak == daysFor(4)[1]
    assert metrics.drawdownTrough == daysFor(4)[2]
    assert metrics.annualisedVolatility == pytest.approx(1.8330, rel=1e-4)
    assert metrics.sharpeRatio == pytest.approx(4.5826, rel=1e-4)


# worked example 4: the mean and spread of the daily returns
def testWorkedExampleFourMeanAndSpread() -> None:
    returns = dailyReturns([100.0, 110.0, 99.0, 108.9])
    assert sum(returns) / 3 == pytest.approx(0.0333333, rel=1e-5)
    metrics = curveMetrics(daysFor(4), [100.0, 110.0, 99.0, 108.9], SETTINGS)
    assert metrics.annualisedVolatility == pytest.approx(0.1154701 * math.sqrt(252), rel=1e-6)


# worked example 4: the deepest fall is 25%, from the second value to the third
def testWorkedExampleFourDrawdown() -> None:
    equity = [100.0, 120.0, 90.0, 95.0, 130.0, 117.0]
    metrics = curveMetrics(daysFor(6), equity, SETTINGS)
    assert metrics.maxDrawdown == pytest.approx(-0.25, rel=1e-9)
    assert metrics.drawdownPeak == daysFor(6)[1]
    assert metrics.drawdownTrough == daysFor(6)[2]


# worked example 4: profits +10, -5, +3 and 0 give a win rate of 50%
def testWorkedExampleFourWinRate() -> None:
    trips = [tripWith(10.0), tripWith(-5.0), tripWith(3.0), tripWith(0.0)]
    assert winRate(trips) == 0.5


# an open round trip is not counted, and no completed trips means no win rate
def testWinRateIgnoresOpenTrips() -> None:
    assert winRate([]) is None
    assert winRate([tripWith(10.0, isOpen=True)]) is None
    assert winRate([tripWith(10.0), tripWith(10.0, isOpen=True)]) == 1.0


# equity that never falls has a drawdown of zero and no dates
def testNoDrawdownWhenEquityOnlyRises() -> None:
    metrics = curveMetrics(daysFor(3), [100.0, 101.0, 105.0], SETTINGS)
    assert metrics.maxDrawdown == 0.0
    assert metrics.drawdownPeak is None
    assert metrics.drawdownTrough is None


# annualised return uses calendar days over 365.25: 100 to 121 in two years is 10% a year
def testAnnualisedReturn() -> None:
    days = [FIRST, FIRST + timedelta(days=round(365.25 * 2))]
    metrics = curveMetrics(days, [100.0, 121.0], SETTINGS)
    assert metrics.annualisedReturn == pytest.approx(0.1, rel=1e-3)


# equity that falls to zero gives a return of minus 100% a year
def testAnnualisedReturnOfTotalLoss() -> None:
    assert curveMetrics(daysFor(3), [100.0, 50.0, 0.0], SETTINGS).annualisedReturn == -1.0


# a huge gain over very few days has no annualised number instead of infinity
def testAnnualisedReturnTooBigToShow() -> None:
    metrics = curveMetrics(daysFor(2), [1.0, 1000.0], SETTINGS)
    assert metrics.annualisedReturn is None
    assert metrics.totalReturn == 999.0


# the Sharpe ratio is not available when every return is the same
def testSharpeNotAvailableWithNoSpread() -> None:
    metrics = curveMetrics(daysFor(4), [100.0, 100.0, 100.0, 100.0], SETTINGS)
    assert metrics.sharpeRatio is None
    assert metrics.annualisedVolatility == 0.0
    steady = curveMetrics(daysFor(4), [100.0, 101.0, 102.01, 103.0301], SETTINGS)
    assert steady.sharpeRatio is None


# with one return there is no spread, so no volatility and no Sharpe ratio
def testOneReturnHasNoSpread() -> None:
    metrics = curveMetrics(daysFor(2), [100.0, 110.0], SETTINGS)
    assert metrics.annualisedVolatility is None
    assert metrics.sharpeRatio is None
    assert metrics.totalReturn == pytest.approx(0.1, rel=1e-9)


# a risk-free rate lowers the Sharpe ratio
def testRiskFreeRateLowersSharpe() -> None:
    equity = [100.0, 110.0, 99.0, 108.9]
    free = replace(SETTINGS, riskFreeRate=0.05)
    lower = curveMetrics(daysFor(4), equity, free).sharpeRatio
    base = curveMetrics(daysFor(4), equity, SETTINGS).sharpeRatio
    assert lower is not None
    assert base is not None
    assert lower < base
    riskFreeDaily = 1.05 ** (1 / 252) - 1
    expected = (0.1 / 3 - riskFreeDaily) / 0.1154701 * math.sqrt(252)
    assert lower == pytest.approx(expected, rel=1e-5)


# the trading numbers of a real engine run: costs, slippage, time in market and trades
def testRunMetricsOnWorkedExampleTwo() -> None:
    settings = replace(plainSettings(), costs=DEFAULT.costs, slippageRate=0.0005)
    window = Window(0, 3, ())
    result = runEngine(exampleBars(), Scripted((1.0, 0.0, 0.0, 0.0)), settings, window)
    trips = buildRoundTrips(result.fills, datetime(2024, 1, 4), 99.0)
    metrics = runMetrics(result, trips, settings)
    assert metrics.completedTrades == 1
    assert metrics.winRate == 1.0
    assert metrics.costsPaid == pytest.approx(0.918459 + 0.953523, rel=1e-9)
    assert metrics.slippageCost == pytest.approx(0.051 * 9 + 0.053 * 9, rel=1e-9)
    assert metrics.timeInMarket == pytest.approx(1 / 3, rel=1e-9)
    assert metrics.totalReturn == pytest.approx(0.033192018, rel=1e-9)


# buy and hold on the example bars is in the market for every day after the first buy
def testBuyAndHoldTimeInMarket() -> None:
    result = runEngine(exampleBars(), BuyAndHold(), plainSettings(), Window(0, 3, ()))
    metrics = runMetrics(result, [], plainSettings())
    assert metrics.timeInMarket == 1.0
    assert metrics.completedTrades == 0
    assert metrics.winRate is None
    assert metrics.totalReturn == pytest.approx(-0.027, rel=1e-9)
