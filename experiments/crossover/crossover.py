import sys

from crosscheck import Check, checkRun
from figures import drawAll
from page import Context, writePage
from plan import FILES, HERE, NIFTY, RECENT, REPORTS, STOCKS, Period, Run, allRuns, settingsFor
from pricefiles import chooseIndexAsset, downloadAll, downloadDate, loadPeriod
from records import Row, buildRow, writeRows

from backtestlab.api import MovingAverageCrossover, runBacktest, writeReport, writeResultsFile
from backtestlab.backtest import BacktestResult
from backtestlab.prices import PriceData

# the parts whose full results are kept for the charts, the page and the html reports
KEEP = ("1", "2-crash", "2-assets")

PriceCache = dict[tuple[str, str], PriceData]


# the saved prices of one ticker for one period, loaded only once
def cachedPrices(ticker: str, period: Period, cache: PriceCache) -> PriceData:
    key = (ticker, period.name)
    if key not in cache:
        cache[key] = loadPeriod(ticker, period)
    return cache[key]


# one backtest through the library, from the saved prices, with NIFTY 50 as the benchmark
def runOne(run: Run, cache: PriceCache) -> BacktestResult:
    prices = cachedPrices(run.ticker, run.period, cache)
    benchmark = cachedPrices(NIFTY, run.period, cache)
    strategy = MovingAverageCrossover(shortWindow=run.shortWindow, longWindow=run.longWindow)
    settings = settingsFor(run)
    return runBacktest(prices, strategy, settings, run.period.start, run.period.end, benchmark)


# the tool's own html report and json file for one run, kept out of git
def saveReport(run: Run, result: BacktestResult) -> None:
    if not REPORTS.exists():
        REPORTS.mkdir(parents=True)
    name = f"{run.part}-{run.period.name}-{FILES[run.ticker]}-{run.shortWindow}-{run.longWindow}"
    writeReport(result, REPORTS / f"{name}.html")
    writeResultsFile(result, REPORTS / f"{name}.json")


# the hand-worked checks on the 50/200 run of each stock
def crossChecks(kept: dict[Run, BacktestResult]) -> list[Check]:
    checks = []
    for run, result in kept.items():
        if run.part == "1" and run.longWindow == 200 and run.ticker in STOCKS:
            checks += checkRun(result, run.ticker, run.shortWindow, run.longWindow)
    return checks


# run every test, write results.csv and the reports, and keep what the page needs
def runEverything(indexAsset: str) -> tuple[list[Row], dict[Run, BacktestResult]]:
    cache: PriceCache = {}
    rows = []
    kept = {}
    runs = allRuns(indexAsset)
    for number, run in enumerate(runs, start=1):
        result = runOne(run, cache)
        rows.append(buildRow(run, result))
        if run.part in KEEP:
            kept[run] = result
            saveReport(run, result)
        if number % 25 == 0 or number == len(runs):
            print(f"Ran {number} of {len(runs)} backtests")
    writeRows(rows, HERE / "results.csv")
    return rows, kept


# rebuild every number, chart and the results page from the saved prices
def rebuild() -> int:
    indexAsset, etfNotes = chooseIndexAsset()
    rows, kept = runEverything(indexAsset)
    checks = crossChecks(kept)
    context = Context(downloadDate(), indexAsset, etfNotes, RECENT)
    drawAll(rows, kept)
    writePage(rows, kept, checks, context)
    failed = [check for check in checks if not check.matches()]
    for check in failed:
        print(f"Check failed for {check.ticker}, {check.name}: {check.byHand} against {check.tool}")
    print(f"{len(checks) - len(failed)} of {len(checks)} hand-worked checks match the tool")
    return 1 if failed else 0


# "download" saves the prices, "run" rebuilds everything from them
def main() -> int:
    command = sys.argv[1:]
    if command == ["download"]:
        downloadAll()
        return 0
    if command == ["run"]:
        return rebuild()
    print("Use: python experiments/crossover/crossover.py download, then the same with run")
    return 1


sys.exit(main())
