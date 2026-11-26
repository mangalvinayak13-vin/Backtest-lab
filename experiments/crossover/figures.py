from datetime import datetime
from pathlib import Path

import matplotlib.style
import numpy
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from measures import outOfMarket
from plan import CHARTS, LONGS, NAMES, OLDER, PROMISED, RECENT, SHORTS, STOCKS, Period, Run
from records import Row

from backtestlab.backtest import BacktestResult

STRATEGY = "#0072B2"
HOLD = "#E69F00"
SHADES = ("#9ecae1", "#6baed6", "#3182bd", "#08519c")
STYLE = {
    "font.size": 13,
    "axes.titlesize": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.formatter.useoffset": False,
    "axes.grid": False,
}
SETUP = "India preset: ₹1,00,000, Indian charges, whole shares. Seed 42."


# "all 12", "none of the 12" or "3 of 12"
def share(count: int, total: int) -> str:
    if count == total:
        return f"all {total}"
    if count == 0:
        return f"none of the {total}"
    return f"{count} of {total}"


# the number in one column of a row
def number(row: Row, column: str) -> float:
    return float(row[column])


# the row of one run with seed 42, from the promised tests or the extra ones
def findRow(rows: list[Row], period: Period, ticker: str, shortWindow: int, longWindow: int) -> Row:
    for row in rows:
        same = (row["period"], row["ticker"], row["shortWindow"], row["longWindow"], row["seed"])
        if same == (period.name, ticker, shortWindow, longWindow, 42):
            return row
    raise KeyError(f"no row for {ticker} {shortWindow}/{longWindow} in {period.name}")


# strategy minus buy and hold for each stock and each promised long window
def gapGrid(rows: list[Row], period: Period, column: str) -> list[list[float]]:
    return [
        [number(findRow(rows, period, ticker, 50, longWindow), column) for longWindow in PROMISED]
        for ticker in STOCKS
    ]


# a portrait figure the size of a carousel page
def newFigure(title: str, footnote: str) -> Figure:
    figure = Figure(figsize=(7.2, 9), layout="constrained")
    figure.suptitle(title, fontsize=16, fontweight="bold")
    figure.supxlabel(footnote, fontsize=10, color="#555555")
    return figure


# save a figure at 1080 by 1350 pixels
def save(figure: Figure, name: str) -> None:
    if not CHARTS.exists():
        CHARTS.mkdir(parents=True)
    figure.savefig(Path(CHARTS / name), dpi=150)


# a grid of coloured cells with the value written in each one
def drawGrid(
    ax: Axes,
    grid: list[list[float]],
    labels: tuple[list[str], list[str]],
    scale: tuple[str, float, float],
) -> AxesImage:
    colours, low, high = scale
    image = ax.imshow(numpy.array(grid), cmap=colours, vmin=low, vmax=high, aspect="auto")
    for rowNumber, values in enumerate(grid):
        for columnNumber, value in enumerate(values):
            if not numpy.isnan(value):
                text = f"{value:.1f}%" if colours == "Blues" else f"{value:+.1f}"
                ax.text(
                    columnNumber,
                    rowNumber,
                    text,
                    ha="center",
                    va="center",
                    fontsize=13,
                    color=textColour(image, value),
                )
    ax.set(
        xticks=range(len(labels[1])),
        xticklabels=labels[1],
        yticks=range(len(labels[0])),
        yticklabels=labels[0],
    )
    return image


# white text on dark cells and black text on light ones
def textColour(image: AxesImage, value: float) -> str:
    colour = numpy.asarray(image.cmap(image.norm(numpy.array([value])))).reshape(-1)
    red, green, blue = float(colour[0]), float(colour[1]), float(colour[2])
    return "white" if 0.299 * red + 0.587 * green + 0.114 * blue < 0.5 else "black"


# the stock names and the promised window pairs, for the 3 by 4 grids
def promisedLabels() -> tuple[list[str], list[str]]:
    return [NAMES[ticker] for ticker in STOCKS], [f"50/{window}" for window in PROMISED]


# how many tests lost to buy and hold
def countLost(grid: list[list[float]]) -> int:
    return sum(1 for values in grid for value in values if value < 0)


# chart: strategy minus buy and hold for the 12 promised tests
def drawHeatmap(rows: list[Row]) -> None:
    grid = gapGrid(rows, RECENT, "gapPoints")
    limit = max(abs(value) for values in grid for value in values)
    title = f"Buy and hold beat the crossover\nin {share(countLost(grid), 12)} tests, 2018 to 2024"
    figure = newFigure(title, SETUP)
    ax = figure.subplots()
    image = drawGrid(ax, grid, promisedLabels(), ("RdBu", -limit, limit))
    ax.set(xlabel="Short/long moving average window (trading days)")
    figure.colorbar(
        image, ax=ax, location="bottom", label="Strategy minus buy and hold (percentage points)"
    )
    save(figure, "heatmap2018.png")


# chart: the Monte Carlo chance of beating buy and hold for the 12 promised tests
def drawChances(rows: list[Row]) -> None:
    grid = gapGrid(rows, RECENT, "mcBeatsHoldPct")
    values = [value for row in grid for value in row]
    title = (
        f"In 1,000 reshuffled histories the crossover\n"
        f"beat holding {min(values):.1f}% to {max(values):.1f}% of the time"
    )
    figure = newFigure(title, f"Blocks of 20 trading days. {SETUP}")
    ax = figure.subplots()
    image = drawGrid(ax, grid, promisedLabels(), ("Blues", 0.0, 100.0))
    ax.set(xlabel="Short/long moving average window (trading days)")
    figure.colorbar(image, ax=ax, location="bottom", label="Chance of beating buy and hold (%)")
    save(figure, "montecarlo.png")


# bars side by side for each group, with the value written on each bar
def groupedBars(ax: Axes, groups: list[str], series: list[tuple[str, str, list[float]]]) -> None:
    width = 0.84 / len(series)
    for number, (label, colour, values) in enumerate(series):
        offset = (number - (len(series) - 1) / 2) * width
        places = [group + offset for group in range(len(groups))]
        ax.bar(places, values, width, color=colour, label=label)
        for place, value in zip(places, values, strict=True):
            ax.text(
                place,
                value,
                f"{value:.0f}",
                ha="center",
                fontsize=9,
                va="top" if value < 0 else "bottom",
            )
    ax.set(xticks=range(len(groups)), xticklabels=groups)
    ax.axhline(0, color="#333333", linewidth=0.8)


# the worst fall of buy and hold and of each promised setting, for every stock
def fallSeries(rows: list[Row], prefix: str) -> list[tuple[str, str, list[float]]]:
    first = [findRow(rows, RECENT, ticker, 50, PROMISED[0]) for ticker in STOCKS]
    series = [("Buy and hold", HOLD, [number(row, f"hold{prefix}FallPct") for row in first])]
    for shade, window in zip(SHADES, PROMISED, strict=True):
        found = [findRow(rows, RECENT, ticker, 50, window) for ticker in STOCKS]
        series.append(
            (f"50/{window}", shade, [number(row, f"strategy{prefix}FallPct") for row in found])
        )
    return series


# how many tests cut the worst fall by more than one percentage point
def countSmallerFalls(rows: list[Row], prefix: str) -> int:
    found = [findRow(rows, RECENT, ticker, 50, window) for ticker in STOCKS for window in PROMISED]
    return sum(
        1
        for row in found
        if number(row, f"strategy{prefix}FallPct") - number(row, f"hold{prefix}FallPct") > 1
    )


# chart: the worst fall for the whole period and inside 2020
def drawFalls(rows: list[Row]) -> None:
    whole = countSmallerFalls(rows, "Worst")
    crash = countSmallerFalls(rows, "Crash")
    title = (
        f"The crossover cut the worst fall by over\n"
        f"1 point in {whole} of 12 tests ({crash} of 12 in 2020)"
    )
    figure = newFigure(title, SETUP)
    top, bottom = figure.subplots(2, 1)
    names = [NAMES[ticker] for ticker in STOCKS]
    for ax, prefix, heading in (
        (top, "Worst", "Worst fall, 2018 to 2024"),
        (bottom, "Crash", "Worst fall inside 2020"),
    ):
        groupedBars(ax, names, fallSeries(rows, prefix))
        lowest = min(value for series in fallSeries(rows, prefix) for value in series[2])
        ax.set(title=heading, ylabel="Fall from the high (%)", ylim=(lowest * 1.3, 0))
    top.legend(ncols=5, fontsize=9, loc="lower center")
    save(figure, "worstfall.png")


# the kept result of one promised 50/long run
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


# where each year starts, for the ticks of a chart drawn against the day number
def yearTicks(days: list[datetime]) -> tuple[list[int], list[str]]:
    places = [
        index for index, day in enumerate(days) if index == 0 or day.year != days[index - 1].year
    ]
    return places, [str(days[index].year) for index in places]


# the final value written at the right end of a line
def endLabel(ax: Axes, values: list[float], amount: float, colour: str) -> None:
    ax.text(
        len(values) - 1,
        values[-1],
        f" ₹{amount / 100000:.2f}L",
        color=colour,
        va="center",
        fontsize=11,
    )


# one panel of the growth chart, with the days out of the market shaded
def drawGrowthPanel(ax: Axes, result: BacktestResult, row: Row, ticker: str) -> None:
    days = list(result.days)
    for stretch in outOfMarket(result):
        right = days.index(stretch.back) if stretch.back is not None else len(days) - 1
        ax.axvspan(days.index(stretch.left), right, color="#e5e5e5", linewidth=0)
    strategyValues = [value / 100000 for value in result.strategyRun.equity()]
    holdValues = [value / 100000 for value in result.holdRun.equity()]
    ax.plot(holdValues, color=HOLD, linewidth=2, label="Buy and hold")
    ax.plot(strategyValues, color=STRATEGY, linewidth=2, label="50/200 crossover")
    endLabel(ax, holdValues, number(row, "holdFinalRs"), HOLD)
    endLabel(ax, strategyValues, number(row, "strategyFinalRs"), STRATEGY)
    places, years = yearTicks(days)
    ax.set(title=NAMES[ticker], ylabel="₹ lakh", xticks=places, xticklabels=years)


# chart: growth of 1 lakh for the 50/200 crossover against holding
def drawGrowth(rows: list[Row], kept: dict[Run, BacktestResult]) -> None:
    found = [findRow(rows, RECENT, ticker, 50, 200) for ticker in STOCKS]
    holdWins = sum(1 for row in found if number(row, "gapPoints") < 0)
    title = (
        f"₹1,00,000 grew more by holding than with\n"
        f"the 50/200 crossover on {share(holdWins, 3)} stocks"
    )
    figure = newFigure(title, f"Grey: the crossover is out of the market.\n{SETUP}")
    for ax, ticker, row in zip(figure.subplots(3, 1), STOCKS, found, strict=True):
        drawGrowthPanel(ax, keptResult(kept, RECENT, ticker, 200), row, ticker)
    figure.axes[0].legend(fontsize=10, loc="upper left")
    save(figure, "growth.png")


# chart: total return with costs times 0, 1 and 2, next to buy and hold
def drawCosts(rows: list[Row]) -> None:
    found = [findRow(rows, RECENT, ticker, 50, window) for ticker in STOCKS for window in PROMISED]
    freeWins = sum(
        1 for row in found if number(row, "costs0ReturnPct") > number(row, "holdReturnPct")
    )
    title = f"With zero costs, {share(freeWins, 12)} settings\nbeat buy and hold, 2018 to 2024"
    figure = newFigure(title, f"Costs are the charges, taxes and slippage.\n{SETUP}")
    groups = [f"50/{window}" for window in PROMISED]
    for ax, ticker in zip(figure.subplots(3, 1), STOCKS, strict=True):
        mine = [findRow(rows, RECENT, ticker, 50, window) for window in PROMISED]
        series = [
            (f"Costs ×{factor}", shade, [number(row, f"costs{factor}ReturnPct") for row in mine])
            for factor, shade in ((0, SHADES[0]), (1, SHADES[2]), (2, SHADES[3]))
        ]
        groupedBars(ax, groups, series)
        hold = number(mine[0], "holdReturnPct")
        ax.axhline(hold, color=HOLD, linewidth=2, linestyle="--", label="Buy and hold")
        lowest = min(0.0, *(value for item in series for value in item[2]))
        ax.set(title=NAMES[ticker], ylabel="Total return (%)", ylim=(lowest * 1.8, hold * 1.35))
    figure.axes[0].legend(ncols=4, fontsize=9, loc="upper left")
    save(figure, "costs.png")


# chart: the 12 promised tests in 2008 to 2017 above the same tests in 2018 to 2024
def drawPeriods(rows: list[Row]) -> None:
    older = gapGrid(rows, OLDER, "gapPoints")
    recent = gapGrid(rows, RECENT, "gapPoints")
    limit = max(abs(value) for grid in (older, recent) for values in grid for value in values)
    olderWins = 12 - countLost(older)
    recentWins = 12 - countLost(recent)
    title = (
        f"The crossover beat holding in {share(olderWins, 12)} tests\n"
        f"in 2008 to 2017, and {share(recentWins, 12)} in 2018 to 2024"
    )
    figure = newFigure(title, f"Strategy minus buy and hold, in percentage points.\n{SETUP}")
    top, bottom = figure.subplots(2, 1)
    drawGrid(top, older, promisedLabels(), ("RdBu", -limit, limit))
    image = drawGrid(bottom, recent, promisedLabels(), ("RdBu", -limit, limit))
    top.set(title="2008 to 2017 (includes the 2008 crash)")
    bottom.set(title="2018 to 2024 (includes the 2020 crash)")
    figure.colorbar(image, ax=[top, bottom], location="bottom", label="Percentage points")
    save(figure, "periods.png")


# the gap for every short and long window of one stock, blank where short is not below long
def plateauGrid(rows: list[Row], ticker: str) -> list[list[float]]:
    return [
        [
            number(findRow(rows, RECENT, ticker, shortWindow, longWindow), "gapPoints")
            if shortWindow < longWindow
            else float("nan")
            for longWindow in LONGS
        ]
        for shortWindow in SHORTS
    ]


# chart: one heatmap per stock over the wider grid of windows
def drawPlateaus(rows: list[Row]) -> None:
    grids = {ticker: plateauGrid(rows, ticker) for ticker in STOCKS}
    limit = max(
        abs(value)
        for grid in grids.values()
        for values in grid
        for value in values
        if not numpy.isnan(value)
    )
    for ticker, grid in grids.items():
        tried = sum(1 for values in grid for value in values if not numpy.isnan(value))
        title = (
            f"{NAMES[ticker]}: buy and hold beat the crossover\n"
            f"in {share(countLost(grid), tried)} window pairs, 2018 to 2024"
        )
        footnote = (
            "Blank cells: the short window is not below the long one.\n"
            f"No best setting is picked. {SETUP}"
        )
        figure = newFigure(title, footnote)
        ax = figure.subplots()
        labels = ([str(window) for window in SHORTS], [str(window) for window in LONGS])
        image = drawGrid(ax, grid, labels, ("RdBu", -limit, limit))
        ax.set(xlabel="Long window (trading days)", ylabel="Short window (trading days)")
        figure.colorbar(
            image, ax=ax, location="bottom", label="Strategy minus buy and hold (percentage points)"
        )
        save(figure, f"plateau{ticker.split('.')[0].lower()}.png")


# draw every chart from the rows of results.csv and the kept results
def drawAll(rows: list[Row], kept: dict[Run, BacktestResult]) -> None:
    with matplotlib.style.context(STYLE):
        drawHeatmap(rows)
        drawChances(rows)
        drawFalls(rows)
        drawGrowth(rows, kept)
        drawCosts(rows)
        drawPeriods(rows)
        drawPlateaus(rows)
