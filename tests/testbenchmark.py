from datetime import datetime, timedelta

import pytest
from helpers import FIRST

from backtestlab.benchmark import alignBenchmark
from backtestlab.prices import PriceData, Row, buildPrices


# a benchmark with a close on each given day number, where day 0 is 1 Jan 2024
def makeBenchmark(closes: dict[int, float]) -> PriceData:
    rows = [
        Row(FIRST + timedelta(days=number), price, price + 1, price - 1, price, 0.0)
        for number, price in sorted(closes.items())
    ]
    return buildPrices(rows, False, "index", [])


# the dates of the test, day numbers counted from 1 Jan 2024
def windowDays(*numbers: int) -> list[datetime]:
    return [FIRST + timedelta(days=number) for number in numbers]


# the benchmark is scaled to start at the starting cash
def testScaledToStartingCash() -> None:
    benchmark = makeBenchmark({0: 200.0, 1: 210.0, 2: 220.0})
    aligned = alignBenchmark(benchmark, windowDays(0, 1, 2), 1000.0, "Index")
    assert aligned.warning is None
    assert aligned.values == pytest.approx((1000.0, 1050.0, 1100.0), rel=1e-9)


# a date with no benchmark price takes the last known price
def testLastKnownPriceIsCarriedForward() -> None:
    benchmark = makeBenchmark({0: 100.0, 2: 120.0})
    aligned = alignBenchmark(benchmark, windowDays(0, 1, 2, 3), 100.0, "Index")
    assert aligned.values == pytest.approx((100.0, 100.0, 120.0, 120.0), rel=1e-9)


# earlier benchmark days are used when the test starts later
def testStartingOnAGapUsesTheEarlierPrice() -> None:
    benchmark = makeBenchmark({0: 100.0, 1: 110.0, 4: 150.0})
    aligned = alignBenchmark(benchmark, windowDays(2, 3, 4), 1000.0, "Index")
    assert aligned.values == pytest.approx((1000.0, 1000.0, 1000.0 * 150 / 110), rel=1e-9)


# a price after the first date is never used backwards, so the benchmark is left out
def testNoPriceOnOrBeforeTheFirstDate() -> None:
    benchmark = makeBenchmark({2: 100.0, 3: 110.0})
    aligned = alignBenchmark(benchmark, windowDays(0, 1, 2), 1000.0, "NIFTY 50")
    assert aligned.values == ()
    assert aligned.warning is not None
    assert aligned.warning.code == "benchmark-missing"
    assert aligned.warning.message == (
        "NIFTY 50 has no price on or before 1 Jan 2024, so it is left out."
    )
