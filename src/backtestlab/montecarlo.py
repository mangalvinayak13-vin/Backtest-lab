import math
from dataclasses import dataclass

import numpy as np

MINRETURNS = 60


# the 5th, 50th and 95th percentile of a list of numbers
@dataclass(frozen=True)
class Percentiles:
    p5: float
    p50: float
    p95: float


# what the simulations say about one series
@dataclass(frozen=True)
class SimulatedSeries:
    totalReturn: Percentiles
    maxDrawdown: Percentiles
    probabilityOfLoss: float


# the bands of the strategy's simulated equity over time, as growth of 100
@dataclass(frozen=True)
class FanChart:
    days: tuple[int, ...]
    low: tuple[float, ...]
    high: tuple[float, ...]
    innerLow: tuple[float, ...]
    innerHigh: tuple[float, ...]
    median: tuple[float, ...]


# the whole Monte Carlo summary
@dataclass(frozen=True)
class MonteCarloResult:
    simulations: int
    blockLength: int
    seed: int
    strategy: SimulatedSeries
    buyAndHold: SimulatedSeries
    probabilityBeatsHold: float
    fan: FanChart
    strategyReturns: tuple[float, ...]


# for each simulation, the day numbers to use: blocks of days in a row, wrapping round the end
def chooseDays(count: int, simulations: int, blockLength: int, seed: int) -> np.ndarray:
    generator = np.random.Generator(np.random.PCG64(seed))
    blocks = math.ceil(count / blockLength)
    starts = generator.integers(0, count, size=(simulations, blocks))
    steps = np.arange(blockLength)
    days = (starts[:, :, None] + steps[None, None, :]) % count
    return days.reshape(simulations, blocks * blockLength)[:, :count]


# the growth of 1 over time for every simulation, one row each, starting with a column of ones
def growthPaths(returns: np.ndarray, days: np.ndarray) -> np.ndarray:
    paths = np.cumprod(1 + returns[days], axis=1)
    return np.concatenate([np.ones((len(days), 1)), paths], axis=1)


# the biggest fall from a peak in each simulation
def worstFalls(paths: np.ndarray) -> np.ndarray:
    return np.min(paths / np.maximum.accumulate(paths, axis=1) - 1, axis=1)


# the 5th, 50th and 95th percentile of the values
def percentilesOf(values: np.ndarray) -> Percentiles:
    low, middle, high = (float(number) for number in np.percentile(values, [5, 50, 95]))
    return Percentiles(low, middle, high)


# the summary of one series of simulated paths
def summarise(paths: np.ndarray) -> SimulatedSeries:
    totals = paths[:, -1] - 1
    return SimulatedSeries(
        percentilesOf(totals), percentilesOf(worstFalls(paths)), float(np.mean(totals < 0))
    )


# the bands of the paths over time, scaled to start at 100
def makeFan(paths: np.ndarray) -> FanChart:
    scaled = paths * 100
    low, innerLow, middle, innerHigh, high = np.percentile(scaled, [5, 25, 50, 75, 95], axis=0)
    return FanChart(
        days=tuple(range(scaled.shape[1])),
        low=tuple(float(value) for value in low),
        high=tuple(float(value) for value in high),
        innerLow=tuple(float(value) for value in innerLow),
        innerHigh=tuple(float(value) for value in innerHigh),
        median=tuple(float(value) for value in middle),
    )


# reshuffle the daily returns in blocks, the same way for the strategy and for buy and hold
def runMonteCarlo(
    strategyReturns: list[float],
    holdReturns: list[float],
    simulations: int,
    blockLength: int,
    seed: int,
) -> MonteCarloResult | None:
    count = len(strategyReturns)
    if count < MINRETURNS:
        return None
    length = min(blockLength, count)
    days = chooseDays(count, simulations, length, seed)
    mine = growthPaths(np.array(strategyReturns), days)
    theirs = growthPaths(np.array(holdReturns), days)
    return MonteCarloResult(
        simulations=simulations,
        blockLength=length,
        seed=seed,
        strategy=summarise(mine),
        buyAndHold=summarise(theirs),
        probabilityBeatsHold=float(np.mean(mine[:, -1] > theirs[:, -1])),
        fan=makeFan(mine),
        strategyReturns=tuple(float(value) for value in mine[:, -1] - 1),
    )
