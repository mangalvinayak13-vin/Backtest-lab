import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from backtestlab.presets import DEFAULT
from backtestlab.prices import PriceData, Row, buildPrices
from backtestlab.settings import CostModel, Settings
from backtestlab.strategy import Strategy

FIRST = datetime(2024, 1, 1)


# prices from (open, close) pairs, one bar per day, with high and low one away from the body
def makePrices(pairs: list[tuple[float, float]]) -> PriceData:
    rows = []
    for number, (openPrice, closePrice) in enumerate(pairs):
        top = max(openPrice, closePrice) + 1
        bottom = min(openPrice, closePrice) - 1
        day = FIRST + timedelta(days=number)
        rows.append(Row(day, openPrice, top, bottom, closePrice, 1000.0))
    return buildPrices(rows, True, "test", [])


# the four bars of the worked examples
def exampleBars() -> PriceData:
    return makePrices([(100, 100), (102, 104), (106, 103), (101, 99)])


# a strategy that follows a list of targets, one for each bar counted from the start of the data
@dataclass(frozen=True)
class Scripted(Strategy):
    description: ClassVar[str] = "follows a script"
    targets: tuple[float, ...]

    # the target for the bar that today is, or the last target when the script has ended
    def decide(self, history: pd.DataFrame) -> float:
        return self.targets[min(len(history), len(self.targets)) - 1]


# a strategy that wraps another one and writes down what it was asked
@dataclass(frozen=True)
class Recorder(Strategy):
    description: ClassVar[str] = "records what it sees"
    inner: Strategy
    lengths: list[int]
    lastDays: list[datetime]
    answers: list[float]

    # the history this strategy needs is whatever the inner one needs
    @property
    def warmupBars(self) -> int:
        return self.inner.warmupBars

    # remember the length and last date of the history, and the answer given
    def decide(self, history: pd.DataFrame) -> float:
        answer = self.inner.decide(history)
        self.lengths.append(len(history))
        stamp = history.index[-1]
        self.lastDays.append(datetime(stamp.year, stamp.month, stamp.day))
        self.answers.append(answer)
        return answer


# settings with no costs and no slippage, so the arithmetic is easy to follow
def plainSettings(**changes: Any) -> Settings:
    values: dict[str, Any] = {
        "startingCash": 1000.0,
        "costs": CostModel(brokerageRate=0.0),
        "slippageRate": 0.0,
    }
    values.update(changes)
    return replace(DEFAULT, **values)


# random but valid prices made from a seed, starting near 100
def randomPrices(seed: int, bars: int) -> PriceData:
    generator = np.random.Generator(np.random.PCG64(seed))
    pairs: list[tuple[float, float]] = []
    previous = 100.0
    while len(pairs) < bars:
        openPrice = previous * math.exp(0.01 * generator.normal())
        closePrice = openPrice * math.exp(0.02 * generator.normal())
        pairs.append((openPrice, closePrice))
        previous = closePrice
    return makePrices(pairs)
