import statistics
from datetime import datetime

import pandas as pd

TOLERANCE = 1e-6
BIGMOVE = 0.35
BIGGAPDAYS = 10
DAILYGAPDAYS = 3
SHOWN = 5


# the first few dates as text, with a count of the rest
def listDates(days: list[datetime]) -> str:
    shown = ", ".join(day.date().isoformat() for day in days[:SHOWN])
    if len(days) > SHOWN:
        return f"{shown} and {len(days) - SHOWN} more"
    return shown


# the dates of the index as plain datetimes
def indexDays(frame: pd.DataFrame) -> list[datetime]:
    return [datetime(stamp.year, stamp.month, stamp.day) for stamp in frame.index]


# the dates where the high is too low or the low is too high
def badRangeDays(frame: pd.DataFrame) -> list[datetime]:
    top = frame[["open", "close"]].max(axis=1)
    bottom = frame[["open", "close"]].min(axis=1)
    bad = (frame["high"] < top * (1 - TOLERANCE)) | (frame["low"] > bottom * (1 + TOLERANCE))
    return [day for day, isBad in zip(indexDays(frame), bad.values, strict=True) if isBad]


# a warning when the high or low does not fit the open and close
def rangeWarnings(frame: pd.DataFrame) -> list[str]:
    days = badRangeDays(frame)
    if not days:
        return []
    return [
        f"{len(days)} rows have a high below the open or close, or a low above it "
        f"(first dates: {listDates(days)}). The data may be wrong."
    ]


# a warning for each very large one-day move in the close
def jumpWarnings(frame: pd.DataFrame) -> list[str]:
    closes = [float(price) for price in frame["close"].values]
    days = indexDays(frame)
    found = []
    for position in range(1, len(closes)):
        move = closes[position] / closes[position - 1] - 1
        if abs(move) > BIGMOVE:
            found.append(f"{days[position].date().isoformat()} ({move * 100:+.1f}%)")
    if not found:
        return []
    where = ", ".join(found[:SHOWN])
    return [
        f"The close moved by more than {BIGMOVE * 100:.0f}% in one day on {where}. "
        "This is often a split or bonus issue that was not adjusted for."
    ]


# the number of calendar days between each date and the next
def gapSizes(days: list[datetime]) -> list[int]:
    return [(days[position] - days[position - 1]).days for position in range(1, len(days))]


# warnings about long gaps between dates and about data that is not daily
def gapWarnings(frame: pd.DataFrame) -> list[str]:
    days = indexDays(frame)
    gaps = gapSizes(days)
    warnings = []
    afterGaps = [days[position + 1] for position, gap in enumerate(gaps) if gap > BIGGAPDAYS]
    if afterGaps:
        warnings.append(
            f"Some dates are more than {BIGGAPDAYS} days after the one before, so data may be "
            f"missing (dates after the gap: {listDates(afterGaps)})."
        )
    median = statistics.median(gaps)
    if median > DAILYGAPDAYS:
        warnings.append(
            f"The dates are a median of {median:g} days apart, so the data does not look daily. "
            "Annualised numbers assume daily data."
        )
    return warnings


# every data warning for a cleaned table of prices
def findWarnings(frame: pd.DataFrame) -> list[str]:
    return rangeWarnings(frame) + jumpWarnings(frame) + gapWarnings(frame)
