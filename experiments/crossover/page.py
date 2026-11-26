from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import jinja2
from crosscheck import Check
from measures import outOfMarket, timesOutDuring
from plan import HERE, NAMES, OLDER, RECENT, STOCKS, Period, Run
from records import Row

from backtestlab.api import presets
from backtestlab.backtest import BacktestResult
from backtestlab.formatting import formatDate, formatMoney

# what PROGRESS.md and my posts said about the 50/200 runs: strategy, buy and hold, trades
EARLIER = {
    "TCS.NS": (162.6, 253.7, 3),
    "RELIANCE.NS": (39.7, 199.1, 6),
    "HDFCBANK.NS": (22.8, 100.9, 5),
}
EARLIERNIFTY = 124.5


# facts about the data that the page mentions
@dataclass(frozen=True)
class Context:
    downloaded: str
    indexAsset: str
    etfNotes: tuple[str, ...]
    period: Period


# a markdown table from a header and rows of text
def table(head: list[str], body: list[list[str]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(cells) + " |" for cells in body]
    return "\n".join(lines)


# a number from a row
def number(row: Row, column: str) -> float:
    return float(row[column])


# a percentage with one decimal, or n/a
def pct(row: Row, column: str) -> str:
    return "n/a" if row[column] == "" else f"{number(row, column):.1f}%"


# percentage points with a sign
def points(row: Row, column: str) -> str:
    return f"{number(row, column):+.1f}"


# rupees with Indian grouping
def money(row: Row, column: str) -> str:
    return formatMoney(number(row, column), "₹", "indian")


# an ISO date written out, or a fallback when it is blank
def day(text: object, fallback: str = "n/a") -> str:
    return formatDate(date.fromisoformat(str(text))) if text else fallback


# the stock name and the windows, the first two cells of most tables
def label(row: Row) -> list[str]:
    return [NAMES[str(row["ticker"])], f"{row['shortWindow']}/{row['longWindow']}"]


# the rows of one part and period with seed 42
def select(rows: list[Row], part: str, period: Period) -> list[Row]:
    return [row for row in rows if row["part"] == part and row["period"] == period.name]


# the kept result of one run
def keptResult(
    kept: dict[Run, BacktestResult], period: Period, ticker: str, longWindow: int
) -> BacktestResult:
    for run, result in kept.items():
        if (run.period, run.ticker, run.shortWindow, run.longWindow) == (
            period,
            ticker,
            50,
            longWindow,
        ):
            return result
    raise KeyError(f"no kept result for {ticker} 50/{longWindow}")


# returns and final values
def returnsTable(rows: list[Row]) -> str:
    head = [
        "Stock",
        "Windows",
        "Strategy final value",
        "Strategy return",
        "Buy and hold return",
        "NIFTY 50 return",
        "Strategy minus hold (points)",
    ]
    body = [
        [
            *label(row),
            money(row, "strategyFinalRs"),
            pct(row, "strategyReturnPct"),
            pct(row, "holdReturnPct"),
            pct(row, "niftyReturnPct"),
            points(row, "gapPoints"),
        ]
        for row in rows
    ]
    return table(head, body)


# annualised return, volatility and Sharpe ratio, strategy then hold
def riskTable(rows: list[Row]) -> str:
    head = ["Stock", "Windows", "Annualised return", "Volatility", "Sharpe ratio"]
    body = []
    for row in rows:
        sharpe = f"{number(row, 'strategySharpe'):.2f} / {number(row, 'holdSharpe'):.2f}"
        body.append(
            [
                *label(row),
                f"{pct(row, 'strategyAnnualPct')} / {pct(row, 'holdAnnualPct')}",
                f"{pct(row, 'strategyVolatilityPct')} / {pct(row, 'holdVolatilityPct')}",
                sharpe,
            ]
        )
    return table(head, body)


# a fall with its dates
def fallCell(row: Row, prefix: str) -> str:
    peak = day(row[prefix + "Peak"], "no fall")
    trough = day(row[prefix + "Trough"], "no fall")
    return f"{pct(row, prefix + 'FallPct')} ({peak} to {trough})"


# the worst fall over the whole period and inside the crash year
def fallTable(rows: list[Row]) -> str:
    year = rows[0]["crashYear"]
    head = [
        "Stock",
        "Windows",
        "Worst fall, strategy",
        "Worst fall, buy and hold",
        f"Worst fall in {year}, strategy",
        f"Worst fall in {year}, buy and hold",
    ]
    body = [
        [
            *label(row),
            fallCell(row, "strategyWorst"),
            fallCell(row, "holdWorst"),
            fallCell(row, "strategyCrash"),
            fallCell(row, "holdCrash"),
        ]
        for row in rows
    ]
    return table(head, body)


# a length in trading days, marked when the stretch was still open at the end
def daysCell(row: Row, name: str) -> str:
    still = " (still under at the end)" if row[name + "Open"] == "yes" else ""
    return f"{row[name + 'Days']}{still}"


# the longest time under water and the stretch that holds the crash-year low
def underwaterTable(rows: list[Row]) -> str:
    year = rows[0]["crashYear"]
    head = [
        "Stock",
        "Windows",
        "Longest under water, strategy",
        "Longest under water, buy and hold",
        "Same in calendar days (strategy / hold)",
        f"Stretch with the {year} low (strategy / hold)",
    ]
    body = [
        [
            *label(row),
            daysCell(row, "strategyUnderwater"),
            daysCell(row, "holdUnderwater"),
            f"{row['strategyUnderwaterCalendarDays']} / {row['holdUnderwaterCalendarDays']}",
            f"{daysCell(row, 'strategyCrashStretch')} / {daysCell(row, 'holdCrashStretch')}",
        ]
        for row in rows
    ]
    return table(head, body)


# how much the strategy traded and what it paid
def tradingTable(rows: list[Row]) -> str:
    head = [
        "Stock",
        "Windows",
        "Time in the market",
        "Round trips",
        "Win rate",
        "Charges and taxes",
        "Slippage",
    ]
    body = [
        [
            *label(row),
            pct(row, "timeInMarketPct"),
            str(row["roundTrips"]),
            pct(row, "winRatePct"),
            money(row, "costsRs"),
            money(row, "slippageRs"),
        ]
        for row in rows
    ]
    return table(head, body)


# the Monte Carlo chance of beating buy and hold and the spread of final values
def monteCarloTable(rows: list[Row]) -> str:
    head = [
        "Stock",
        "Windows",
        "Chance of beating buy and hold",
        "5th percentile final value",
        "Median final value",
        "95th percentile final value",
    ]
    body = [
        [
            *label(row),
            pct(row, "mcBeatsHoldPct"),
            money(row, "mcFinalP5Rs"),
            money(row, "mcFinalP50Rs"),
            money(row, "mcFinalP95Rs"),
        ]
        for row in rows
    ]
    return table(head, body)


# the strategy with costs times 0, 1 and 2
def costsTable(rows: list[Row]) -> str:
    head = [
        "Stock",
        "Windows",
        "Return, costs ×0",
        "×1",
        "×2",
        "Annualised ×0 / ×1 / ×2",
        "Sharpe ×0 / ×1 / ×2",
        "Buy and hold return",
    ]
    body = []
    for row in rows:
        annual = " / ".join(pct(row, f"costs{factor}AnnualPct") for factor in (0, 1, 2))
        sharpe = " / ".join(f"{number(row, f'costs{factor}Sharpe'):.2f}" for factor in (0, 1, 2))
        returns = [pct(row, f"costs{factor}ReturnPct") for factor in (0, 1, 2)]
        body.append(label(row) + returns + [annual, sharpe, pct(row, "holdReturnPct")])
    return table(head, body)


# every warning the tool gave
def warningsTable(rows: list[Row]) -> str:
    body = [[*label(row), str(row["warnings"]).replace(" | ", " ")] for row in rows]
    return table(["Stock", "Windows", "Warnings from backtestlab"], body)


# the round trips of one 50/200 run, without prices
def tripsTable(result: BacktestResult) -> str:
    body = []
    for trip in result.strategyRun.trips:
        sold = "still held at the end" if trip.isOpen else formatDate(trip.exitDay)
        body.append(
            [formatDate(trip.entryDay), sold, str(trip.daysHeld), f"{trip.returnRate * 100:+.1f}%"]
        )
    return table(["Bought", "Sold", "Days held", "Result after costs"], body)


# when each 50/200 run was out of the market during the crash year, and what holding made meanwhile
def outTable(kept: dict[Run, BacktestResult], year: int) -> str:
    body = []
    for ticker in STOCKS:
        stretches = outOfMarket(keptResult(kept, RECENT, ticker, 200))
        for stretch in timesOutDuring(stretches, year):
            back = "not before the end" if stretch.back is None else formatDate(stretch.back)
            gain = f"{stretch.holdGain() * 100:+.1f}%"
            body.append([NAMES[ticker], formatDate(stretch.left), back, gain])
    head = ["Stock", "Sold (out of the market)", "Bought back", "Holding gained in between"]
    return table(head, body)


# the first exit of each 50/200 run in the crash year, read back from the rows
def exitFacts(rows: list[Row]) -> dict[str, object]:
    found = [row for row in select(rows, "1", RECENT) if row["longWindow"] == 200]
    sold = sorted(str(row["crashOutFrom"]) for row in found)
    back = sorted(str(row["crashOutTo"]) for row in found if row["crashOutTo"])
    gains = sorted(number(row, "crashOutHoldGainPct") for row in found)
    return {
        "sold": (day(sold[0]), day(sold[-1])),
        "back": (day(back[0]), day(back[-1])),
        "gain": (gains[0], gains[-1]),
    }


# the chance of beating buy and hold with seed 42 and with seeds 1 to 5
def seedsTable(rows: list[Row]) -> str:
    body = []
    for row in select(rows, "1", RECENT):
        others = [
            number(other, "mcBeatsHoldPct")
            for other in rows
            if other["part"] == "2-seeds"
            and other["ticker"] == row["ticker"]
            and other["longWindow"] == row["longWindow"]
        ]
        body.append(
            [*label(row), pct(row, "mcBeatsHoldPct"), f"{min(others):.1f}% to {max(others):.1f}%"]
        )
    return table(["Stock", "Windows", "Seed 42", "Seeds 1 to 5"], body)


# the idle cash estimate next to the tool's own numbers
def idleTable(rows: list[Row]) -> str:
    head = [
        "Stock",
        "Windows",
        "Strategy minus hold, cash at 0%",
        "Same with cash at 6%",
        "Strategy return with 6%",
        "Buy and hold return with 6%",
    ]
    body = [
        [
            *label(row),
            points(row, "gapPoints"),
            points(row, "idleGapPoints"),
            pct(row, "idleStrategyReturnPct"),
            pct(row, "idleHoldReturnPct"),
        ]
        for row in rows
    ]
    return table(head, body)


# the older period, in one table
def olderTable(rows: list[Row]) -> str:
    head = [
        "Stock",
        "Windows",
        "Strategy return",
        "Buy and hold return",
        "NIFTY 50 return",
        "Strategy minus hold (points)",
        "Worst fall in 2008 (strategy / hold)",
        "Chance of beating hold",
        "Round trips",
    ]
    body = [
        [
            *label(row),
            pct(row, "strategyReturnPct"),
            pct(row, "holdReturnPct"),
            pct(row, "niftyReturnPct"),
            points(row, "gapPoints"),
            f"{pct(row, 'strategyCrashFallPct')} / {pct(row, 'holdCrashFallPct')}",
            pct(row, "mcBeatsHoldPct"),
            str(row["roundTrips"]),
        ]
        for row in rows
    ]
    return table(head, body)


# the index and the fallen stock, in one table
def assetsTable(rows: list[Row]) -> str:
    head = [
        "Asset",
        "Windows",
        "Strategy return",
        "Buy and hold return",
        "Strategy minus hold (points)",
        "Worst fall (strategy / hold)",
        "Chance of beating hold",
        "Round trips",
        "Warnings",
    ]
    body = [
        [
            *label(row),
            pct(row, "strategyReturnPct"),
            pct(row, "holdReturnPct"),
            points(row, "gapPoints"),
            f"{pct(row, 'strategyWorstFallPct')} / {pct(row, 'holdWorstFallPct')}",
            pct(row, "mcBeatsHoldPct"),
            str(row["roundTrips"]),
            str(row["warningCodes"]),
        ]
        for row in rows
    ]
    return table(head, body)


# the hand-worked checks against the tool
def checksTable(checks: list[Check]) -> str:
    body = [
        [
            NAMES[check.ticker],
            check.name,
            f"{check.byHand:.10g}",
            f"{check.tool:.10g}",
            "yes" if check.matches() else "no",
        ]
        for check in checks
    ]
    return table(["Stock", "Number", "Worked out by hand", "From backtestlab", "Match"], body)


# today's 50/200 numbers next to the ones I posted before
def earlierTable(rows: list[Row]) -> str:
    body = []
    for row in select(rows, "1", RECENT):
        if row["longWindow"] == 200:
            mine, hold, trades = EARLIER[str(row["ticker"])]
            body.append(
                [
                    NAMES[str(row["ticker"])],
                    f"{mine}% / {pct(row, 'strategyReturnPct')}",
                    f"{hold}% / {pct(row, 'holdReturnPct')}",
                    f"{trades} / {row['roundTrips']}",
                ]
            )
    nifty = pct(select(rows, "1", RECENT)[0], "niftyReturnPct")
    body.append(["NIFTY 50", "", f"{EARLIERNIFTY}% / {nifty}", ""])
    return table(
        [
            "Stock",
            "Strategy (earlier / now)",
            "Buy and hold (earlier / now)",
            "Round trips (earlier / now)",
        ],
        body,
    )


# how many rows pass a test
def count(rows: list[Row], test: Callable[[Row], bool]) -> int:
    return sum(1 for row in rows if test(row))


# whether the strategy cut a fall by more than one percentage point
def smaller(row: Row, prefix: str) -> bool:
    return number(row, f"strategy{prefix}FallPct") - number(row, f"hold{prefix}FallPct") > 1


# whether the strategy stayed under water longer, in one of the two ways of counting
def longer(row: Row, column: str) -> bool:
    return number(row, f"strategy{column}") > number(row, f"hold{column}")


# the smallest and largest value of one column
def spread(rows: list[Row], column: str) -> tuple[float, float]:
    values = [number(row, column) for row in rows]
    return min(values), max(values)


# the counts and ranges for the 12 promised tests
def promisedFacts(rows: list[Row]) -> dict[str, object]:
    promised = select(rows, "1", RECENT)
    costEffects = [
        number(row, "costs0ReturnPct") - number(row, "strategyReturnPct") for row in promised
    ]
    return {
        "lost": count(promised, lambda row: number(row, "gapPoints") < 0),
        "gap": spread(promised, "gapPoints"),
        "chance": spread(promised, "mcBeatsHoldPct"),
        "smallerFalls": count(promised, lambda row: smaller(row, "Worst")),
        "smallerCrashFalls": count(promised, lambda row: smaller(row, "Crash")),
        "longerUnder": count(promised, lambda row: longer(row, "UnderwaterDays")),
        "longerUnderCalendar": count(promised, lambda row: longer(row, "UnderwaterCalendarDays")),
        "freeWins": count(
            promised, lambda row: number(row, "costs0ReturnPct") > number(row, "holdReturnPct")
        ),
        "costEffect": (min(costEffects), max(costEffects)),
        "idleFlips": count(promised, lambda row: number(row, "idleGapPoints") > 0),
        "trips": spread(promised, "roundTrips"),
    }


# the most that changing the seed moved one test's chance of beating buy and hold, in points
def seedMove(rows: list[Row]) -> float:
    moves = []
    for row in select(rows, "1", RECENT):
        chances = [
            number(other, "mcBeatsHoldPct")
            for other in rows
            if other["part"] in ("1", "2-seeds")
            and (other["ticker"], other["longWindow"]) == (row["ticker"], row["longWindow"])
        ]
        moves.append(max(chances) - min(chances))
    return max(moves)


# the counts and ranges for the checks I added
def extraFacts(rows: list[Row]) -> dict[str, object]:
    older = select(rows, "2-crash", OLDER)
    assets = select(rows, "2-assets", RECENT)
    fallen = [row for row in assets if row["ticker"] == "YESBANK.NS"]
    index = [row for row in assets if row["ticker"] != "YESBANK.NS"]
    plateau = [
        row for row in rows if row["period"] == RECENT.name and row["part"] in ("1", "2-plateau")
    ]
    return {
        "seed": spread([row for row in rows if row["part"] == "2-seeds"], "mcBeatsHoldPct"),
        "seedMove": seedMove(rows),
        "plateauTried": len(plateau),
        "plateauWins": count(plateau, lambda row: number(row, "gapPoints") > 0),
        "olderWins": count(older, lambda row: number(row, "gapPoints") > 0),
        "olderSmallerCrash": count(older, lambda row: smaller(row, "Crash")),
        "olderLongerUnder": count(older, lambda row: longer(row, "UnderwaterDays")),
        "idleFlipsOlder": count(
            older, lambda row: number(row, "gapPoints") < 0 < number(row, "idleGapPoints")
        ),
        "indexWins": count(index, lambda row: number(row, "gapPoints") > 0),
        "fallenWins": count(fallen, lambda row: number(row, "gapPoints") > 0),
        "fallenReturn": spread(fallen, "strategyReturnPct"),
        "fallenHold": number(fallen[0], "holdReturnPct"),
    }


# the tables, keyed by the name the template uses
def tables(rows: list[Row], kept: dict[Run, BacktestResult], checks: list[Check]) -> dict[str, str]:
    promised = select(rows, "1", RECENT)
    trips = {NAMES[ticker]: tripsTable(keptResult(kept, RECENT, ticker, 200)) for ticker in STOCKS}
    return {
        "returns": returnsTable(promised),
        "risk": riskTable(promised),
        "falls": fallTable(promised),
        "underwater": underwaterTable(promised),
        "trading": tradingTable(promised),
        "monteCarlo": monteCarloTable(promised),
        "costs": costsTable(promised),
        "warnings": warningsTable(promised),
        "trips": "\n\n".join(f"{name}\n\n{text}" for name, text in trips.items()),
        "out": outTable(kept, RECENT.crashYear),
        "seeds": seedsTable(rows),
        "idle": idleTable(promised),
        "older": olderTable(select(rows, "2-crash", OLDER)),
        "olderUnderwater": underwaterTable(select(rows, "2-crash", OLDER)),
        "assets": assetsTable(select(rows, "2-assets", RECENT)),
        "checks": checksTable(checks),
        "earlier": earlierTable(rows),
    }


# the settings everyone can check against the india preset
def settingsText() -> dict[str, object]:
    india = presets.INDIA
    return {
        "cash": formatMoney(india.startingCash, "₹", "indian"),
        "slippage": f"{india.slippageRate * 100:.2f}%",
        "wholeShares": india.wholeShares,
        "benchmarkLabel": india.benchmarkLabel,
        "simulations": f"{india.simulations:,}",
        "blockLength": india.blockLength,
        "seed": india.seed,
        "costsChecked": day(india.costsCheckedOn),
        "costNotes": india.costNotes,
    }


# write RESULTS.md from the template, the rows and the kept results
def writePage(
    rows: list[Row], kept: dict[Run, BacktestResult], checks: list[Check], context: Context
) -> None:
    with (HERE / "template.md").open(encoding="utf-8") as file:
        template = jinja2.Template(file.read())
    text = template.render(
        tables=tables(rows, kept, checks),
        facts=promisedFacts(rows) | extraFacts(rows),
        exits=exitFacts(rows),
        settings=settingsText(),
        downloaded=formatDate(date.fromisoformat(context.downloaded)),
        indexAsset=context.indexAsset,
        etfNotes=context.etfNotes,
        checksPassed=all(check.matches() for check in checks),
        runCount=len(rows),
    )
    with (HERE / "RESULTS.md").open("w", encoding="utf-8") as file:
        file.write(text.rstrip() + "\n")
