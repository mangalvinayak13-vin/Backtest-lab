import pytest
from helpers import makePrices

from backtestlab.errors import DataError, SettingsError
from backtestlab.window import chooseWindow

# ten daily bars from 1 Jan 2024 to 10 Jan 2024
TEN = makePrices([(100.0 + n, 100.0 + n) for n in range(10)])


# with no start, end or warm-up the window is the whole table
def testWholeTableByDefault() -> None:
    window = chooseWindow(TEN, 0)
    assert (window.first, window.last) == (0, 9)
    assert window.warnings == ()


# a start and an end trim the window to those dates, both included
def testStartAndEndTrim() -> None:
    window = chooseWindow(TEN, 0, start="2024-01-03", end="2024-01-08")
    assert (window.first, window.last) == (2, 7)
    assert window.warnings == ()


# a start on a day with no bar moves to the next bar without a warning about warm-up
def testStartBetweenBars() -> None:
    window = chooseWindow(TEN, 0, start="2023-12-30", end="2024-01-08")
    assert window.first == 0
    assert "the data starts later" in window.warnings[0].message


# the warm-up pushes the first bar later and a warning says why
def testWarmupMovesTheStart() -> None:
    window = chooseWindow(TEN, 4, start="2024-01-01")
    assert window.first == 3
    assert window.warnings[0].code == "window-moved"
    assert window.warnings[0].message == (
        "The test starts on 4 Jan 2024 instead of 1 Jan 2024 "
        "because the strategy needs 4 days of history first."
    )


# without a start, the warm-up is compared with the first date in the data
def testWarmupWithoutStart() -> None:
    window = chooseWindow(TEN, 3)
    assert window.first == 2
    assert "instead of 1 Jan 2024" in window.warnings[0].message


# a start later than the warm-up needs gives no warning
def testLateStartNeedsNoWarning() -> None:
    window = chooseWindow(TEN, 3, start="2024-01-06")
    assert window.first == 5
    assert window.warnings == ()


# a start before the data begins gives a warning that the data starts later
def testStartBeforeData() -> None:
    window = chooseWindow(TEN, 0, start="2023-12-25")
    assert window.first == 0
    assert window.warnings[0].message == (
        "The test starts on 1 Jan 2024 instead of 25 Dec 2023 because the data starts later."
    )


# a warm-up of one bar needs no history before the first bar
def testWarmupOfOne() -> None:
    assert chooseWindow(TEN, 1).first == 0


# fewer than two bars is a data error that says how much history is needed
def testTooFewBars() -> None:
    with pytest.raises(
        DataError, match=r"needs 10 bars of history.*10 bars.*1 Jan 2024 to 10 Jan 2024"
    ):
        chooseWindow(TEN, 10)
    with pytest.raises(DataError, match="Fewer than 2 bars"):
        chooseWindow(TEN, 0, start="2024-01-10")
    with pytest.raises(DataError, match="Fewer than 2 bars"):
        chooseWindow(TEN, 0, end="2023-12-01")


# a start after the end is a data error
def testStartAfterEnd() -> None:
    with pytest.raises(DataError, match="Fewer than 2 bars"):
        chooseWindow(TEN, 0, start="2024-01-08", end="2024-01-03")


# bad dates are settings errors
def testBadDates() -> None:
    with pytest.raises(SettingsError, match="start date 'soon'"):
        chooseWindow(TEN, 0, start="soon")
    with pytest.raises(SettingsError, match="end date 'later'"):
        chooseWindow(TEN, 0, end="later")
