import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yfinance
from helpers import randomPrices

from backtestlab.api import VERSION
from backtestlab.cli import main
from backtestlab.csvsource import loadCsv

SAMPLE = "data/sampleprices.csv"


# run the command from the repository folder, writing into the work folder
def runIn(monkeypatch: pytest.MonkeyPatch, root: Path, arguments: list[str]) -> int:
    monkeypatch.chdir(root)
    return main(arguments)


# a fake Yahoo that serves random prices, and fails for the symbols given
def fakeYahoo(monkeypatch: pytest.MonkeyPatch, failing: tuple[str, ...] = ()) -> list[str]:
    asked: list[str] = []

    class FakeTicker:
        def history(self, **options: Any) -> pd.DataFrame:
            frame = randomPrices(len(asked), 300).frame
            table = frame.rename(columns=str.title)
            table.index = pd.DatetimeIndex(frame.index, tz="Asia/Kolkata")
            return table

    # make a fake ticker, or fail like Yahoo does for a bad symbol
    def makeTicker(symbol: str) -> FakeTicker:
        asked.append(symbol)
        if symbol in failing:
            raise RuntimeError("no data")
        return FakeTicker()

    monkeypatch.setattr(yfinance, "Ticker", makeTicker)
    return asked


# the version flag prints the name and the installed version
def testVersionPrintsNameAndVersion(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"backtestlab {VERSION}"


# the help flag prints the usage and both examples
def testHelpPrintsUsage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "Usage:" in out
    assert "backtestlab run --ticker TCS.NS --strategy ma-crossover --preset india" in out
    assert "backtestlab run --csv data/sampleprices.csv --strategy ma-crossover" in out


# running with no arguments shows the help instead of failing
def testNoArgumentsShowsHelp(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "Usage:" in capsys.readouterr().out


# a wrong command gives a one-line error and exit code 1, with no traceback
def testUnknownCommand(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--nonsense"]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("Error: unknown command or option '--nonsense'")
    assert "Traceback" not in captured.err


# main reads the real command line when it is given no list
def testMainReadsTheCommandLine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["backtestlab", "--version"])
    assert main() == 0
    assert VERSION in capsys.readouterr().out


# the strategies command lists names, descriptions and parameters with defaults
def testStrategiesCommand(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["strategies"]) == 0
    out = capsys.readouterr().out
    assert "buy-and-hold\n  Buys on the first day" in out
    assert "No parameters." in out
    assert "shortWindow (int, default 50)" in out
    assert "longWindow (int, default 200)" in out


# a run on the csv sample writes both files and prints the results
def testRunWritesBothFiles(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pytestconfig: pytest.Config,
    workdir: Path,
) -> None:
    output = workdir / "out" / "result.html"
    arguments = ["run", "--csv", SAMPLE, "--strategy", "ma-crossover", "--param", "shortWindow=20"]
    code = runIn(monkeypatch, pytestconfig.rootpath, [*arguments, "--output", str(output)])
    assert code == 0
    assert output.exists()
    with (workdir / "out" / "result.json").open(encoding="utf-8") as file:
        assert json.loads(file.read())["schemaVersion"] == 1
    out = capsys.readouterr().out
    assert "Strategy  Moving average crossover (shortWindow=20, longWindow=200)" in out
    assert "Total return" in out
    assert f"Report saved to {output} and" in out
    assert out.rstrip().endswith("For education only. Not investment advice.")


# the settings options change the run
def testSettingsOptions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pytestconfig: pytest.Config,
    workdir: Path,
) -> None:
    arguments = [
        "run",
        "--csv",
        SAMPLE,
        "--strategy",
        "buy-and-hold",
        "--preset",
        "india",
        "--cash",
        "2,00,000",
        "--fractional-shares",
        "--simulations",
        "200",
        "--seed",
        "3",
        "--benchmark",
        "none",
        "--start",
        "2020-01-01",
        "--end",
        "2022-12-30",
        "--output",
        str(workdir / "report.html"),
    ]
    assert runIn(monkeypatch, pytestconfig.rootpath, arguments) == 0
    with (workdir / "report.json").open(encoding="utf-8") as file:
        data = json.loads(file.read())
    assert data["settings"]["startingCash"] == 200000.0
    assert data["settings"]["wholeShares"] is False
    assert data["settings"]["simulations"] == 200
    assert data["settings"]["seed"] == 3
    assert data["window"]["firstDate"] == "2020-01-01"
    assert data["benchmark"] is None


# a download runs, saves the cleaned prices, and those prices load back the same
def testTickerRunAndSaveData(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pytestconfig: pytest.Config,
    workdir: Path,
) -> None:
    asked = fakeYahoo(monkeypatch)
    saved = workdir / "saved" / "prices.csv"
    arguments = [
        "run",
        "--ticker",
        "TCS.NS",
        "--strategy",
        "ma-crossover",
        "--param",
        "shortWindow=5",
        "--param",
        "longWindow=20",
        "--benchmark",
        "^GSPC",
        "--save-data",
        str(saved),
        "--start",
        "2024-01-25",
        "--end",
        "2024-10-01",
        "--output",
        str(workdir / "report.html"),
    ]
    assert runIn(monkeypatch, pytestconfig.rootpath, arguments) == 0
    assert asked == ["TCS.NS", "^GSPC"]
    first = loadCsv(saved)
    assert first.frame.equals(loadCsv(saved).frame)
    assert len(first.frame) == 300
    out = capsys.readouterr().out
    assert "^GSPC" in out


# a benchmark that can't be downloaded becomes a warning and the run goes on
def testBenchmarkFailureIsAWarning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pytestconfig: pytest.Config,
    workdir: Path,
) -> None:
    fakeYahoo(monkeypatch, failing=("^NSEI",))
    arguments = [
        "run",
        "--ticker",
        "TCS.NS",
        "--strategy",
        "buy-and-hold",
        "--preset",
        "india",
        "--output",
        str(workdir / "report.html"),
    ]
    assert runIn(monkeypatch, pytestconfig.rootpath, arguments) == 0
    out = capsys.readouterr().out
    assert "The benchmark could not be loaded." in out


# every user mistake returns 1 with a helpful message
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["run", "--strategy", "buy-and-hold"], "give exactly one of --ticker and --csv"),
        (["run", "--csv", SAMPLE, "--ticker", "X", "--strategy", "buy-and-hold"], "exactly one of"),
        (["run", "--csv", SAMPLE], "--strategy is needed. Valid strategies: buy-and-hold"),
        (["run", "--csv", SAMPLE, "--strategy", "magic"], "Unknown strategy 'magic'. Valid"),
        (["run", "--csv", SAMPLE, "--strategy", "ma-crossover", "--param", "shortWindow=x"], "int"),
        (
            ["run", "--csv", SAMPLE, "--strategy", "buy-and-hold", "--save-data", "a.csv"],
            "only works with --ticker",
        ),
        (
            ["run", "--ticker", "X", "--strategy", "buy-and-hold", "--date-format", "%d"],
            "only works with --csv",
        ),
        (
            ["run", "--csv", SAMPLE, "--strategy", "buy-and-hold", "--preset", "usa"],
            "unknown preset 'usa'",
        ),
        (
            ["run", "--csv", SAMPLE, "--strategy", "buy-and-hold", "--cash", "lots"],
            "--cash should be an amount",
        ),
        (
            ["run", "--csv", SAMPLE, "--strategy", "buy-and-hold", "--seed", "1.5"],
            "--seed should be a whole number",
        ),
        (
            ["run", "--csv", SAMPLE, "--strategy", "buy-and-hold", "--cash", "0"],
            "Starting cash must be above 0",
        ),
        (
            ["run", "--csv", SAMPLE, "--strategy", "buy-and-hold", "--wrong"],
            "unknown option '--wrong'",
        ),
        (["run", "--csv", "missing.csv", "--strategy", "buy-and-hold"], "was not found"),
        (
            ["run", "--ticker", "X", "--strategy", "buy-and-hold", "--end", "soon"],
            "end date 'soon'",
        ),
    ],
)
def testUserMistakes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pytestconfig: pytest.Config,
    arguments: list[str],
    message: str,
) -> None:
    assert runIn(monkeypatch, pytestconfig.rootpath, arguments) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("Error: ")
    assert message in captured.err
    assert "Traceback" not in captured.err
