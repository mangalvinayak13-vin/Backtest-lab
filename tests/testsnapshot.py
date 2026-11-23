import json
from pathlib import Path
from typing import Any

import pytest

from backtestlab.cli import main

ARGUMENTS = [
    "run",
    "--csv",
    "data/sampleprices.csv",
    "--strategy",
    "ma-crossover",
    "--benchmark",
    "none",
]
CHANGING = ("createdAt", "version")


# the differences between two json objects, leaving out the values that change on every run
def dictDifferences(expected: dict[str, Any], actual: dict[str, Any], where: str) -> list[str]:
    if set(expected) != set(actual):
        return [f"{where}: keys differ"]
    found = []
    for key in expected:
        if key not in CHANGING:
            found += differences(expected[key], actual[key], f"{where}.{key}")
    return found


# the differences between two json lists, item by item
def listDifferences(expected: list[Any], actual: list[Any], where: str) -> list[str]:
    if len(expected) != len(actual):
        return [f"{where}: lengths differ"]
    found = []
    for position, pair in enumerate(zip(expected, actual, strict=True)):
        found += differences(pair[0], pair[1], f"{where}[{position}]")
    return found


# the differences between two json values, with numbers compared to a relative 1e-9
def differences(expected: Any, actual: Any, where: str) -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        return dictDifferences(expected, actual, where)
    if isinstance(expected, list) and isinstance(actual, list):
        return listDifferences(expected, actual, where)
    if isinstance(expected, float) and isinstance(actual, float):
        same = actual == pytest.approx(expected, rel=1e-9, abs=1e-12)
        return [] if same else [f"{where}: {expected} != {actual}"]
    return [] if expected == actual else [f"{where}: {expected!r} != {actual!r}"]


# the end-to-end run on the sample data gives the numbers in the snapshot
def testRunMatchesSnapshot(
    monkeypatch: pytest.MonkeyPatch, pytestconfig: pytest.Config, workdir: Path
) -> None:
    monkeypatch.chdir(pytestconfig.rootpath)
    assert main([*ARGUMENTS, "--output", str(workdir / "report.html")]) == 0
    with (workdir / "report.json").open(encoding="utf-8") as file:
        actual = json.loads(file.read())
    with (pytestconfig.rootpath / "tests" / "snapshots" / "macrossover.json").open(
        encoding="utf-8"
    ) as file:
        expected = json.loads(file.read())
    assert differences(expected, actual, "results") == []


# the comparison itself notices changed numbers, keys and lengths
def testDifferencesFindsChanges() -> None:
    assert differences({"a": 1.0}, {"a": 1.0 + 1e-12}, "x") == []
    assert differences({"a": 1.0}, {"a": 1.1}, "x") == ["x.a: 1.0 != 1.1"]
    assert differences({"a": 1}, {"b": 1}, "x") == ["x: keys differ"]
    assert differences([1, 2], [1], "x") == ["x: lengths differ"]
    assert differences(["a"], ["b"], "x") == ["x[0]: 'a' != 'b'"]
    assert differences({"createdAt": "now"}, {"createdAt": "later"}, "x") == []
