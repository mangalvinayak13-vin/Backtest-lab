import io
import re
from collections.abc import Callable

import matplotlib.style
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from backtestlab.backtest import BacktestResult

BLUE = "#2166ac"
ORANGE = "#e08214"
GREY = "#7f7f7f"
INK = "#333333"
STYLE = {
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.formatter.useoffset": False,
    "axes.edgecolor": "#999999",
    "axes.labelcolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "xtick.color": INK,
    "ytick.color": INK,
    "font.size": 9,
    "svg.fonttype": "path",
    "svg.hashsalt": "backtestlab",
}


# keep only the svg element, without the file header, the metadata or the group names
def cleanSvg(text: str) -> str:
    text = text[text.index("<svg") :]
    text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return re.sub(r'<g id="[^"]*"', "<g", text)


# draw one chart with the house style and give it back as svg text
def drawChart(draw: Callable[[Axes], None]) -> str:
    with matplotlib.style.context(STYLE):
        figure = Figure(figsize=(9, 3.4), layout="constrained")
        axes = figure.subplots()
        draw(axes)
        axes.grid(visible=True, color="#dddddd", linewidth=0.6)
        buffer = io.StringIO()
        figure.savefig(buffer, format="svg", metadata={"Date": None})
    return cleanSvg(buffer.getvalue())


# the test dates as a numpy array, which matplotlib draws as a date axis
def dayArray(result: BacktestResult) -> np.ndarray:
    return np.array(result.days, dtype="datetime64[D]")


# values scaled so the first one is 100
def growthOf100(values: list[float]) -> list[float]:
    return [value / values[0] * 100 for value in values]


# the fall from the highest value so far, in percent
def fallsInPercent(values: list[float]) -> list[float]:
    numbers = np.array(values)
    return [float(value) * 100 for value in numbers / np.maximum.accumulate(numbers) - 1]


# chart 1: growth of 100 for the strategy, buy and hold and the index
def growthChart(result: BacktestResult) -> str:
    def draw(axes: Axes) -> None:
        days = dayArray(result)
        axes.plot(days, growthOf100(result.strategyRun.equity()), color=BLUE, label="Strategy")
        axes.plot(days, growthOf100(result.holdRun.equity()), color=ORANGE, label="Buy and hold")
        if result.benchmark is not None:
            values = growthOf100(list(result.benchmark.values))
            axes.plot(days, values, color=GREY, label=result.benchmark.label)
        axes.set(title="Growth of 100", xlabel="Date", ylabel="Value (start = 100)")
        axes.legend(frameon=False)

    return drawChart(draw)


# chart 2: the fall from the last peak over time, for the strategy and buy and hold
def drawdownChart(result: BacktestResult) -> str:
    def draw(axes: Axes) -> None:
        days = dayArray(result)
        axes.plot(days, fallsInPercent(result.strategyRun.equity()), color=BLUE, label="Strategy")
        holdFalls = fallsInPercent(result.holdRun.equity())
        axes.plot(days, holdFalls, color=ORANGE, label="Buy and hold")
        axes.set(title="Drawdown", xlabel="Date", ylabel="Fall from peak (%)")
        axes.legend(frameon=False)

    return drawChart(draw)


# chart 3: the closing price with a marker for every buy and every sell
def priceChart(result: BacktestResult) -> str:
    def draw(axes: Axes) -> None:
        frame = result.prices.frame.iloc[result.window.first : result.window.last + 1]
        closes = [float(price) for price in frame["close"].values]
        axes.plot(dayArray(result), closes, color=INK, linewidth=1.0, label="Close")
        fills = result.strategyRun.engine.fills
        for side, marker, colour in (("buy", "^", BLUE), ("sell", "v", ORANGE)):
            chosen = [fill for fill in fills if fill.side == side]
            days = np.array([fill.day for fill in chosen], dtype="datetime64[D]")
            prices = [fill.openPrice for fill in chosen]
            axes.scatter(
                days, prices, marker=marker, color=colour, s=40, zorder=3, label=side.title()
            )
        axes.set(title="Price with trades", xlabel="Date", ylabel="Price")
        axes.legend(frameon=False)

    return drawChart(draw)


# chart 4: the bands of the reshuffled equity, with the real strategy on top
def fanChart(result: BacktestResult) -> str:
    def draw(axes: Axes) -> None:
        fan = result.monteCarlo.fan if result.monteCarlo is not None else None
        if fan is not None:
            days = list(fan.days)
            outline = days + days[::-1]
            axes.fill(
                outline,
                list(fan.low) + list(fan.high)[::-1],
                color=BLUE,
                alpha=0.15,
                label="5% to 95%",
            )
            inner = list(fan.innerLow) + list(fan.innerHigh)[::-1]
            axes.fill(outline, inner, color=BLUE, alpha=0.3, label="25% to 75%")
            axes.plot(days, list(fan.median), color=BLUE, linestyle="--", label="Median")
        actual = growthOf100(result.strategyRun.equity())
        axes.plot(list(range(len(actual))), actual, color=INK, label="Actual")
        axes.set(
            title="Reshuffled growth of 100",
            xlabel="Trading days from the start",
            ylabel="Value (start = 100)",
        )
        axes.legend(frameon=False)

    return drawChart(draw)


# chart 5: how often each total return came up in the reshuffles, with the real one and zero marked
def histogramChart(result: BacktestResult) -> str:
    def draw(axes: Axes) -> None:
        if result.monteCarlo is not None:
            values = [value * 100 for value in result.monteCarlo.strategyReturns]
            axes.hist(values, bins=40, color=BLUE, alpha=0.6)
        actual = result.strategyRun.metrics.totalReturn * 100
        axes.axvline(actual, color=INK, linewidth=1.5, label="Actual")
        axes.axvline(0, color=ORANGE, linestyle="--", linewidth=1.2, label="Zero")
        axes.set(
            title="Reshuffled total returns",
            xlabel="Total return (%)",
            ylabel="Number of simulations",
        )
        axes.legend(frameon=False)

    return drawChart(draw)


# all five charts, in the order of the report
def allCharts(result: BacktestResult) -> dict[str, str]:
    return {
        "growth": growthChart(result),
        "drawdown": drawdownChart(result),
        "price": priceChart(result),
        "fan": fanChart(result),
        "histogram": histogramChart(result),
    }
