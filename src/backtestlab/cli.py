import shlex
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from backtestlab.api import VERSION
from backtestlab.arguments import Options, parseOptions
from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.csvsource import loadCsv, saveCsv
from backtestlab.dates import parseDay
from backtestlab.errors import BacktestLabError, DataError, SettingsError
from backtestlab.presets import DEFAULT, INDIA
from backtestlab.prices import PriceData
from backtestlab.report import writeReport
from backtestlab.resultsfile import writeResultsFile
from backtestlab.runwarning import RunWarning
from backtestlab.settings import Settings
from backtestlab.strategies import REGISTRY, describeParameters, makeStrategy
from backtestlab.strategy import Strategy
from backtestlab.terminal import runLines
from backtestlab.yahoosource import downloadPrices

PRESETS = {"default": DEFAULT, "india": INDIA}
TENYEARS = timedelta(days=3652)
HELPLINES = (
    "backtestlab: an honest backtester for daily prices",
    "",
    "It runs a trading strategy over past prices, with costs, and compares it with simply",
    "holding the asset. It writes an HTML report and a JSON results file.",
    "",
    "Usage:",
    "  backtestlab run (--ticker SYMBOL | --csv PATH) --strategy NAME",
    "                  [--param NAME=VALUE ...] [--start YYYY-MM-DD] [--end YYYY-MM-DD]",
    "                  [--preset default|india] [--cash AMOUNT] [--fractional-shares]",
    "                  [--benchmark SYMBOL|none] [--simulations N] [--seed N]",
    "                  [--output report.html] [--save-data PATH] [--date-format FORMAT]",
    "  backtestlab strategies",
    "  backtestlab --version",
    "  backtestlab --help",
    "",
    "Examples:",
    "  backtestlab run --ticker TCS.NS --strategy ma-crossover --preset india "
    "--start 2018-01-01 --end 2024-12-31",
    "  backtestlab run --csv data/sampleprices.csv --strategy ma-crossover "
    "--param shortWindow=20 --param longWindow=100",
    "",
    "For education only. Not investment advice.",
)


# print the help text
def showHelp() -> int:
    print("\n".join(HELPLINES))
    return 0


# print the version number
def showVersion() -> int:
    print(f"backtestlab {VERSION}")
    return 0


# print every strategy with its description and parameters
def showStrategies() -> int:
    for name, strategyClass in REGISTRY.items():
        print(name)
        print(f"  {strategyClass.description}")
        parameters = describeParameters(name)
        for parameter, kind, default in parameters:
            print(f"  {parameter} ({kind}, default {default})")
        if not parameters:
            print("  No parameters.")
        print()
    return 0


# a whole number from an option, or a clear error
def wholeNumber(options: Options, name: str) -> int | None:
    text = options.get(name)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        raise SettingsError(f"{name} should be a whole number, but got '{text}'.") from None


# the starting cash from --cash, or None when it was not given
def cashAmount(options: Options) -> float | None:
    text = options.get("--cash")
    if text is None:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        raise SettingsError(
            f"--cash should be an amount such as 100000, but got '{text}'."
        ) from None


# the preset with the changes asked for on the command line
def buildSettings(options: Options) -> Settings:
    name = options.get("--preset") or "default"
    if name not in PRESETS:
        raise SettingsError(f"unknown preset '{name}'. Valid presets: default, india.")
    settings = PRESETS[name]
    changes: dict[str, Any] = {}
    cash = cashAmount(options)
    if cash is not None:
        changes["startingCash"] = cash
    if "--fractional-shares" in options.flags:
        changes["wholeShares"] = False
    for option, field in (("--simulations", "simulations"), ("--seed", "seed")):
        number = wholeNumber(options, option)
        if number is not None:
            changes[field] = number
    return replace(settings, **changes)


# stop early when the options don't fit together
def checkCombinations(options: Options) -> None:
    hasTicker, hasCsv = options.get("--ticker") is not None, options.get("--csv") is not None
    if hasTicker == hasCsv:
        raise SettingsError("give exactly one of --ticker and --csv.")
    if options.get("--strategy") is None:
        valid = ", ".join(REGISTRY)
        raise SettingsError(f"--strategy is needed. Valid strategies: {valid}.")
    if options.get("--save-data") is not None and not hasTicker:
        raise SettingsError("--save-data only works with --ticker.")
    if options.get("--date-format") is not None and not hasCsv:
        raise SettingsError("--date-format only works with --csv.")
    outputPaths(options)


# the start and end dates for a download: by default the last ten years up to today
def downloadDates(options: Options) -> tuple[str, str]:
    end = options.get("--end") or date.today().isoformat()
    tenYearsBefore = (parseDay(end, "end") - TENYEARS).isoformat()
    return options.get("--start") or tenYearsBefore, end


# load the prices from the file or from Yahoo, saving a download when asked
def loadPrices(options: Options, strategy: Strategy) -> tuple[PriceData, str | None, str | None]:
    csvPath = options.get("--csv")
    if csvPath is not None:
        print(f"Loading {csvPath}")
        return (
            loadCsv(csvPath, options.get("--date-format")),
            options.get("--start"),
            options.get("--end"),
        )
    ticker = options.get("--ticker") or ""
    start, end = downloadDates(options)
    print(f"Downloading {ticker} from Yahoo Finance")
    prices = downloadPrices(ticker, start, end, historyBars=strategy.warmupBars)
    savePath = options.get("--save-data")
    if savePath is not None:
        try:
            saveCsv(prices, savePath)
        except OSError as error:
            raise writeFailure(savePath, error) from error
        print(f"Saved the prices to {savePath}")
    return prices, start, end


# the index to compare with, or None, and a warning when it could not be downloaded
def loadBenchmark(
    options: Options, settings: Settings, prices: PriceData
) -> tuple[Settings, PriceData | None, RunWarning | None]:
    chosen = options.get("--benchmark") or settings.benchmarkTicker
    if chosen is None or chosen.lower() == "none":
        return settings, None, None
    if chosen != settings.benchmarkTicker:
        settings = replace(settings, benchmarkTicker=chosen, benchmarkLabel=chosen)
    days = [stamp.date().isoformat() for stamp in prices.frame.index]
    print(f"Downloading the benchmark {chosen}")
    try:
        return settings, downloadPrices(chosen, days[0], days[-1]), None
    except DataError as error:
        return (
            settings,
            None,
            RunWarning("benchmark-missing", f"The benchmark could not be loaded. {error}"),
        )


# the report path and the results path next to it
def outputPaths(options: Options) -> tuple[Path, Path]:
    report = Path(options.get("--output") or "report.html")
    # lower case too, because some computers treat res.JSON and res.json as one file
    if report.suffix.lower() == ".json":
        raise SettingsError(
            "--output is the name of the HTML report, so it can't end in .json. Use a name "
            "such as report.html, and the .json file is written next to it."
        )
    return report, report.parent / f"{report.stem}.json"


# the error for a file that could not be written
def writeFailure(path: str | Path, error: OSError) -> SettingsError:
    return SettingsError(
        f"could not write {path} ({error.strerror}). Check that it is a file you can "
        "write to, and not a folder."
    )


# run one backtest from the command line and write both files
def runCommand(arguments: list[str]) -> int:
    options = parseOptions(arguments)
    checkCombinations(options)
    settings = buildSettings(options)
    strategy = makeStrategy(options.get("--strategy") or "", options.repeated["--param"])
    prices, start, end = loadPrices(options, strategy)
    settings, benchmark, missing = loadBenchmark(options, settings, prices)
    print("Running the backtest")
    result = runBacktest(prices, strategy, settings, start, end, benchmark)
    if missing is not None:
        result = replace(result, warnings=(*result.warnings, missing))
    return writeOutputs(result, options, arguments)


# write the report and then the results file, naming the one that fails
def saveOutputs(result: BacktestResult, report: Path, results: Path, command: str) -> None:
    try:
        writeReport(result, report, command)
    except OSError as error:
        raise writeFailure(report, error) from error
    try:
        writeResultsFile(result, results)
    except OSError as error:
        raise writeFailure(results, error) from error


# write both files, then print what happened
def writeOutputs(result: BacktestResult, options: Options, arguments: list[str]) -> int:
    report, results = outputPaths(options)
    print("Writing the report")
    saveOutputs(result, report, results, shlex.join(["backtestlab", "run", *arguments]))
    print()
    print("\n".join(runLines(result, str(report), str(results))))
    return 0


# pick the command from the arguments and run it
def chooseCommand(arguments: list[str]) -> int:
    if not arguments or arguments[0] in ("--help", "-h", "help"):
        return showHelp()
    if arguments[0] == "--version":
        return showVersion()
    if arguments[0] == "strategies":
        return showStrategies()
    if arguments[0] == "run":
        return runCommand(arguments[1:])
    raise SettingsError(f"unknown command or option '{arguments[0]}'. Try backtestlab --help")


# the entry point of the command, returns the exit code
def main(arguments: list[str] | None = None) -> int:
    if arguments is None:
        arguments = sys.argv[1:]
    try:
        return chooseCommand(arguments)
    except BacktestLabError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
