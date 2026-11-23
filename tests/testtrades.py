from datetime import datetime

import pytest
from helpers import Scripted, makePrices, plainSettings

from backtestlab.engine import runEngine
from backtestlab.trades import RoundTrip, buildRoundTrips
from backtestlab.window import Window


# the round trips of a run that follows a script, with an open one valued at the last close
def tripsFor(pairs: list[tuple[float, float]], script: tuple[float, ...]) -> list[RoundTrip]:
    prices = makePrices(pairs)
    window = Window(0, len(pairs) - 1, ())
    settings = plainSettings(wholeShares=False)
    result = runEngine(prices, Scripted(script), settings, window)
    return buildRoundTrips(result.fills, datetime(2024, 1, len(pairs)), pairs[-1][1])


# extra buys and partial sells belong to one round trip
def testExtraBuysAndPartialSellsAreOneTrip() -> None:
    flat = [(100.0, 100.0)] * 6
    trips = tripsFor(flat, (0.5, 1.0, 0.5, 0.0, 0.0, 0.0))
    assert len(trips) == 1
    trip = trips[0]
    assert trip.paid == pytest.approx(1000.0, rel=1e-9)
    assert trip.received == pytest.approx(1000.0, rel=1e-9)
    assert trip.profit == pytest.approx(0.0, abs=1e-9)
    assert trip.entryDay == datetime(2024, 1, 2)
    assert trip.exitDay == datetime(2024, 1, 5)
    assert trip.daysHeld == 3
    assert trip.isOpen is False


# two separate stretches of holding are two round trips
def testTwoSeparateTrips() -> None:
    bars = [
        (100.0, 100.0),
        (100.0, 110.0),
        (110.0, 110.0),
        (110.0, 110.0),
        (110.0, 99.0),
        (99.0, 99.0),
    ]
    trips = tripsFor(bars, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    assert len(trips) == 2
    assert trips[0].profit == pytest.approx(100.0, rel=1e-9)
    assert trips[0].returnRate == pytest.approx(0.1, rel=1e-9)
    assert trips[1].isOpen is False
    assert trips[1].entryDay > trips[0].exitDay


# a position still held at the end is an open trip valued at the last close
def testOpenTripAtTheEnd() -> None:
    bars = [(100.0, 100.0), (100.0, 110.0), (110.0, 120.0)]
    trips = tripsFor(bars, (1.0, 1.0, 1.0))
    assert len(trips) == 1
    trip = trips[0]
    assert trip.isOpen is True
    assert trip.paid == pytest.approx(1000.0, rel=1e-9)
    assert trip.received == pytest.approx(1200.0, rel=1e-9)
    assert trip.profit == pytest.approx(200.0, rel=1e-9)
    assert trip.returnRate == pytest.approx(0.2, rel=1e-9)
    assert trip.daysHeld == 1


# no fills means no round trips
def testNoFillsNoTrips() -> None:
    assert buildRoundTrips((), datetime(2024, 1, 4), 100.0) == []
