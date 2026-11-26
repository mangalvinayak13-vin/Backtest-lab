import sys
from dataclasses import dataclass, replace
from pathlib import Path

from backtestlab.api import Settings, presets

# the folder of crossover.py, the script that is run
HERE = Path(sys.argv[0]).resolve().parent
PRICES = HERE / "prices"
REPORTS = HERE / "reports"
CHARTS = HERE / "charts"

STOCKS = ("TCS.NS", "RELIANCE.NS", "HDFCBANK.NS")
NIFTY = "^NSEI"
ETF = "NIFTYBEES.NS"
FALLEN = "YESBANK.NS"

# the short names used for the price files and the charts
NAMES = {
    "TCS.NS": "TCS",
    "RELIANCE.NS": "Reliance",
    "HDFCBANK.NS": "HDFC Bank",
    "NIFTYBEES.NS": "NIFTYBEES",
    "YESBANK.NS": "YES Bank",
    "^NSEI": "NIFTY 50",
}
FILES = {
    "TCS.NS": "tcs",
    "RELIANCE.NS": "reliance",
    "HDFCBANK.NS": "hdfcbank",
    "NIFTYBEES.NS": "niftybees",
    "YESBANK.NS": "yesbank",
    "^NSEI": "nifty50",
}

PROMISED = (100, 150, 175, 200)
SHORTS = (10, 20, 50, 100)
LONGS = (100, 125, 150, 175, 200, 250)
SEEDS = (1, 2, 3, 4, 5)


# one test period, with the year whose crash we look at on its own
@dataclass(frozen=True)
class Period:
    name: str
    start: str
    end: str
    crashYear: int
    historyFrom: str


RECENT = Period("2018to2024", "2018-01-01", "2024-12-31", 2020, "2016-06-01")
OLDER = Period("2008to2017", "2008-01-01", "2017-12-31", 2008, "2006-06-01")


# one backtest to run
@dataclass(frozen=True)
class Run:
    part: str
    period: Period
    ticker: str
    shortWindow: int
    longWindow: int
    seed: int

    # a short label that names the run in results.csv
    def label(self) -> str:
        return (
            f"{self.part} {self.period.name} {self.ticker} "
            f"{self.shortWindow}/{self.longWindow} seed {self.seed}"
        )


# the india preset as it is, with fractional shares only for the index
def settingsFor(run: Run) -> Settings:
    settings = replace(presets.INDIA, seed=run.seed)
    if run.ticker == NIFTY:
        settings = replace(settings, wholeShares=False)
    return settings


# the 12 promised tests, for one period and one seed
def promisedRuns(part: str, period: Period, seed: int) -> list[Run]:
    return [
        Run(part, period, ticker, 50, longWindow, seed)
        for ticker in STOCKS
        for longWindow in PROMISED
    ]


# the wider grid of windows, leaving out the four promised ones
def plateauRuns() -> list[Run]:
    runs = []
    for ticker in STOCKS:
        for shortWindow in SHORTS:
            for longWindow in LONGS:
                promised = shortWindow == 50 and longWindow in PROMISED
                if shortWindow < longWindow and not promised:
                    runs.append(Run("2-plateau", RECENT, ticker, shortWindow, longWindow, 42))
    return runs


# the promised settings on the index and on a stock that collapsed
def assetRuns(indexAsset: str) -> list[Run]:
    return [
        Run("2-assets", RECENT, ticker, 50, longWindow, 42)
        for ticker in (indexAsset, FALLEN)
        for longWindow in PROMISED
    ]


# every run, in the order it appears in results.csv
def allRuns(indexAsset: str) -> list[Run]:
    runs = promisedRuns("1", RECENT, 42)
    for seed in SEEDS:
        runs += promisedRuns("2-seeds", RECENT, seed)
    runs += plateauRuns()
    runs += promisedRuns("2-crash", OLDER, 42)
    return runs + assetRuns(indexAsset)
