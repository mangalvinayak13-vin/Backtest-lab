from dataclasses import replace

import hypothesis
import numpy as np
import pytest
from helpers import Scripted, plainSettings, randomPrices
from hypothesis import strategies as st

from backtestlab.engine import EngineResult, runEngine
from backtestlab.presets import DEFAULT, INDIA
from backtestlab.settings import CostModel, Settings
from backtestlab.strategies import BuyAndHold
from backtestlab.window import Window

BARS = 60
SEEDS = st.integers(0, 1000000)
SAME = hypothesis.settings(derandomize=True, deadline=None)


# a random script of targets from 0 to 1 in steps of a quarter, made from a seed
def randomTargets(seed: int) -> Scripted:
    generator = np.random.Generator(np.random.PCG64(seed + 1))
    steps = generator.integers(0, 5, size=BARS)
    return Scripted(tuple(float(step) / 4 for step in steps))


# run a script over random prices made from the same seed
def runRandom(seed: int, settings: Settings) -> EngineResult:
    prices = randomPrices(seed, BARS)
    return runEngine(prices, randomTargets(seed), settings, Window(0, BARS - 1, ()))


# the settings to try: plain, default costs, india costs, with whole and fractional shares
def variants() -> list[Settings]:
    return [
        plainSettings(),
        plainSettings(wholeShares=False),
        replace(DEFAULT, startingCash=5000.0),
        replace(DEFAULT, startingCash=5000.0, wholeShares=False),
        replace(INDIA, startingCash=20000.0),
        replace(INDIA, startingCash=300.0),
    ]


# cash and shares never go below zero, and equity is cash plus shares at the close
@SAME
@hypothesis.given(SEEDS)
def testCashAndSharesNeverNegative(seed: int) -> None:
    prices = randomPrices(seed, BARS)
    closes = [float(price) for price in prices.frame["close"].values]
    for settings in variants():
        result = runRandom(seed, settings)
        cashes = [float(value) for value in result.bars["cash"].values]
        shares = [float(value) for value in result.bars["shares"].values]
        equities = [float(value) for value in result.bars["equity"].values]
        for position, equity in enumerate(equities):
            assert cashes[position] >= 0
            assert shares[position] >= 0
            expected = cashes[position] + shares[position] * closes[position]
            assert equity == pytest.approx(expected, rel=1e-9)
        for fill in result.fills:
            assert fill.cashAfter >= 0
            assert fill.sharesAfter >= 0


# with no costs and fractional shares, buy and hold ends with cash times last close over first open
@SAME
@hypothesis.given(SEEDS)
def testBuyAndHoldWithoutCostsEndsWhereItShould(seed: int) -> None:
    prices = randomPrices(seed, BARS)
    settings = plainSettings(wholeShares=False)
    result = runEngine(prices, BuyAndHold(), settings, Window(0, BARS - 1, ()))
    firstOpen = float(prices.frame["open"].iloc[1])
    lastClose = float(prices.frame["close"].iloc[-1])
    expected = settings.startingCash * lastClose / firstOpen
    assert float(result.bars["equity"].iloc[-1]) == pytest.approx(expected, rel=1e-9)


# with fractional shares and percentage costs, costs never make the final equity higher
@SAME
@hypothesis.given(SEEDS)
def testCostsNeverHelp(seed: int) -> None:
    withCosts = replace(
        plainSettings(wholeShares=False),
        costs=CostModel(brokerageRate=0.002, buyTaxRate=0.001, sellTaxRate=0.001),
        slippageRate=0.0005,
    )
    free = runRandom(seed, plainSettings(wholeShares=False))
    paid = runRandom(seed, withCosts)
    assert float(paid.bars["equity"].iloc[-1]) <= float(free.bars["equity"].iloc[-1]) * (1 + 1e-9)
