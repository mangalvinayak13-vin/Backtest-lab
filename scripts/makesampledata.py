import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

SEED = 2019
BARS = 1305
FIRSTDAY = date(2019, 1, 2)
STARTPRICE = 1000.0


# the repository folder is one level above scripts
def findRoot() -> Path:
    return Path(sys.argv[0]).resolve().parent.parent


# every weekday from the first day on, with no holidays
def tradingDays() -> list[date]:
    days: list[date] = []
    day = FIRSTDAY
    while len(days) < BARS:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


# the length, daily drift and daily volatility of each calm rising or choppy falling spell
def makeSpells(generator: np.random.Generator) -> list[tuple[int, float, float]]:
    spells: list[tuple[int, float, float]] = []
    total = 0
    rising = True
    while total < BARS:
        length = int(generator.integers(42, 127))
        spells.append((length, 0.0012, 0.007) if rising else (length, -0.0015, 0.016))
        total += length
        rising = not rising
    return spells


# the drift and volatility to use on each day
def dailySettings(generator: np.random.Generator) -> list[tuple[float, float]]:
    settings: list[tuple[float, float]] = []
    for length, drift, volatility in makeSpells(generator):
        settings.extend([(drift, volatility)] * length)
    return settings[:BARS]


# one bar as open, high, low, close and volume, with consistent prices
def makeBar(
    generator: np.random.Generator, previous: float, drift: float, volatility: float
) -> tuple[float, float, float, float, int]:
    openPrice = round(previous * float(np.exp(0.3 * volatility * generator.normal())), 2)
    closePrice = round(openPrice * float(np.exp(drift + volatility * generator.normal())), 2)
    reach = 0.3 * volatility * abs(float(generator.normal()))
    highPrice = max(round(max(openPrice, closePrice) * (1 + reach), 2), openPrice, closePrice)
    reach = 0.3 * volatility * abs(float(generator.normal()))
    lowPrice = min(round(min(openPrice, closePrice) * (1 - reach), 2), openPrice, closePrice)
    busy = 1.5 if drift < 0 else 1.0
    volume = int(1000000 * busy * float(np.exp(0.3 * generator.normal())))
    return openPrice, highPrice, lowPrice, closePrice, volume


# all the rows of the sample file, as text
def makeRows() -> list[list[str]]:
    generator = np.random.Generator(np.random.PCG64(SEED))
    settings = dailySettings(generator)
    rows = [["date", "open", "high", "low", "close", "volume"]]
    previous = STARTPRICE
    for day, (drift, volatility) in zip(tradingDays(), settings, strict=True):
        openPrice, highPrice, lowPrice, closePrice, volume = makeBar(
            generator, previous, drift, volatility
        )
        rows.append(
            [
                day.isoformat(),
                f"{openPrice:.2f}",
                f"{highPrice:.2f}",
                f"{lowPrice:.2f}",
                f"{closePrice:.2f}",
                str(volume),
            ]
        )
        previous = closePrice
    return rows


# write the sample file, to the path given on the command line or to data/sampleprices.csv
def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else findRoot() / "data" / "sampleprices.csv"
    with target.open("w", encoding="utf-8", newline="") as file:
        csv.writer(file, lineterminator="\n").writerows(makeRows())
    print(f"Wrote {BARS} bars to {target}")
    return 0


sys.exit(main())
