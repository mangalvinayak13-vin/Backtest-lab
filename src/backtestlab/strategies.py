from dataclasses import dataclass, fields
from typing import Any, ClassVar

import pandas as pd

from backtestlab.errors import SettingsError
from backtestlab.strategy import Strategy


# always fully invested
@dataclass(frozen=True)
class BuyAndHold(Strategy):
    description: ClassVar[str] = "Buys on the first day and holds until the end."

    # always say fully invested
    def decide(self, history: pd.DataFrame) -> float:
        return 1.0


# invested while the short average of closes is above the long average
@dataclass(frozen=True)
class MovingAverageCrossover(Strategy):
    description: ClassVar[str] = (
        "Invested while the short moving average of the close is above the long one."
    )
    shortWindow: int = 50
    longWindow: int = 200

    # the long average needs this many bars
    @property
    def warmupBars(self) -> int:
        return self.longWindow

    # the short window must be at least 1 and shorter than the long one
    def check(self) -> None:
        if not 1 <= self.shortWindow < self.longWindow:
            raise SettingsError(
                f"ma-crossover needs 1 <= shortWindow < longWindow, but shortWindow is "
                f"{self.shortWindow} and longWindow is {self.longWindow}."
            )

    # fully invested when the short average is above the long average, otherwise in cash
    def decide(self, history: pd.DataFrame) -> float:
        closes = history["close"]
        shortAverage = float(closes.tail(self.shortWindow).mean())
        longAverage = float(closes.tail(self.longWindow).mean())
        return 1.0 if shortAverage > longAverage else 0.0


REGISTRY: dict[str, Any] = {
    "buy-and-hold": BuyAndHold,
    "ma-crossover": MovingAverageCrossover,
}
TRUEWORDS = ("true", "yes", "1")
FALSEWORDS = ("false", "no", "0")
TYPENAMES: dict[Any, str] = {bool: "bool", int: "int", float: "float", str: "str"}


# turn the text of a parameter into the type of the field
def convertValue(name: str, kind: Any, text: str) -> Any:
    word = text.strip()
    try:
        if kind is bool:
            return convertBool(word)
        return kind(word)
    except ValueError:
        typeName = TYPENAMES.get(kind, "value")
        raise SettingsError(
            f"Parameter {name} should be of type {typeName}, but got '{text}'."
        ) from None


# true or false from words such as true, no or 1
def convertBool(word: str) -> bool:
    if word.lower() in TRUEWORDS:
        return True
    if word.lower() in FALSEWORDS:
        return False
    raise ValueError(word)


# split name=value into its two parts
def splitParameter(text: str) -> tuple[str, str]:
    name, separator, value = text.partition("=")
    if not separator or not name.strip():
        raise SettingsError(f"The parameter '{text}' should look like name=value.")
    return name.strip(), value


# the parameters of a strategy class, as name and type
def parameterTypes(strategyClass: Any) -> dict[str, Any]:
    return {field.name: field.type for field in fields(strategyClass)}


# turn name=value texts into converted values for one strategy class
def readParameters(strategyName: str, pairs: list[str]) -> dict[str, Any]:
    types = parameterTypes(REGISTRY[strategyName])
    values: dict[str, Any] = {}
    for pair in pairs:
        name, text = splitParameter(pair)
        if name not in types:
            valid = ", ".join(types) if types else "none, this strategy has no parameters"
            raise SettingsError(
                f"{strategyName} has no parameter '{name}'. Valid parameters: {valid}."
            )
        if name in values:
            raise SettingsError(f"The parameter {name} was given more than once.")
        values[name] = convertValue(name, types[name], text)
    return values


# build a strategy from its registry name and name=value parameters, and check it
def makeStrategy(strategyName: str, pairs: list[str] | None = None) -> Strategy:
    if strategyName not in REGISTRY:
        valid = ", ".join(REGISTRY)
        raise SettingsError(f"Unknown strategy '{strategyName}'. Valid strategies: {valid}.")
    values = readParameters(strategyName, pairs or [])
    strategy: Strategy = REGISTRY[strategyName](**values)
    strategy.check()
    return strategy


# the name, type and default of each parameter of a strategy, for the strategies command
def describeParameters(strategyName: str) -> list[tuple[str, str, str]]:
    return [
        (field.name, TYPENAMES.get(field.type, "value"), str(field.default))
        for field in fields(REGISTRY[strategyName])
    ]
