from datetime import datetime
from typing import Any

import pandas as pd
import pytest
import yfinance

from backtestlab.errors import DataError, SettingsError
from backtestlab.yahoosource import downloadPrices

CALLS: list[dict[str, Any]] = []


# a table like the one yfinance gives, with dates that carry the Indian time zone
def makeTable(columns: list[str] | None = None) -> pd.DataFrame:
    days = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"], tz="Asia/Kolkata")
    names = columns or ["Open", "High", "Low", "Close", "Volume"]
    values = {name: [100.0 + n for n in range(3)] for name in names}
    return pd.DataFrame(values, index=days)


# put a fake Ticker in place of the real one, answering with the given result
def fakeYahoo(monkeypatch: pytest.MonkeyPatch, answer: object) -> None:
    CALLS.clear()

    class FakeTicker:
        def history(self, **options: Any) -> object:
            CALLS[-1].update(options)
            if isinstance(answer, Exception):
                raise answer
            return answer

    # the fake Ticker function remembers the symbol it was made with
    def makeTicker(symbol: str) -> FakeTicker:
        CALLS.append({"symbol": symbol})
        return FakeTicker()

    monkeypatch.setattr(yfinance, "Ticker", makeTicker)


# the download gives the same table shape as the csv loader
def testDownloadGivesCleanPrices(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, makeTable())
    data = downloadPrices("TCS.NS", "2024-01-02", "2024-01-04")
    assert isinstance(data.frame.index, pd.DatetimeIndex)
    assert data.frame.index.tz is None
    assert data.frame.index.name == "date"
    assert data.frame.index[0] == datetime(2024, 1, 2)
    assert list(data.frame.columns) == ["open", "high", "low", "close", "volume"]
    assert data.source == "TCS.NS (Yahoo Finance)"
    assert "adjusted for splits and dividends" in data.notes[0]


# yfinance is asked for daily bars without actions, and the end date is made inclusive
def testRequestIsDailyAndEndIsInclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, makeTable())
    downloadPrices("TCS.NS", "2024-01-02", "2024-01-31")
    assert CALLS[0]["symbol"] == "TCS.NS"
    assert CALLS[0]["interval"] == "1d"
    assert CALLS[0]["actions"] is False
    assert CALLS[0]["end"] == "2024-02-01"
    assert CALLS[0]["start"] == "2023-12-03"


# history bars move the first requested day earlier
def testHistoryBarsAskForEarlierDays(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, makeTable())
    downloadPrices("TCS.NS", "2024-01-02", "2024-01-31", historyBars=200)
    assert CALLS[0]["start"] == "2022-10-29"


# a table with no rows is a data error with advice
def testEmptyTable(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, pd.DataFrame())
    with pytest.raises(DataError, match=r"no prices for TCS.NS.*\.NS or \.BO.*--csv"):
        downloadPrices("TCS.NS", "2024-01-02", "2024-01-04")


# no table at all is a data error
def testNoTable(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, None)
    with pytest.raises(DataError, match="no prices for BAD"):
        downloadPrices("BAD", "2024-01-02", "2024-01-04")


# an exception from yfinance becomes a data error that repeats the reason
def testFailedDownload(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, RuntimeError("rate limited"))
    with pytest.raises(DataError, match=r"Could not download TCS.NS.*rate limited.*try again"):
        downloadPrices("TCS.NS", "2024-01-02", "2024-01-04")


# a table without a price column is a data error that lists what came back
def testMissingColumn(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, makeTable(["Open", "High", "Close"]))
    with pytest.raises(DataError, match=r"no low column. Found: Open, High, Close"):
        downloadPrices("TCS.NS", "2024-01-02", "2024-01-04")


# a table without volume still loads
def testNoVolumeIsFine(monkeypatch: pytest.MonkeyPatch) -> None:
    fakeYahoo(monkeypatch, makeTable(["Open", "High", "Low", "Close"]))
    data = downloadPrices("TCS.NS", "2024-01-02", "2024-01-04")
    assert "volume" not in data.frame.columns


# the same checks as the csv loader apply to downloaded prices
def testDownloadedPricesAreChecked(monkeypatch: pytest.MonkeyPatch) -> None:
    table = makeTable()
    table.iloc[1, 3] = -1.0
    fakeYahoo(monkeypatch, table)
    with pytest.raises(DataError, match="2024-01-03"):
        downloadPrices("TCS.NS", "2024-01-02", "2024-01-04")


# bad dates are setting errors
def testBadDates() -> None:
    with pytest.raises(SettingsError, match="start date 'soon'"):
        downloadPrices("TCS.NS", "soon", "2024-01-04")
    with pytest.raises(SettingsError, match="end date '31/01/2024'"):
        downloadPrices("TCS.NS", "2024-01-02", "31/01/2024")
    with pytest.raises(SettingsError, match="before the start date"):
        downloadPrices("TCS.NS", "2024-02-02", "2024-01-04")
