import math
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from backtestlab.errors import DataError
from backtestlab.pricewarnings import findWarnings, listDates

# the two notes a loader records when the prices have been adjusted
CSVADJUSTED = "Prices were adjusted for dividends and splits using the Adj Close column."
YAHOOADJUSTED = "Prices come from Yahoo Finance and are adjusted for splits and dividends."


# daily prices as a table of dates and floats, with where they came from
@dataclass(frozen=True)
class PriceData:
    frame: pd.DataFrame
    source: str
    notes: tuple[str, ...]


# one day of raw prices as read from a file or a download, with nan for a missing value
@dataclass(frozen=True)
class Row:
    day: datetime
    openPrice: float
    highPrice: float
    lowPrice: float
    closePrice: float
    volume: float

    # the four prices in order
    def prices(self) -> tuple[float, float, float, float]:
        return (self.openPrice, self.highPrice, self.lowPrice, self.closePrice)


# a column name written the same way every time, so Adj Close becomes adjclose
def cleanHeader(name: str) -> str:
    return "".join(name.split()).lower()


# a price must be a real number above zero
def goodPrice(value: float) -> bool:
    return math.isfinite(value) and value > 0


# a row with no prices at all is a placeholder for a day without trading
def isEmptyRow(row: Row) -> bool:
    return all(math.isnan(price) for price in row.prices())


# drop the empty rows and add a note saying how many went
def dropEmptyRows(rows: list[Row], notes: list[str]) -> list[Row]:
    kept = [row for row in rows if not isEmptyRow(row)]
    dropped = len(rows) - len(kept)
    if dropped:
        notes.append(f"Dropped {dropped} rows that had no prices (probably days without trading).")
    return kept


# stop when a price is missing, not a number, zero or negative
def checkPrices(rows: list[Row]) -> None:
    bad = [row.day for row in rows if not all(goodPrice(price) for price in row.prices())]
    if bad:
        raise DataError(
            f"These dates have a missing, infinite, zero or negative price: {listDates(bad)}. "
            "Fix or remove those rows."
        )


# stop when a volume is negative, a missing volume is fine
def checkVolumes(rows: list[Row]) -> None:
    bad = [row.day for row in rows if row.volume < 0]
    if bad:
        raise DataError(f"These dates have a negative volume: {listDates(bad)}.")


# stop when two rows have the same date
def checkDuplicates(rows: list[Row]) -> None:
    seen: set[datetime] = set()
    repeated = []
    for row in rows:
        if row.day in seen:
            repeated.append(row.day)
        seen.add(row.day)
    if repeated:
        raise DataError(f"These dates appear more than once: {listDates(repeated)}.")


# sort the rows by date and add a note if they were not sorted already
def sortRows(rows: list[Row], notes: list[str]) -> list[Row]:
    ordered = sorted(rows, key=lambda row: row.day)
    if [row.day for row in ordered] != [row.day for row in rows]:
        notes.append("The dates were not in ascending order, so the rows were sorted.")
    return ordered


# the table of prices, with a date index called date
def buildFrame(rows: list[Row], hasVolume: bool) -> pd.DataFrame:
    index = pd.DatetimeIndex([row.day for row in rows], name="date")
    columns = {
        "open": [row.openPrice for row in rows],
        "high": [row.highPrice for row in rows],
        "low": [row.lowPrice for row in rows],
        "close": [row.closePrice for row in rows],
    }
    if hasVolume:
        columns["volume"] = [row.volume for row in rows]
    return pd.DataFrame(columns, index=index)


# check and clean raw rows (notes already recorded by the loader are kept and added to)
def buildPrices(rows: list[Row], hasVolume: bool, source: str, notes: list[str]) -> PriceData:
    kept = dropEmptyRows(rows, notes)
    checkPrices(kept)
    checkVolumes(kept)
    checkDuplicates(kept)
    ordered = sortRows(kept, notes)
    if len(ordered) < 2:
        raise DataError(
            f"Only {len(ordered)} rows of prices were found, and at least 2 are needed."
        )
    frame = buildFrame(ordered, hasVolume)
    return PriceData(frame, source, tuple(notes + findWarnings(frame)))
