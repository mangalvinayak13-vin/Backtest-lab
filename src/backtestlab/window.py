from dataclasses import dataclass
from datetime import datetime

from backtestlab.dates import parseDay
from backtestlab.errors import DataError
from backtestlab.formatting import formatDate
from backtestlab.prices import PriceData
from backtestlab.pricewarnings import indexDays
from backtestlab.runwarning import RunWarning


# the first and last bar of the test, as positions in the price table, and any warning
@dataclass(frozen=True)
class Window:
    first: int
    last: int
    warnings: tuple[RunWarning, ...]


# a date given as text, or None when it was not given
def parseOptional(text: str | None, name: str) -> datetime | None:
    if text is None:
        return None
    day = parseDay(text, name)
    return datetime(day.year, day.month, day.day)


# the position of the first day on or after start, or the number of days if there is none
def firstOnOrAfter(days: list[datetime], start: datetime | None) -> int:
    if start is None:
        return 0
    return next((position for position, day in enumerate(days) if day >= start), len(days))


# the position of the last day on or before end, or -1 if there is none
def lastOnOrBefore(days: list[datetime], end: datetime | None) -> int:
    if end is None:
        return len(days) - 1
    return max((position for position, day in enumerate(days) if day <= end), default=-1)


# the message about a window that starts later than asked for
def movedWarning(
    requested: datetime, actual: datetime, warmedUp: bool, warmupBars: int
) -> RunWarning:
    reason = (
        f"the strategy needs {warmupBars} days of history first"
        if warmedUp
        else "the data starts later"
    )
    text = (
        f"The test starts on {formatDate(actual)} instead of {formatDate(requested)} "
        f"because {reason}."
    )
    return RunWarning("window-moved", text)


# pick the bars of the test, so that the strategy has its warm-up history before the first bar
def chooseWindow(
    prices: PriceData, warmupBars: int, start: str | None = None, end: str | None = None
) -> Window:
    days = indexDays(prices.frame)
    startDay = parseOptional(start, "start")
    endDay = parseOptional(end, "end")
    wanted = firstOnOrAfter(days, startDay)
    first = max(wanted, warmupBars - 1, 0)
    last = lastOnOrBefore(days, endDay)
    if last - first + 1 < 2:
        raise DataError(
            f"Fewer than 2 bars are left to test. The strategy needs {warmupBars} bars of "
            f"history before its first decision, and the data has {len(days)} bars "
            f"({formatDate(days[0])} to {formatDate(days[-1])}). Use a longer date range."
        )
    requested = startDay if startDay is not None else days[0]
    warnings: tuple[RunWarning, ...] = ()
    if days[first] > requested:
        warnings = (movedWarning(requested, days[first], first > wanted, warmupBars),)
    return Window(first, last, warnings)
