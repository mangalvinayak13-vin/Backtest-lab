import math

import numpy as np
import pandas as pd
import pytest

from backtestlab.errors import SettingsError, StrategyError
from backtestlab.strategies import (
    REGISTRY,
    BuyAndHold,
    MovingAverageCrossover,
    convertValue,
    makeStrategy,
)
from backtestlab.strategy import Strategy, checkTarget, strategyLabel


# a history table with only a close column
def makeHistory(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": closes, "open": closes})


# buy and hold is always fully invested and needs no history
def testBuyAndHoldIsAlwaysInvested() -> None:
    strategy = BuyAndHold()
    assert strategy.decide(makeHistory([1.0])) == 1.0
    assert strategy.warmupBars == 0
    strategy.check()
    assert BuyAndHold.description


# a short average above the long average means invested (averages 4.5 and 3)
def testCrossoverInvestedWhenShortIsAbove() -> None:
    strategy = MovingAverageCrossover(shortWindow=2, longWindow=5)
    assert strategy.decide(makeHistory([1, 2, 3, 4, 5])) == 1.0


# a short average below the long average means cash (averages 1.5 and 3)
def testCrossoverInCashWhenShortIsBelow() -> None:
    strategy = MovingAverageCrossover(shortWindow=2, longWindow=5)
    assert strategy.decide(makeHistory([5, 4, 3, 2, 1])) == 0.0


# equal averages are not above, so the strategy stays in cash
def testCrossoverInCashWhenAveragesAreEqual() -> None:
    strategy = MovingAverageCrossover(shortWindow=2, longWindow=5)
    assert strategy.decide(makeHistory([3, 3, 3, 3, 3])) == 0.0


# only the last longWindow closes matter, older bars do not
def testCrossoverIgnoresOlderBars() -> None:
    strategy = MovingAverageCrossover(shortWindow=2, longWindow=5)
    assert strategy.decide(makeHistory([1000, 1000, 1, 2, 3, 4, 5])) == 1.0


# the default windows are 50 and 200, and the warm-up is the long window
def testCrossoverDefaults() -> None:
    strategy = MovingAverageCrossover()
    assert (strategy.shortWindow, strategy.longWindow) == (50, 200)
    assert strategy.warmupBars == 200
    assert strategy.description


# bad windows are a settings error that shows both values
@pytest.mark.parametrize(("short", "long"), [(0, 5), (-1, 5), (5, 5), (6, 5)])
def testCrossoverCheckRejectsBadWindows(short: int, long: int) -> None:
    with pytest.raises(SettingsError, match=rf"shortWindow is {short} and longWindow is {long}"):
        MovingAverageCrossover(shortWindow=short, longWindow=long).check()


# good windows pass, including a short window of 1
def testCrossoverCheckAcceptsGoodWindows() -> None:
    MovingAverageCrossover(shortWindow=1, longWindow=2).check()


# both built-in strategies are in the registry under their command line names
def testRegistryNames() -> None:
    assert list(REGISTRY) == ["buy-and-hold", "ma-crossover"]
    assert issubclass(REGISTRY["ma-crossover"], Strategy)


# a strategy is made from its name with the default parameters
def testMakeStrategyWithDefaults() -> None:
    assert makeStrategy("buy-and-hold") == BuyAndHold()
    assert makeStrategy("ma-crossover") == MovingAverageCrossover()


# parameters from the command line change the fields
def testMakeStrategyWithParameters() -> None:
    strategy = makeStrategy("ma-crossover", ["shortWindow=20", " longWindow = 100"])
    assert strategy == MovingAverageCrossover(shortWindow=20, longWindow=100)


# an unknown strategy lists the valid ones
def testUnknownStrategy() -> None:
    with pytest.raises(
        SettingsError, match=r"Unknown strategy 'foo'. Valid strategies: buy-and-hold, ma-crossover"
    ):
        makeStrategy("foo")


# an unknown parameter lists the valid ones
def testUnknownParameter() -> None:
    with pytest.raises(
        SettingsError, match=r"no parameter 'speed'. Valid parameters: shortWindow, longWindow"
    ):
        makeStrategy("ma-crossover", ["speed=3"])


# a strategy without parameters says so
def testStrategyWithNoParameters() -> None:
    with pytest.raises(SettingsError, match="this strategy has no parameters"):
        makeStrategy("buy-and-hold", ["x=1"])


# a value of the wrong type is a settings error
def testBadParameterValue() -> None:
    with pytest.raises(
        SettingsError, match=r"Parameter shortWindow should be of type int, but got '2\.5'"
    ):
        makeStrategy("ma-crossover", ["shortWindow=2.5"])


# a parameter without an equals sign is a settings error
def testParameterWithoutEquals() -> None:
    with pytest.raises(SettingsError, match="should look like name=value"):
        makeStrategy("ma-crossover", ["shortWindow"])
    with pytest.raises(SettingsError, match="should look like name=value"):
        makeStrategy("ma-crossover", ["=5"])


# the same parameter twice is a settings error
def testRepeatedParameter() -> None:
    with pytest.raises(SettingsError, match="shortWindow was given more than once"):
        makeStrategy("ma-crossover", ["shortWindow=2", "shortWindow=3"])


# an invalid combination is caught while the strategy is made
def testInvalidCombinationFromParameters() -> None:
    with pytest.raises(SettingsError, match="shortWindow is 300 and longWindow is 200"):
        makeStrategy("ma-crossover", ["shortWindow=300"])


# text is converted using the type of the field
def testConvertValue() -> None:
    assert convertValue("x", int, " 20 ") == 20
    assert convertValue("x", float, "2.5") == 2.5
    assert convertValue("x", float, "2") == 2.0
    assert convertValue("x", str, "hello") == "hello"
    assert convertValue("x", bool, "True") is True
    assert convertValue("x", bool, "no") is False
    with pytest.raises(SettingsError, match="of type bool"):
        convertValue("x", bool, "maybe")


# a decision that is a real number from 0 to 1 is accepted, including booleans and numpy numbers
@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0.0), (1, 1.0), (0.5, 0.5), (True, 1.0), (False, 0.0), (np.float64(0.25), 0.25)],
)
def testCheckTargetAcceptsGoodValues(value: object, expected: float) -> None:
    assert checkTarget("MyRule", "2024-01-02", value) == expected


# numpy integers are accepted too
def testCheckTargetAcceptsNumpyIntegers() -> None:
    assert checkTarget("MyRule", "2024-01-02", np.int64(1)) == 1.0


# anything else is a strategy error naming the strategy, the date and the value
@pytest.mark.parametrize("value", [1.5, -0.1, math.nan, math.inf, "1", None])
def testCheckTargetRejectsBadValues(value: object) -> None:
    with pytest.raises(StrategyError, match=r"MyRule returned .* on 2024-01-02"):
        checkTarget("MyRule", "2024-01-02", value)


# a strategy that is not a dataclass still gets a readable label
class Plain(Strategy):
    description = "a plain class"

    # always in cash
    def decide(self, history: pd.DataFrame) -> float:
        return 0.0


# built-in strategies get their name in words with their parameters
def testStrategyLabels() -> None:
    assert strategyLabel(BuyAndHold()) == "Buy and hold"
    crossover = strategyLabel(MovingAverageCrossover())
    assert crossover == "Moving average crossover (shortWindow=50, longWindow=200)"
    assert strategyLabel(Plain()) == "Custom strategy"
