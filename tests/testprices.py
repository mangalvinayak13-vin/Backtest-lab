import math
from datetime import datetime, timedelta

import pandas as pd
import pytest

from backtestlab.errors import DataError
from backtestlab.prices import Row, buildPrices, cleanHeader
from backtestlab.pricewarnings import listDates

FIRST = datetime(2024, 1, 1)


# a normal row for day number n, with close 100 + n
def makeRow(n: int, **changes: float) -> Row:
    close = 100.0 + n
    values = {
        "openPrice": close,
        "highPrice": close + 1,
        "lowPrice": close - 1,
        "closePrice": close,
        "volume": 1000.0,
    }
    values.update(changes)
    return Row(FIRST + timedelta(days=n), **values)


# several normal rows in date order
def makeRows(count: int) -> list[Row]:
    return [makeRow(n) for n in range(count)]


# the table has a date index called date, no time zone, and float columns
def testFrameHasTheRightShape() -> None:
    data = buildPrices(makeRows(3), True, "test", [])
    assert data.frame.index.name == "date"
    assert isinstance(data.frame.index, pd.DatetimeIndex)
    assert data.frame.index.tz is None
    assert list(data.frame.columns) == ["open", "high", "low", "close", "volume"]
    assert data.source == "test"
    assert data.notes == ()
    assert float(data.frame["close"].iloc[2]) == 102.0


# without a volume column the table has only the four prices
def testNoVolumeColumnWhenThereIsNoVolume() -> None:
    data = buildPrices(makeRows(3), False, "test", [])
    assert list(data.frame.columns) == ["open", "high", "low", "close"]


# a missing volume stays as nan and is allowed
def testMissingVolumeIsAllowed() -> None:
    rows = [makeRow(0, volume=math.nan), makeRow(1)]
    data = buildPrices(rows, True, "test", [])
    assert math.isnan(float(data.frame["volume"].iloc[0]))


# every bad price is a data error that names the date
@pytest.mark.parametrize("bad", [0.0, -5.0, math.inf, math.nan])
def testBadPriceIsAnError(bad: float) -> None:
    rows = [makeRow(0), makeRow(1, lowPrice=bad), makeRow(2)]
    with pytest.raises(DataError, match="2024-01-02"):
        buildPrices(rows, True, "test", [])


# a negative volume is an error
def testNegativeVolumeIsAnError() -> None:
    rows = [makeRow(0), makeRow(1, volume=-1.0)]
    with pytest.raises(DataError, match="negative volume: 2024-01-02"):
        buildPrices(rows, True, "test", [])


# two rows with the same date are an error
def testDuplicateDatesAreAnError() -> None:
    rows = [makeRow(0), makeRow(1), makeRow(1)]
    with pytest.raises(DataError, match="more than once: 2024-01-02"):
        buildPrices(rows, True, "test", [])


# fewer than two rows is an error, including when the rest were empty
def testTooFewRowsIsAnError() -> None:
    with pytest.raises(DataError, match="Only 1 rows"):
        buildPrices(makeRows(1), True, "test", [])
    empty = makeRow(
        0, openPrice=math.nan, highPrice=math.nan, lowPrice=math.nan, closePrice=math.nan
    )
    with pytest.raises(DataError, match="Only 0 rows"):
        buildPrices([empty], True, "test", [])


# rows with no prices at all are dropped and counted in a note
def testEmptyRowsAreDropped() -> None:
    nothing = {"openPrice": math.nan, "highPrice": math.nan, "lowPrice": math.nan}
    rows = [makeRow(0), makeRow(1, closePrice=math.nan, **nothing), makeRow(2)]
    data = buildPrices(rows, True, "test", [])
    assert len(data.frame) == 2
    assert data.notes == ("Dropped 1 rows that had no prices (probably days without trading).",)


# newest-first rows are sorted and a note says so
def testRowsAreSortedWithANote() -> None:
    rows = list(reversed(makeRows(4)))
    data = buildPrices(rows, True, "test", [])
    assert list(data.frame.index) == sorted(data.frame.index)
    assert float(data.frame["close"].iloc[0]) == 100.0
    assert "not in ascending order" in data.notes[0]


# notes from the loader are kept
def testLoaderNotesAreKept() -> None:
    data = buildPrices(makeRows(3), True, "test", ["from the loader"])
    assert data.notes == ("from the loader",)


# a high below the close, or a low above the open, gives a warning
def testHighAndLowWarning() -> None:
    rows = [makeRow(0), makeRow(1, highPrice=100.0), makeRow(2, lowPrice=110.0)]
    data = buildPrices(rows, True, "test", [])
    assert len(data.notes) == 1
    assert "2 rows have a high below" in data.notes[0]


# a tiny rounding difference in the high is not a warning
def testTinyRoundingIsIgnored() -> None:
    rows = [makeRow(0), makeRow(1, highPrice=101.0 * (1 - 1e-9))]
    assert buildPrices(rows, True, "test", []).notes == ()


# a one-day move of more than 35% gives a warning with the date and size
def testBigJumpWarning() -> None:
    jump = {"openPrice": 140.0, "highPrice": 141.0, "lowPrice": 139.0, "closePrice": 140.0}
    rows = [makeRow(0), makeRow(1, **jump)]
    data = buildPrices(rows, True, "test", [])
    assert "2024-01-02 (+40.0%)" in data.notes[0]


# a move of 30% is fine
def testMoveOfThirtyPercentIsFine() -> None:
    same = {"openPrice": 130.0, "highPrice": 131.0, "lowPrice": 129.0, "closePrice": 130.0}
    rows = [makeRow(0), makeRow(1, **same)]
    assert buildPrices(rows, True, "test", []).notes == ()


# a gap of more than ten days gives a warning
def testLongGapWarning() -> None:
    rows = [makeRow(0), makeRow(1), makeRow(20), makeRow(21)]
    data = buildPrices(rows, True, "test", [])
    assert "more than 10 days" in data.notes[0]
    assert "2024-01-21" in data.notes[0]


# data that is not daily gives a warning about annualised numbers
def testNotDailyWarning() -> None:
    rows = [makeRow(n * 7) for n in range(5)]
    data = buildPrices(rows, True, "test", [])
    assert "median of 7 days" in data.notes[-1]


# a long list of dates is shortened
def testListDatesShortensLongLists() -> None:
    days = [FIRST + timedelta(days=n) for n in range(8)]
    assert listDates(days[:2]) == "2024-01-01, 2024-01-02"
    assert listDates(days).endswith("and 3 more")


# column names lose spaces and capital letters
def testCleanHeader() -> None:
    assert cleanHeader(" Adj Close ") == "adjclose"
