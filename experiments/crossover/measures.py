from dataclasses import dataclass
from datetime import datetime

from backtestlab.backtest import BacktestResult
from backtestlab.engine import Fill


# one stretch of days spent below an earlier high
@dataclass(frozen=True)
class Stretch:
    peak: int
    first: int
    last: int
    recovered: bool

    # how many trading days the value stayed below the high
    def tradingDays(self) -> int:
        return self.last - self.first + 1

    # calendar days from the high to the day it was regained, or to the last day if it never was
    def calendarDays(self, days: tuple[datetime, ...]) -> int:
        end = self.last + 1 if self.recovered else self.last
        return (days[end] - days[self.peak]).days


# every stretch below an earlier high, including one still open on the last day
def underwaterStretches(values: list[float]) -> list[Stretch]:
    stretches = []
    peak = 0
    first: int | None = None
    for index, value in enumerate(values):
        if value >= values[peak]:
            if first is not None:
                stretches.append(Stretch(peak, first, index - 1, True))
                first = None
            peak = index
        elif first is None:
            first = index
    if first is not None:
        stretches.append(Stretch(peak, first, len(values) - 1, False))
    return stretches


# the longest stretch counted in trading days, or None if the value never fell
def longestInTradingDays(stretches: list[Stretch]) -> Stretch | None:
    return max(stretches, key=lambda stretch: stretch.tradingDays(), default=None)


# the longest stretch counted in calendar days, the way my first one-off script counted it
def longestInCalendarDays(stretches: list[Stretch], days: tuple[datetime, ...]) -> int:
    return max((stretch.calendarDays(days) for stretch in stretches), default=0)


# the stretch that contains one day, if that day was below an earlier high
def stretchContaining(stretches: list[Stretch], index: int) -> Stretch | None:
    for stretch in stretches:
        if stretch.first <= index <= stretch.last:
            return stretch
    return None


# a fall from a high to a low, as a negative fraction
@dataclass(frozen=True)
class Fall:
    size: float
    peak: datetime | None
    trough: datetime | None


# the worst fall whose high and low are both inside one calendar year
def yearFall(days: tuple[datetime, ...], values: list[float], year: int) -> Fall:
    worst = Fall(0.0, None, None)
    peakValue = 0.0
    peakDay = days[0]
    for day, value in zip(days, values, strict=True):
        if day.year != year:
            continue
        if value >= peakValue:
            peakValue, peakDay = value, day
        if value / peakValue - 1 < worst.size:
            worst = Fall(value / peakValue - 1, peakDay, day)
    return worst


# equity as if cash earned a yearly rate, worked out outside the tool from the daily values
def withInterest(
    equity: list[float], cash: list[float], yearlyRate: float, daysPerYear: int
) -> list[float]:
    dailyRate = (1 + yearlyRate) ** (1 / daysPerYear) - 1
    grown = [equity[0]]
    for index in range(1, len(equity)):
        dayReturn = equity[index] / equity[index - 1] - 1
        cashShare = cash[index - 1] / equity[index - 1]
        grown.append(grown[-1] * (1 + dayReturn + cashShare * dailyRate))
    return grown


# one time out of the market: when it sold, when it bought back, and the price at each
@dataclass(frozen=True)
class TimeOut:
    left: datetime
    back: datetime | None
    leftPrice: float
    backPrice: float

    # what simply holding gained while the strategy was out
    def holdGain(self) -> float:
        return self.backPrice / self.leftPrice - 1


# every time out of the market, starting with the cash it holds on the first day
def timesOut(
    fills: tuple[Fill, ...], firstDay: datetime, firstClose: float, lastClose: float
) -> list[TimeOut]:
    stretches = []
    left: tuple[datetime, float] | None = (firstDay, firstClose)
    for fill in fills:
        if fill.side == "buy" and left is not None:
            stretches.append(TimeOut(left[0], fill.day, left[1], fill.openPrice))
            left = None
        elif fill.side == "sell" and fill.sharesAfter == 0:
            left = (fill.day, fill.openPrice)
    if left is not None:
        stretches.append(TimeOut(left[0], None, left[1], lastClose))
    return stretches


# the times out of the market that overlap one calendar year
def timesOutDuring(stretches: list[TimeOut], year: int) -> list[TimeOut]:
    return [
        stretch
        for stretch in stretches
        if stretch.left.year <= year and (stretch.back is None or stretch.back.year >= year)
    ]


# every time one backtest's strategy was out of the market
def outOfMarket(result: BacktestResult) -> list[TimeOut]:
    frame = result.prices.frame
    firstClose = float(frame["close"].iloc[result.window.first])
    lastClose = float(frame["close"].iloc[result.window.last])
    return timesOut(result.strategyRun.engine.fills, result.days[0], firstClose, lastClose)
