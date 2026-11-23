import math
from dataclasses import replace
from typing import Any

import pytest

from backtestlab.errors import SettingsError
from backtestlab.presets import DEFAULT, INDIA
from backtestlab.settings import CostModel, Settings


# the two presets pass their own checks
def testPresetsAreValid() -> None:
    DEFAULT.check()
    INDIA.check()
    Settings().check()


# the default preset has no currency symbol, western grouping and no benchmark
def testDefaultPresetValues() -> None:
    assert DEFAULT.presetName == "default"
    assert DEFAULT.currencySymbol == ""
    assert DEFAULT.grouping == "western"
    assert DEFAULT.startingCash == 100000.0
    assert DEFAULT.costs == CostModel(brokerageRate=0.001, brokerageCap=None)
    assert DEFAULT.slippageRate == 0.0005
    assert DEFAULT.wholeShares is True
    assert DEFAULT.tradingDaysPerYear == 252
    assert DEFAULT.riskFreeRate == 0.0
    assert DEFAULT.benchmarkTicker is None
    assert (DEFAULT.simulations, DEFAULT.blockLength, DEFAULT.seed) == (1000, 20, 42)


# the india preset has the charges from the table in the notes
def testIndiaPresetValues() -> None:
    assert INDIA.currencySymbol == "₹"
    assert INDIA.grouping == "indian"
    assert INDIA.costs.brokerageCap == 20.0
    assert INDIA.costs.buyTaxRate == 0.00115
    assert INDIA.costs.sellTaxRate == 0.001
    assert INDIA.costs.exchangeFeeRate == 0.0000317
    assert INDIA.costs.taxOnFeesRate == 0.18
    assert INDIA.costs.sellFeePerOrder == 15.34
    assert INDIA.benchmarkTicker == "^NSEI"
    assert INDIA.benchmarkLabel == "NIFTY 50 (price index, excludes dividends)"
    assert INDIA.costsCheckedOn == "2026-11-23"
    assert len(INDIA.costNotes) == 7


# overrides use dataclasses.replace and leave the preset alone
def testOverridesDoNotChangeThePreset() -> None:
    changed = replace(INDIA, startingCash=50000.0)
    assert changed.startingCash == 50000.0
    assert INDIA.startingCash == 100000.0


# every bad value gives a settings error that names the setting
@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"startingCash": 0.0}, "Starting cash must be above 0"),
        ({"startingCash": -5.0}, "Starting cash must be above 0"),
        ({"startingCash": math.nan}, "Starting cash must be above 0"),
        ({"slippageRate": 1.0}, "slippageRate must be from 0 up to"),
        ({"slippageRate": -0.1}, "slippageRate must be from 0 up to"),
        ({"grouping": "european"}, "grouping must be indian or western"),
        ({"tradingDaysPerYear": 0}, "tradingDaysPerYear must be at least 1"),
        ({"riskFreeRate": 1.0}, "riskFreeRate must be between"),
        ({"simulations": 99}, "simulations must be from 100 to 5000"),
        ({"simulations": 5001}, "simulations must be from 100 to 5000"),
        ({"blockLength": 0}, "blockLength must be at least 1"),
    ],
)
def testBadSettingsAreRejected(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(SettingsError, match=message):
        replace(DEFAULT, **changes).check()


# the edges of the allowed ranges are accepted
def testEdgesAreAccepted() -> None:
    replace(DEFAULT, simulations=100, blockLength=1, slippageRate=0.0).check()
    replace(DEFAULT, simulations=5000, slippageRate=0.999).check()


# bad costs are rejected too
@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"brokerageRate": 1.0}, "brokerageRate must be from 0 up to"),
        ({"buyTaxRate": -0.001}, "buyTaxRate must be from 0 up to"),
        ({"sellTaxRate": 2.0}, "sellTaxRate must be from 0 up to"),
        ({"exchangeFeeRate": 1.5}, "exchangeFeeRate must be from 0 up to"),
        ({"taxOnFeesRate": -1.0}, "taxOnFeesRate must be from 0 up to"),
        ({"brokerageCap": -1.0}, "brokerageCap must be 0 or more"),
        ({"sellFeePerOrder": -0.5}, "sellFeePerOrder must be 0 or more"),
        ({"sellFeePerOrder": math.inf}, "sellFeePerOrder must be 0 or more"),
    ],
)
def testBadCostsAreRejected(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(SettingsError, match=message):
        replace(DEFAULT, costs=CostModel(**changes)).check()
