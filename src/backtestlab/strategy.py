import math
import re
from abc import ABC, abstractmethod
from numbers import Real
from typing import ClassVar

import pandas as pd

from backtestlab.errors import StrategyError

# where a class name splits into words: myRule, and the end of a short form as in RSIRule
WORDBREAK = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


# a trading rule: it looks at the past and says how invested to be tomorrow
class Strategy(ABC):
    description: ClassVar[str]

    # how many bars of history this strategy needs before its first decision
    @property
    def warmupBars(self) -> int:
        return 0

    # complain early if the parameters make no sense
    def check(self) -> None:
        return None

    # look at the history up to today and say how invested to be tomorrow
    @abstractmethod
    def decide(self, history: pd.DataFrame) -> float: ...


# whether a word is a short form such as RSI, which keeps its capitals
def isShortForm(word: str) -> bool:
    return len(word) > 1 and word.isupper()


# the words of a class name as they are written inside a sentence
def sentenceWords(name: str) -> str:
    words = WORDBREAK.split(name)
    return " ".join(word if isShortForm(word) else word.lower() for word in words)


# a readable name for a strategy, such as "Moving average crossover (shortWindow=50, ...)"
def strategyLabel(strategy: Strategy) -> str:
    text = repr(strategy)
    name, bracket, rest = text.partition("(")
    if not bracket or text.startswith("<"):
        return "Custom strategy"
    sentence = sentenceWords(name)
    words = sentence[:1].upper() + sentence[1:]
    settings = rest[:-1]
    return f"{words} ({settings})" if settings else words


# make sure a decision is a real number from 0 to 1, and give it back as a float
def checkTarget(strategyName: str, dayText: str, value: object) -> float:
    if not isinstance(value, Real):
        raise StrategyError(
            f"{strategyName} returned {value!r} on {dayText}, which is not a number."
        )
    target = float(value)
    if not math.isfinite(target) or not 0.0 <= target <= 1.0:
        raise StrategyError(
            f"{strategyName} returned {target} on {dayText}. "
            "A decision must be a number from 0 to 1."
        )
    return target
