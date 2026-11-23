from datetime import datetime

from backtestlab.engine import COSTS, UNAFFORDABLE, EngineResult
from backtestlab.formatting import formatDate, formatMoney, formatPercent
from backtestlab.montecarlo import MINRETURNS
from backtestlab.runwarning import RunWarning
from backtestlab.settings import Settings
from backtestlab.trades import RoundTrip

SHORTYEARS = 3.0
FEWTRADES = 20
CASHDRAG = 0.05
DAYSPERYEAR = 365.25


# a warning when the test covers less than three years
def periodWarnings(days: list[datetime]) -> list[RunWarning]:
    years = (days[-1] - days[0]).days / DAYSPERYEAR
    if years >= SHORTYEARS:
        return []
    text = (
        f"The test covers only {years:.1f} years. Results from short periods often don't hold up."
    )
    return [RunWarning("short-period", text)]


# warnings about a strategy that never invested or that made very few trades
def tradeWarnings(result: EngineResult, trips: list[RoundTrip]) -> list[RunWarning]:
    if not result.fills:
        return [
            RunWarning("no-trades", "The strategy never invested, so there is nothing to judge.")
        ]
    completed = sum(1 for trip in trips if not trip.isOpen)
    if 1 <= completed < FEWTRADES:
        noun = "trade" if completed == 1 else "trades"
        text = (
            f"Only {completed} completed {noun}. A win rate based on so few trades is unreliable."
        )
        return [RunWarning("few-trades", text)]
    return []


# a warning when one whole share is a large part of the starting cash
def cashDragWarnings(settings: Settings, firstPrice: float) -> list[RunWarning]:
    share = firstPrice / settings.startingCash
    if not settings.wholeShares or share <= CASHDRAG:
        return []
    cost = formatMoney(firstPrice, settings.currencySymbol, settings.grouping)
    text = (
        f"One share costs {cost}, which is {formatPercent(share, 0)} of your starting cash, "
        "so a lot of money sits idle. Use more cash or --fractional-shares."
    )
    return [RunWarning("cash-drag", text)]


# warnings about orders that were not placed
def orderWarnings(result: EngineResult) -> list[RunWarning]:
    warnings = []
    unaffordable = [order for order in result.skipped if order.reason == UNAFFORDABLE]
    if unaffordable:
        text = (
            f"The strategy wanted to buy on {formatDate(unaffordable[0].day)} "
            "but could not afford a single share."
        )
        if len(unaffordable) > 1:
            text += f" This happened {len(unaffordable)} times."
        warnings.append(RunWarning("unaffordable", text))
    tooSmall = [order for order in result.skipped if order.reason == COSTS]
    if tooSmall:
        text = (
            f"{len(tooSmall)} orders were skipped because their charges were bigger than their "
            f"value. The first was on {formatDate(tooSmall[0].day)}."
        )
        warnings.append(RunWarning("skipped-orders", text))
    return warnings


# a warning when there are too few daily returns for the Monte Carlo check
def monteCarloWarnings(returnCount: int) -> list[RunWarning]:
    if returnCount >= MINRETURNS:
        return []
    noun = "return" if returnCount == 1 else "returns"
    text = (
        f"The Monte Carlo check was skipped because the test has only {returnCount} daily "
        f"{noun} and at least {MINRETURNS} are needed."
    )
    return [RunWarning("monte-carlo-skipped", text)]


# every warning for a run, in the order of the table in the notes
def buildWarnings(
    days: list[datetime],
    settings: Settings,
    result: EngineResult,
    trips: list[RoundTrip],
    firstPrice: float,
    windowWarnings: tuple[RunWarning, ...],
    benchmarkWarning: RunWarning | None,
    dataNotes: tuple[str, ...],
) -> list[RunWarning]:
    found = periodWarnings(days) + tradeWarnings(result, trips) + list(windowWarnings)
    found += cashDragWarnings(settings, firstPrice) + orderWarnings(result)
    found += [benchmarkWarning] if benchmarkWarning else []
    found += monteCarloWarnings(len(days) - 1)
    return found + [RunWarning("data-note", note) for note in dataNotes]
