import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.csvsource import loadCsv
from backtestlab.presets import INDIA
from backtestlab.strategies import MovingAverageCrossover


# a fresh empty folder for one test, removed afterwards
@pytest.fixture
def workdir() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as folder:
        yield Path(folder)


# one full backtest of the crossover on the sample data with the india preset, shared by tests
@pytest.fixture(scope="session")
def sampleResult(pytestconfig: pytest.Config) -> BacktestResult:
    prices = loadCsv(pytestconfig.rootpath / "data" / "sampleprices.csv")
    return runBacktest(prices, MovingAverageCrossover(), INDIA)
