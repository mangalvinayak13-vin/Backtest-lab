import math
from dataclasses import dataclass, replace
from datetime import datetime
from typing import ClassVar

import pandas as pd
import pytest
from helpers import Recorder, Scripted, exampleBars, makePrices, plainSettings, randomPrices

from backtestlab.csvsource import loadCsv
from backtestlab.engine import EngineResult, runEngine
from backtestlab.errors import StrategyError
from backtestlab.presets import DEFAULT
from backtestlab.prices import PriceData
from backtestlab.settings import CostModel, Settings
from backtestlab.strategies import BuyAndHold, MovingAverageCrossover
from backtestlab.strategy import Strategy
from backtestlab.trades import buildRoundTrips
from backtestlab.window import Window, chooseWindow

EXAMPLE2 = replace(
    DEFAULT,
    startingCash=1000.0,
    costs=CostModel(brokerageRate=0.001),
    slippageRate=0.0005,
    wholeShares=True,
)


# run a strategy over the whole table
def runAll(prices: PriceData, strategy: Strategy, settings: Settings) -> EngineResult:
    return runEngine(prices, strategy, settings, Window(0, len(prices.frame) - 1, ()))


# the equity column as a list of floats
def equities(result: EngineResult) -> list[float]:
    return [float(value) for value in result.bars["equity"].values]


# worked example 1: buy and hold with whole shares
def testWorkedExampleOne() -> None:
    result = runAll(exampleBars(), BuyAndHold(), plainSettings())
    assert equities(result) == pytest.approx([1000.0, 1018.0, 1009.0, 973.0], rel=1e-9)
    assert list(result.bars["cash"]) == pytest.approx([1000.0, 82.0, 82.0, 82.0], rel=1e-9)
    assert list(result.bars["shares"]) == [0.0, 9.0, 9.0, 9.0]
    assert len(result.fills) == 1
    fill = result.fills[0]
    assert fill.day == datetime(2024, 1, 2)
    assert (fill.side, fill.shares, fill.fillPrice, fill.orderValue) == ("buy", 9.0, 102.0, 918.0)
    assert fill.cashAfter == pytest.approx(82.0, rel=1e-9)
    assert equities(result)[-1] / 1000.0 - 1 == pytest.approx(-0.027, rel=1e-9)


# worked example 1 with fractional shares
def testWorkedExampleOneFractional() -> None:
    result = runAll(exampleBars(), BuyAndHold(), plainSettings(wholeShares=False))
    assert result.fills[0].shares == pytest.approx(9.80392157, rel=1e-8)
    assert equities(result)[-1] == pytest.approx(970.588235, rel=1e-9)
    assert equities(result)[-1] == pytest.approx(1000.0 * 99 / 102, rel=1e-9)


# worked example 2: costs and slippage, buy on the first signal and sell on the second
def testWorkedExampleTwo() -> None:
    result = runAll(exampleBars(), Scripted((1.0, 0.0, 0.0, 0.0)), EXAMPLE2)
    buy, sell = result.fills
    assert buy.day == datetime(2024, 1, 2)
    assert buy.fillPrice == pytest.approx(102.051, rel=1e-9)
    assert buy.shares == 9.0
    assert buy.orderValue == pytest.approx(918.459, rel=1e-9)
    assert buy.costs.brokerage == pytest.approx(0.918459, rel=1e-9)
    assert buy.cashAfter == pytest.approx(80.622541, rel=1e-9)
    assert sell.day == datetime(2024, 1, 3)
    assert sell.fillPrice == pytest.approx(105.947, rel=1e-9)
    assert sell.orderValue == pytest.approx(953.523, rel=1e-9)
    assert sell.costs.brokerage == pytest.approx(0.953523, rel=1e-9)
    assert sell.cashAfter == pytest.approx(1033.192018, rel=1e-9)
    expected = [1000.0, 1016.622541, 1033.192018, 1033.192018]
    assert equities(result) == pytest.approx(expected, rel=1e-9)


# worked example 2: one completed round trip with profit 33.192018
def testWorkedExampleTwoRoundTrip() -> None:
    result = runAll(exampleBars(), Scripted((1.0, 0.0, 0.0, 0.0)), EXAMPLE2)
    trips = buildRoundTrips(result.fills, datetime(2024, 1, 4), 99.0)
    assert len(trips) == 1
    assert trips[0].paid == pytest.approx(919.377459, rel=1e-9)
    assert trips[0].profit == pytest.approx(33.192018, rel=1e-9)
    assert trips[0].returnRate == pytest.approx(33.192018 / 919.377459, rel=1e-9)
    assert trips[0].returnRate == pytest.approx(0.036103, abs=1e-6)


# the table has a date index and the four columns
def testBarsTableShape() -> None:
    result = runAll(exampleBars(), BuyAndHold(), plainSettings())
    assert result.bars.index.name == "date"
    assert list(result.bars.columns) == ["cash", "shares", "equity", "target"]
    assert list(result.bars["target"]) == [0.0, 1.0, 1.0, 1.0]


# a decision at a close is carried out at the next open, never on the same bar
def testSignalIsExecutedAtNextOpen() -> None:
    result = runAll(exampleBars(), Scripted((0.0, 1.0, 1.0, 1.0)), plainSettings())
    assert len(result.fills) == 1
    assert result.fills[0].day == datetime(2024, 1, 3)
    assert result.fills[0].openPrice == 106.0


# the decision at the close of the last bar is never executed
def testLastDecisionIsNotExecuted() -> None:
    result = runAll(exampleBars(), Scripted((0.0, 0.0, 0.0, 1.0)), plainSettings())
    assert result.fills == ()
    assert equities(result) == [1000.0] * 4


# the engine starts in cash and does nothing when the target stays at zero
def testStartsInCash() -> None:
    result = runAll(exampleBars(), Scripted((0.0,)), plainSettings())
    assert result.fills == ()
    assert result.skipped == ()


# the engine trades only when the target changes
def testNoRebalancingWhenTargetIsUnchanged() -> None:
    result = runAll(exampleBars(), Scripted((1.0,)), plainSettings())
    assert len(result.fills) == 1


# a target of one half buys half the portfolio
def testPartialTargetBuysHalf() -> None:
    flat = makePrices([(100.0, 100.0)] * 3)
    result = runAll(flat, Scripted((0.5,)), plainSettings())
    assert result.fills[0].shares == 5.0
    assert result.bars["cash"].iloc[-1] == pytest.approx(500.0, rel=1e-9)


# lowering the target sells the difference
def testLoweringTheTargetSellsPart() -> None:
    flat = makePrices([(100.0, 100.0)] * 4)
    result = runAll(flat, Scripted((1.0, 0.5, 0.5, 0.5)), plainSettings())
    assert [fill.side for fill in result.fills] == ["buy", "sell"]
    assert result.fills[1].shares == 5.0
    assert result.bars["shares"].iloc[-1] == 5.0
    assert result.bars["cash"].iloc[-1] == pytest.approx(500.0, rel=1e-9)


# a target of zero sells every share exactly
def testTargetZeroSellsEverything() -> None:
    result = runAll(exampleBars(), Scripted((1.0, 0.0, 0.0, 0.0)), plainSettings(wholeShares=False))
    assert result.bars["shares"].iloc[-1] == 0.0


# a buy is cut down to what the cash can pay for with the charges included
def testBuyIsLimitedByAffordability() -> None:
    flat = makePrices([(100.0, 100.0)] * 2)
    settings = plainSettings(costs=CostModel(brokerageRate=0.01))
    result = runAll(flat, Scripted((1.0,)), settings)
    assert result.fills[0].shares == 9.0
    assert result.fills[0].cashAfter == pytest.approx(1000.0 - 900.0 - 9.0, rel=1e-9)


# when not even one share can be paid for, nothing is bought and the order is recorded
def testUnaffordableOrder() -> None:
    flat = makePrices([(100.0, 100.0)] * 3)
    result = runAll(flat, Scripted((1.0,)), plainSettings(startingCash=50.0))
    assert result.fills == ()
    assert len(result.skipped) == 1
    skipped = result.skipped[0]
    assert (skipped.side, skipped.reason, skipped.day) == (
        "buy",
        "unaffordable",
        datetime(2024, 1, 2),
    )
    assert result.bars["shares"].iloc[-1] == 0.0
    assert result.bars["cash"].iloc[-1] == 50.0


# a changed target that rounds to the same number of whole shares makes no trade
def testTargetChangeThatRoundsToTheSameShares() -> None:
    flat = makePrices([(100.0, 100.0)] * 4)
    result = runAll(flat, Scripted((1.0, 0.97, 0.97, 0.97)), plainSettings(startingCash=1050.0))
    assert len(result.fills) == 1
    assert result.skipped == ()
    assert result.bars["shares"].iloc[-1] == 10.0


# a buy that is cut to nothing by the charges is recorded as unaffordable
def testUnaffordableBecauseOfCharges() -> None:
    flat = makePrices([(100.0, 100.0)] * 3)
    settings = plainSettings(startingCash=105.0, costs=CostModel(brokerageRate=0.1))
    result = runAll(flat, Scripted((1.0,)), settings)
    assert result.fills == ()
    assert result.skipped[0].reason == "unaffordable"
    assert result.skipped[0].orderValue == 100.0


# an order that costs more than it is worth is skipped, and the engine does not retry it
def testSellSkippedWhenChargesAreBiggerThanTheOrder() -> None:
    flat = makePrices([(100.0, 100.0)] * 4)
    settings = plainSettings(costs=CostModel(brokerageRate=0.0, sellFeePerOrder=2000.0))
    result = runAll(flat, Scripted((1.0, 0.0, 0.0, 0.0)), settings)
    assert len(result.fills) == 1
    assert len(result.skipped) == 1
    assert (result.skipped[0].side, result.skipped[0].reason) == ("sell", "costs")
    assert result.skipped[0].totalCosts == 2000.0
    assert result.bars["shares"].iloc[-1] == 10.0


# a buy whose charges are bigger than its value is skipped too
def testBuySkippedWhenChargesAreBiggerThanTheOrder() -> None:
    flat = makePrices([(10.0, 10.0)] * 3)
    settings = plainSettings(costs=CostModel(brokerageRate=0.5, buyTaxRate=0.6))
    result = runAll(flat, Scripted((1.0,)), settings)
    assert result.fills == ()
    assert result.skipped[0].reason == "costs"
    assert result.bars["cash"].iloc[-1] == 1000.0


# a decision that is not allowed stops the run with the strategy and the date
def testBadDecisionIsAStrategyError() -> None:
    with pytest.raises(StrategyError, match=r"Scripted.* on 2024-01-02"):
        runAll(exampleBars(), Scripted((0.0, 1.5)), plainSettings())


# each call sees exactly one more bar than the one before, and its last date is that bar
def testEachDecisionSeesOneMoreBar() -> None:
    prices = randomPrices(7, 10)
    recorder = Recorder(MovingAverageCrossover(2, 3), [], [], [])
    window = chooseWindow(prices, recorder.warmupBars)
    runEngine(prices, recorder, plainSettings(), window)
    assert recorder.lengths == [3, 4, 5, 6, 7, 8, 9, 10]
    days = [datetime(2024, 1, n) for n in range(3, 11)]
    assert recorder.lastDays == days


# changing every price after a date changes nothing up to and including that date
def testFuturePricesCannotChangeThePast() -> None:
    original = randomPrices(11, 60)
    changedFrame = original.frame.copy()
    changedFrame.iloc[41:] = changedFrame.iloc[41:] * 3
    changed = PriceData(changedFrame, "changed", ())
    settings = replace(DEFAULT, startingCash=100000.0)
    first = Recorder(MovingAverageCrossover(5, 15), [], [], [])
    second = Recorder(MovingAverageCrossover(5, 15), [], [], [])
    window = chooseWindow(original, 15)
    one = runEngine(original, first, settings, window)
    two = runEngine(changed, second, settings, window)
    keep = 41 - window.first
    assert first.answers[:keep] == second.answers[:keep]
    assert equities(one)[:keep] == equities(two)[:keep]
    cutoff = datetime(2024, 1, 1) + pd.Timedelta(days=40)
    oldFills = [fill for fill in one.fills if fill.day <= cutoff]
    newFills = [fill for fill in two.fills if fill.day <= cutoff]
    assert len(oldFills) > 0
    assert oldFills == newFills


# a strategy that damages the history it is given changes neither the data nor the results
@dataclass(frozen=True)
class Vandal(Strategy):
    description: ClassVar[str] = "overwrites its history"

    # wipe the history and then ask to be fully invested
    def decide(self, history: pd.DataFrame) -> float:
        history.iloc[:, :] = 0.0
        history["close"] = 0.0
        return 1.0


def testStrategyCannotChangeTheEngineData() -> None:
    prices = randomPrices(3, 30)
    before = prices.frame.copy()
    fair = runAll(prices, BuyAndHold(), DEFAULT)
    rough = runAll(prices, Vandal(), DEFAULT)
    assert prices.frame.equals(before)
    assert equities(rough) == equities(fair)


# the engine matches a separate vectorised formula on the sample data
def testCrossCheckAgainstVectorisedFormula(pytestconfig: pytest.Config) -> None:
    prices = loadCsv(pytestconfig.rootpath / "data" / "sampleprices.csv")
    strategy = MovingAverageCrossover(20, 100)
    settings = plainSettings(wholeShares=False)
    window = chooseWindow(prices, strategy.warmupBars)
    result = runEngine(prices, strategy, settings, window)
    frame = prices.frame
    opens = [float(price) for price in frame["open"].values]
    closes = [float(price) for price in frame["close"].values]
    above = (frame["close"].rolling(20).mean() > frame["close"].rolling(100).mean()).values
    expected = [1000.0]
    held = 0.0
    for position in range(window.first + 1, window.last + 1):
        overnight = opens[position] / closes[position - 1] - 1
        nextHeld = 1.0 if above[position - 1] else 0.0
        intraday = closes[position] / opens[position] - 1
        expected.append(expected[-1] * (1 + held * overnight) * (1 + nextHeld * intraday))
        held = nextHeld
    assert equities(result) == pytest.approx(expected, rel=1e-9)
    assert len(result.fills) > 3
    assert not math.isnan(expected[-1])
