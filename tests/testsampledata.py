import itertools
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from backtestlab.csvsource import loadCsv


# how many times the 50 and 200 day averages cross in the closing prices
def countCrossovers(closes: list[float]) -> int:
    above = []
    for position in range(199, len(closes)):
        short = np.mean(closes[position - 49 : position + 1])
        long = np.mean(closes[position - 199 : position + 1])
        above.append(bool(short > long))
    return sum(1 for before, after in itertools.pairwise(above) if before != after)


# the sample file loads cleanly with about five years of business days
def testSampleFileIsCleanAndFiveYearsLong(pytestconfig: pytest.Config) -> None:
    data = loadCsv(pytestconfig.rootpath / "data" / "sampleprices.csv")
    assert data.notes == ()
    assert len(data.frame) == 1305
    assert data.frame.index[0] == datetime(2019, 1, 2)
    assert 900 < float(data.frame["close"].iloc[0]) < 1100
    assert "volume" in data.frame.columns
    assert all(day.weekday() < 5 for day in data.frame.index)


# the crossover strategy would trade several times on the sample prices
def testSampleFileHasSeveralCrossovers(pytestconfig: pytest.Config) -> None:
    data = loadCsv(pytestconfig.rootpath / "data" / "sampleprices.csv")
    closes = [float(price) for price in data.frame["close"].values]
    assert countCrossovers(closes) >= 4


# running the script again writes exactly the file that is in the repository
def testScriptRebuildsTheSameFile(pytestconfig: pytest.Config, workdir: Path) -> None:
    script = pytestconfig.rootpath / "scripts" / "makesampledata.py"
    target = workdir / "again.csv"
    subprocess.run([sys.executable, str(script), str(target)], check=True, stdout=subprocess.PIPE)
    with target.open(encoding="utf-8") as file:
        rebuilt = file.read()
    with (pytestconfig.rootpath / "data" / "sampleprices.csv").open(encoding="utf-8") as file:
        assert file.read() == rebuilt
