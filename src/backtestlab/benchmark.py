from dataclasses import dataclass
from datetime import datetime

from backtestlab.formatting import formatDate
from backtestlab.prices import PriceData
from backtestlab.pricewarnings import indexDays
from backtestlab.runwarning import RunWarning


# a market index lined up with the test dates, or the reason it could not be
@dataclass(frozen=True)
class AlignedBenchmark:
    values: tuple[float, ...]
    warning: RunWarning | None


# for each date, the position of the last benchmark day on or before it, or -1 if there is none
def lastKnownPositions(benchmarkDays: list[datetime], days: list[datetime]) -> list[int]:
    positions = []
    position = -1
    for day in days:
        while position + 1 < len(benchmarkDays) and benchmarkDays[position + 1] <= day:
            position += 1
        positions.append(position)
    return positions


# scale the benchmark to start at the starting cash, carrying the last known price forward
def alignBenchmark(
    benchmark: PriceData, days: list[datetime], startingCash: float, label: str
) -> AlignedBenchmark:
    closes = [float(price) for price in benchmark.frame["close"].values]
    positions = lastKnownPositions(indexDays(benchmark.frame), days)
    if positions[0] < 0:
        text = f"{label} has no price on or before {formatDate(days[0])}, so it is left out."
        return AlignedBenchmark((), RunWarning("benchmark-missing", text))
    start = closes[positions[0]]
    values = tuple(closes[position] / start * startingCash for position in positions)
    return AlignedBenchmark(values, None)
