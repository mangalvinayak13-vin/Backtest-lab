import numpy as np
import pytest

from backtestlab.montecarlo import chooseDays, runMonteCarlo


# daily returns made from a seed, a little above zero on average
def someReturns(seed: int, count: int) -> list[float]:
    generator = np.random.Generator(np.random.PCG64(seed))
    return [float(value) for value in 0.0005 + 0.01 * generator.normal(size=count)]


# the same seed gives exactly the same results
def testSameSeedSameResult() -> None:
    mine, theirs = someReturns(1, 300), someReturns(2, 300)
    first = runMonteCarlo(mine, theirs, 200, 20, 42)
    second = runMonteCarlo(mine, theirs, 200, 20, 42)
    assert first == second


# a different seed gives different results
def testDifferentSeedDiffers() -> None:
    mine, theirs = someReturns(1, 300), someReturns(2, 300)
    first = runMonteCarlo(mine, theirs, 200, 20, 42)
    second = runMonteCarlo(mine, theirs, 200, 20, 43)
    assert first is not None
    assert second is not None
    assert first.strategyReturns != second.strategyReturns


# returns that are all positive never lose money
def testAllPositiveReturnsNeverLose() -> None:
    result = runMonteCarlo([0.001] * 100, [0.002] * 100, 100, 20, 1)
    assert result is not None
    assert result.strategy.probabilityOfLoss == 0.0
    assert result.strategy.maxDrawdown.p5 == 0.0
    assert result.strategy.totalReturn.p50 == pytest.approx(1.001**100 - 1, rel=1e-9)


# when the strategy and buy and hold earn the same, the strategy never beats holding
def testIdenticalReturnsNeverBeatHolding() -> None:
    same = someReturns(5, 120)
    result = runMonteCarlo(same, same, 300, 20, 3)
    assert result is not None
    assert result.probabilityBeatsHold == 0.0
    assert result.strategy == result.buyAndHold


# fewer than 60 returns means the check is skipped
def testTooFewReturnsIsSkipped() -> None:
    assert runMonteCarlo([0.01] * 59, [0.01] * 59, 100, 20, 1) is None
    assert runMonteCarlo([0.01] * 60, [0.01] * 60, 100, 20, 1) is not None


# a block longer than the test is cut down to the length of the test
def testBlockLongerThanTheTest() -> None:
    result = runMonteCarlo(someReturns(1, 70), someReturns(2, 70), 100, 500, 9)
    assert result is not None
    assert result.blockLength == 70


# the days are blocks of days in a row, wrapping round past the end
def testDaysAreWrappedBlocks() -> None:
    days = chooseDays(10, 50, 4, 7)
    assert days.shape == (50, 10)
    for row in days:
        for start in range(0, 10, 4):
            block = list(row[start : start + 4])
            assert all((block[step] - block[0]) % 10 == step for step in range(len(block)))


# the strategy and buy and hold use the same days: a strategy that earns 0.1% more than holding
# on every single day beats holding in every simulation, which unpaired draws would not give
def testSimulationsArePaired() -> None:
    hold = someReturns(4, 100)
    better = [value + 0.001 for value in hold]
    result = runMonteCarlo(better, hold, 500, 10, 2)
    assert result is not None
    assert result.probabilityBeatsHold == 1.0


# the fan chart starts at 100 and its bands are in order
def testFanChart() -> None:
    result = runMonteCarlo(someReturns(1, 100), someReturns(2, 100), 200, 20, 42)
    assert result is not None
    fan = result.fan
    assert fan.days[0] == 0
    assert len(fan.days) == 101
    assert fan.median[0] == 100.0
    for position in range(len(fan.days)):
        assert fan.low[position] <= fan.innerLow[position] <= fan.median[position]
        assert fan.median[position] <= fan.innerHigh[position] <= fan.high[position]
    assert len(result.strategyReturns) == 200
    assert (result.simulations, result.seed) == (200, 42)


# the percentiles are in order
def testPercentilesAreInOrder() -> None:
    result = runMonteCarlo(someReturns(1, 250), someReturns(2, 250), 500, 20, 8)
    assert result is not None
    spread = result.strategy.totalReturn
    assert spread.p5 <= spread.p50 <= spread.p95
    assert 0.0 <= result.buyAndHold.probabilityOfLoss <= 1.0
