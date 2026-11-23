from dataclasses import dataclass
from datetime import datetime

from backtestlab.engine import Fill


# a stretch of time holding shares, from the first buy until the shares are all sold
@dataclass(frozen=True)
class RoundTrip:
    entryDay: datetime
    exitDay: datetime
    daysHeld: int
    paid: float
    received: float
    profit: float
    returnRate: float
    isOpen: bool


# a finished or open round trip, with profit and return worked out
def makeTrip(
    entryDay: datetime, exitDay: datetime, paid: float, received: float, isOpen: bool
) -> RoundTrip:
    profit = received - paid
    return RoundTrip(
        entryDay, exitDay, (exitDay - entryDay).days, paid, received, profit, profit / paid, isOpen
    )


# build the round trips from the fills, with an open one valued at the last close
def buildRoundTrips(
    fills: tuple[Fill, ...], lastDay: datetime, lastClose: float
) -> list[RoundTrip]:
    trips: list[RoundTrip] = []
    entryDay = lastDay
    paid = received = holding = 0.0
    for fill in fills:
        if fill.side == "buy":
            if holding == 0:
                entryDay, paid, received = fill.day, 0.0, 0.0
            paid += fill.orderValue + fill.costs.total
        else:
            received += fill.orderValue - fill.costs.total
        holding = fill.sharesAfter
        if holding == 0:
            trips.append(makeTrip(entryDay, fill.day, paid, received, False))
    if holding > 0:
        trips.append(makeTrip(entryDay, lastDay, paid, received + holding * lastClose, True))
    return trips
