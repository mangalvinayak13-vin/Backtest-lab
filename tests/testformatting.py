from datetime import date

import pytest

from backtestlab.formatting import formatDate, formatMoney, formatPercent


# indian grouping keeps the last three digits together and then uses pairs
@pytest.mark.parametrize(
    ("amount", "text"),
    [
        (0.0, "₹0"),
        (999.0, "₹999"),
        (1000.0, "₹1,000"),
        (100000.0, "₹1,00,000"),
        (184213.0, "₹1,84,213"),
        (12345678.0, "₹1,23,45,678"),
        (-100000.0, "-₹1,00,000"),
    ],
)
def testIndianGrouping(amount: float, text: str) -> None:
    assert formatMoney(amount, "₹", "indian") == text


# western grouping uses threes, and the default preset has no symbol
@pytest.mark.parametrize(
    ("amount", "text"),
    [(184213.0, "184,213"), (12345678.0, "12,345,678"), (999.0, "999"), (-2500.0, "-2,500")],
)
def testWesternGrouping(amount: float, text: str) -> None:
    assert formatMoney(amount, "", "western") == text


# money can have decimals, and rounds to the nearest
def testMoneyWithDecimals() -> None:
    assert formatMoney(142.3406, "₹", "indian", 2) == "₹142.34"
    assert formatMoney(1234567.891, "", "western", 2) == "1,234,567.89"
    assert formatMoney(184212.6, "₹", "indian") == "₹1,84,213"


# a tiny negative amount that rounds to zero has no minus sign
def testRoundedZeroHasNoMinus() -> None:
    assert formatMoney(-0.2, "₹", "indian") == "₹0"
    assert formatPercent(-0.00001) == "0.0%"


# percentages have one decimal place and a plain minus sign
def testPercentages() -> None:
    assert formatPercent(0.842) == "84.2%"
    assert formatPercent(-0.183) == "-18.3%"
    assert formatPercent(0.24, 0) == "24%"
    assert formatPercent(1.0) == "100.0%"


# dates are written with the month as a word
def testDates() -> None:
    assert formatDate(date(2024, 1, 2)) == "2 Jan 2024"
    assert formatDate(date(2018, 10, 18)) == "18 Oct 2018"
