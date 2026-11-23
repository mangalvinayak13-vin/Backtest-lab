import logging
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance

from backtestlab.dates import parseDay
from backtestlab.errors import DataError, SettingsError
from backtestlab.prices import PriceData, Row, buildPrices, cleanHeader

REQUIRED = ("open", "high", "low", "close")
ADVICE = (
    "Check the ticker (Indian stocks end in .NS or .BO). Yahoo may be limiting requests, "
    "so try again later, or use a CSV file with --csv."
)
ADJUSTED = "Prices come from Yahoo Finance and are adjusted for splits and dividends."


# the first day to ask for, and the day after the last one because Yahoo excludes the end
def requestDays(start: date, end: date, historyBars: int) -> tuple[str, str]:
    earlier = start - timedelta(days=2 * historyBars + 30)
    return earlier.isoformat(), (end + timedelta(days=1)).isoformat()


# ask Yahoo for the daily table, turning every failure into a data error
def fetchTable(ticker: str, begin: str, finish: str) -> pd.DataFrame:
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    try:
        table = yfinance.Ticker(ticker).history(
            start=begin, end=finish, interval="1d", actions=False
        )
    except Exception as error:
        raise DataError(
            f"Could not download {ticker} from Yahoo Finance ({error}). {ADVICE}"
        ) from error
    if table is None or len(table) == 0:
        raise DataError(f"Yahoo Finance returned no prices for {ticker}. {ADVICE}")
    return pd.DataFrame(table)


# the table columns by their cleaned names, stopping if a price column is missing
def findColumns(table: pd.DataFrame) -> dict[str, str]:
    columns = {cleanHeader(str(name)): str(name) for name in table.columns}
    missing = [name for name in REQUIRED if name not in columns]
    if missing:
        found = ", ".join(str(name) for name in table.columns)
        raise DataError(
            f"The Yahoo Finance table has no {', '.join(missing)} column. Found: {found}."
        )
    return columns


# the numbers of one column as plain floats
def columnValues(table: pd.DataFrame, name: str) -> list[float]:
    return [float(value) for value in table[name].values]


# turn the Yahoo table into raw rows, keeping the calendar date of each bar
def makeRows(table: pd.DataFrame, columns: dict[str, str]) -> list[Row]:
    days = [datetime(stamp.year, stamp.month, stamp.day) for stamp in table.index]
    opens, highs, lows, closes = (columnValues(table, columns[name]) for name in REQUIRED)
    volumes = [float("nan")] * len(days)
    if "volume" in columns:
        volumes = columnValues(table, columns["volume"])
    return [
        Row(
            days[position],
            opens[position],
            highs[position],
            lows[position],
            closes[position],
            volumes[position],
        )
        for position in range(len(days))
    ]


# download daily prices from Yahoo Finance, with extra history before start for the warm-up
def downloadPrices(ticker: str, start: str, end: str, historyBars: int = 0) -> PriceData:
    first = parseDay(start, "start")
    last = parseDay(end, "end")
    if last < first:
        raise SettingsError(f"The end date {end} is before the start date {start}.")
    begin, finish = requestDays(first, last, historyBars)
    table = fetchTable(ticker, begin, finish)
    columns = findColumns(table)
    rows = makeRows(table, columns)
    return buildPrices(rows, "volume" in columns, f"{ticker} (Yahoo Finance)", [ADJUSTED])
