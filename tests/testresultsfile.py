import json
import math
from datetime import date, datetime
from pathlib import Path

import pytest
from helpers import exampleBars, plainSettings

from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.resultsfile import plain, resultsData, writeResultsFile
from backtestlab.strategies import BuyAndHold


# the file is valid json with every part the notes list
def testResultsFileParts(sampleResult: BacktestResult, workdir: Path) -> None:
    target = workdir / "deep" / "report.json"
    writeResultsFile(sampleResult, target)
    with target.open(encoding="utf-8") as file:
        data = json.loads(file.read())
    assert data["schemaVersion"] == 1
    expected = {
        "schemaVersion",
        "version",
        "createdAt",
        "strategy",
        "settings",
        "data",
        "window",
        "strategyRun",
        "buyAndHoldRun",
        "benchmark",
        "monteCarlo",
        "costSensitivity",
        "equity",
        "warnings",
    }
    assert set(data) == expected


# dates are ISO text, missing values are null, and the curves line up with the dates
def testResultsFileValues(sampleResult: BacktestResult) -> None:
    data = resultsData(sampleResult)
    assert data["window"]["firstDate"] == "2019-10-08"
    assert data["benchmark"] is None
    assert data["equity"]["benchmark"] is None
    assert len(data["equity"]["dates"]) == len(data["equity"]["strategy"])
    assert data["settings"]["costs"]["brokerageCap"] == 20.0
    assert "fan" not in data["monteCarlo"]
    fill = data["strategyRun"]["fills"][0]
    assert fill["totalCosts"] == pytest.approx(sum(fill["costs"].values()))


# no NaN or infinity ever reaches the file
def testNoNotANumber(sampleResult: BacktestResult, workdir: Path) -> None:
    target = workdir / "report.json"
    writeResultsFile(sampleResult, target)
    with target.open(encoding="utf-8") as file:
        text = file.read()
    assert "NaN" not in text
    assert "Infinity" not in text


# values are turned into plain json types, and a value json can't hold is a bug
def testPlainValues() -> None:
    assert plain({"a": (1, date(2024, 1, 2)), "b": datetime(2024, 1, 3, 15, 30)}) == {
        "a": [1, "2024-01-02"],
        "b": "2024-01-03",
    }
    with pytest.raises(ValueError, match="json can't hold"):
        plain([math.nan])


# a short run has no Monte Carlo summary in the file
def testShortRunHasNoMonteCarlo() -> None:
    result = runBacktest(exampleBars(), BuyAndHold(), plainSettings())
    assert resultsData(result)["monteCarlo"] is None
