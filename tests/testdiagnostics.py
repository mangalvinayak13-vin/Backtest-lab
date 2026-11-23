from dataclasses import replace
from datetime import datetime, timedelta

from helpers import FIRST, Scripted, exampleBars, plainSettings

from backtestlab.diagnostics import (
    buildWarnings,
    cashDragWarnings,
    monteCarloWarnings,
    orderWarnings,
    periodWarnings,
    tradeWarnings,
)
from backtestlab.engine import EngineResult, SkippedOrder, runEngine
from backtestlab.presets import DEFAULT, INDIA
from backtestlab.runwarning import RunWarning
from backtestlab.trades import RoundTrip
from backtestlab.window import Window


# a finished or open round trip that started on the first day
def tripWith(isOpen: bool) -> RoundTrip:
    return RoundTrip(FIRST, FIRST, 0, 100.0, 110.0, 10.0, 0.1, isOpen)


# an engine result with no bars and the given skipped orders
def skippedOnly(orders: list[SkippedOrder]) -> EngineResult:
    result = runEngine(exampleBars(), Scripted((0.0,)), plainSettings(), Window(0, 3, ()))
    return replace(result, skipped=tuple(orders))


# a test of less than three years gets a warning with the length
def testShortPeriod() -> None:
    days = [FIRST, FIRST + timedelta(days=511)]
    warnings = periodWarnings(days)
    assert warnings == [
        RunWarning(
            "short-period",
            "The test covers only 1.4 years. Results from short periods often don't hold up.",
        )
    ]
    assert periodWarnings([FIRST, FIRST + timedelta(days=1100)]) == []


# a strategy with no fills never invested
def testNoTrades() -> None:
    result = runEngine(exampleBars(), Scripted((0.0,)), plainSettings(), Window(0, 3, ()))
    warnings = tradeWarnings(result, [])
    assert warnings[0].code == "no-trades"
    assert warnings[0].message == "The strategy never invested, so there is nothing to judge."


# between 1 and 19 completed trades is a warning, open trips don't count
def testFewTrades() -> None:
    result = runEngine(exampleBars(), Scripted((1.0, 0.0)), plainSettings(), Window(0, 3, ()))
    seven = [tripWith(False)] * 7 + [tripWith(True)]
    assert tradeWarnings(result, seven)[0].message == (
        "Only 7 completed trades. A win rate based on so few trades is unreliable."
    )
    assert "Only 1 completed trade." in tradeWarnings(result, [tripWith(False)])[0].message
    assert tradeWarnings(result, [tripWith(False)] * 20) == []
    assert tradeWarnings(result, [tripWith(True)]) == []


# one whole share above 5% of the cash leaves money idle
def testCashDrag() -> None:
    warnings = cashDragWarnings(INDIA, 24150.0)
    assert warnings[0].code == "cash-drag"
    assert warnings[0].message == (
        "One share costs ₹24,150, which is 24% of your starting cash, so a lot of money sits "
        "idle. Use more cash or --fractional-shares."
    )
    assert cashDragWarnings(INDIA, 5000.0) == []
    assert cashDragWarnings(replace(INDIA, wholeShares=False), 24150.0) == []


# an order that could not afford one share names the first date, and counts the rest
def testUnaffordableOrders() -> None:
    first = SkippedOrder(datetime(2021, 3, 3), "buy", 100.0, 0.1, "unaffordable")
    later = SkippedOrder(datetime(2021, 5, 3), "buy", 100.0, 0.1, "unaffordable")
    warnings = orderWarnings(skippedOnly([first]))
    assert warnings[0].message == (
        "The strategy wanted to buy on 3 Mar 2021 but could not afford a single share."
    )
    assert orderWarnings(skippedOnly([first, later]))[0].message.endswith("This happened 2 times.")


# orders whose charges were bigger than their value are counted
def testSkippedOrders() -> None:
    order = SkippedOrder(datetime(2021, 3, 3), "sell", 5.0, 15.34, "costs")
    warnings = orderWarnings(skippedOnly([order, order]))
    assert warnings[0].code == "skipped-orders"
    assert warnings[0].message == (
        "2 orders were skipped because their charges were bigger than their value. "
        "The first was on 3 Mar 2021."
    )


# fewer than 60 daily returns skips the Monte Carlo check
def testMonteCarloSkipped() -> None:
    assert monteCarloWarnings(59)[0].code == "monte-carlo-skipped"
    assert monteCarloWarnings(60) == []


# all the warnings come together in the order of the table, with data notes last
def testBuildWarningsOrder() -> None:
    result = runEngine(exampleBars(), Scripted((0.0,)), plainSettings(), Window(0, 3, ()))
    days = [FIRST + timedelta(days=number) for number in range(4)]
    moved = RunWarning("window-moved", "moved")
    missing = RunWarning("benchmark-missing", "missing")
    warnings = buildWarnings(days, DEFAULT, result, [], 100.0, (moved,), missing, ("a note",))
    codes = [warning.code for warning in warnings]
    assert codes == [
        "short-period",
        "no-trades",
        "window-moved",
        "benchmark-missing",
        "monte-carlo-skipped",
        "data-note",
    ]
    assert warnings[-1].message == "a note"


# a long, busy test with an affordable share has no warnings
def testNoWarningsWhenAllIsWell() -> None:
    result = runEngine(exampleBars(), Scripted((1.0, 0.0)), plainSettings(), Window(0, 3, ()))
    days = [FIRST, FIRST + timedelta(days=4000)]
    trips = [tripWith(False)] * 25
    assert buildWarnings(days, DEFAULT, result, trips, 100.0, (), None, ()) == [
        RunWarning(
            "monte-carlo-skipped",
            "The Monte Carlo check was skipped because the test has only 1 daily return "
            "and at least 60 are needed.",
        )
    ]
