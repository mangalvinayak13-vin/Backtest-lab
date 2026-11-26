import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from plan import ETF, FALLEN, FILES, NIFTY, OLDER, PRICES, RECENT, STOCKS, Period

from backtestlab.api import downloadPrices, loadCsv
from backtestlab.csvsource import saveCsv
from backtestlab.prices import PriceData

INFO = PRICES / "downloaded.json"


# where the prices of one ticker for one period are saved
def pricePath(ticker: str, period: Period) -> Path:
    return PRICES / f"{FILES[ticker]}{period.start[:4]}.csv"


# the periods each ticker is needed for, oldest first
def periodsFor(ticker: str) -> tuple[Period, ...]:
    if ticker in (ETF, FALLEN):
        return (RECENT,)
    return (OLDER, RECENT)


# keep one period's rows, with enough history before it for the longest window
def cutPeriod(prices: PriceData, period: Period) -> PriceData:
    return replace(prices, frame=prices.frame.loc[period.historyFrom : period.end])


# download every ticker once and save one csv file for each period
def downloadAll() -> None:
    tickers = {}
    for ticker in (*STOCKS, NIFTY, ETF, FALLEN):
        periods = periodsFor(ticker)
        prices = downloadPrices(ticker, periods[0].historyFrom, periods[-1].end)
        for period in periods:
            saveCsv(cutPeriod(prices, period), pricePath(ticker, period))
        days = prices.frame.index
        tickers[ticker] = {
            "firstDate": days[0].date().isoformat(),
            "lastDate": days[-1].date().isoformat(),
            "bars": len(days),
        }
        print(f"Saved {ticker}: {len(days)} days from {tickers[ticker]['firstDate']}")
    info = {"downloaded": date.today().isoformat(), "tickers": tickers}
    with INFO.open("w", encoding="utf-8") as file:
        file.write(json.dumps(info, indent=2))


# the saved prices of one ticker for one period
def loadPeriod(ticker: str, period: Period) -> PriceData:
    return loadCsv(pricePath(ticker, period))


# the day the prices were downloaded
def downloadDate() -> str:
    with INFO.open(encoding="utf-8") as file:
        info = json.loads(file.read())
    return str(info["downloaded"])


# the ETF's data notes, and the index to use instead when they show an unadjusted split
def chooseIndexAsset() -> tuple[str, tuple[str, ...]]:
    notes = loadPeriod(ETF, RECENT).notes
    broken = tuple(note for note in notes if "split or bonus" in note)
    return (NIFTY if broken else ETF), broken
