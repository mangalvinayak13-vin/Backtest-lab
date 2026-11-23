from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

import jinja2

from backtestlab.backtest import BacktestResult
from backtestlab.charts import allCharts
from backtestlab.formatting import formatDate, formatMoney, formatPercent
from backtestlab.metrics import Metrics
from backtestlab.strategy import strategyLabel
from backtestlab.summary import summarySentences

MAXTRADES = 500
MISSING = "not available"
EXPLANATIONS = {
    "Final value": "What the starting cash grew or shrank to. Higher is better.",
    "Total return": "The change from the start to the end. Higher is better.",
    "Annualised return": "The steady yearly growth that gives the same result. Higher is better.",
    "Annualised volatility": "How much the value jumped around, scaled to a year. Lower is calmer.",
    "Sharpe ratio": "Return for each unit of ups and downs. Higher is better.",
    "Maximum drawdown": "The biggest fall from a peak to a later low. Closer to 0 is better.",
    "Time in the market": "The share of days on which shares were held at the close.",
    "Completed trades": "Round trips from the first buy until every share was sold.",
    "Win rate": "The share of completed trades that made a profit. Few trades make it unreliable.",
    "Costs paid": "Brokerage, taxes and fees taken from the cash. Lower is better.",
    "Slippage cost": "What was lost by filling orders a little worse than the open price.",
}


# money in the run's currency and grouping
def money(result: BacktestResult, amount: float, decimals: int = 0) -> str:
    return formatMoney(amount, result.settings.currencySymbol, result.settings.grouping, decimals)


# a percentage, or "not available"
def percent(value: float | None) -> str:
    return MISSING if value is None else formatPercent(value)


# a plain number with two decimals, or "not available"
def decimal(value: float | None) -> str:
    return MISSING if value is None else f"{value:.2f}"


# a rate such as 0.00317% with as many digits as it needs
def rate(value: float) -> str:
    return f"{value * 100:.5g}%"


# the drawdown with the dates of the peak and the low
def drawdownText(metrics: Metrics) -> str:
    text = formatPercent(metrics.maxDrawdown)
    if metrics.drawdownPeak is None or metrics.drawdownTrough is None:
        return text
    return f"{text} ({formatDate(metrics.drawdownPeak)} to {formatDate(metrics.drawdownTrough)})"


# every metric of one series as display text, with "-" for the ones that don't apply
def metricTexts(result: BacktestResult, metrics: Metrics) -> dict[str, str]:
    trades = metrics.completedTrades
    return {
        "Final value": money(result, metrics.finalValue),
        "Total return": formatPercent(metrics.totalReturn),
        "Annualised return": percent(metrics.annualisedReturn),
        "Annualised volatility": percent(metrics.annualisedVolatility),
        "Sharpe ratio": decimal(metrics.sharpeRatio),
        "Maximum drawdown": drawdownText(metrics),
        "Time in the market": "-"
        if metrics.timeInMarket is None
        else percent(metrics.timeInMarket),
        "Completed trades": "-" if trades is None else str(trades),
        "Win rate": "-" if trades is None else percent(metrics.winRate),
        "Costs paid": "-" if metrics.costsPaid is None else money(result, metrics.costsPaid),
        "Slippage cost": "-"
        if metrics.slippageCost is None
        else money(result, metrics.slippageCost),
    }


# one row per metric, for the strategy, buy and hold and the index
def metricRows(result: BacktestResult) -> list[dict[str, str]]:
    mine = metricTexts(result, result.strategyRun.metrics)
    held = metricTexts(result, result.holdRun.metrics)
    index = metricTexts(result, result.benchmark.metrics) if result.benchmark else {}
    return [
        {
            "name": name,
            "strategy": mine[name],
            "hold": held[name],
            "benchmark": index.get(name, ""),
            "explanation": explanation,
        }
        for name, explanation in EXPLANATIONS.items()
    ]


# the four key numbers for one series, for the cards at the top
def keyCards(result: BacktestResult, metrics: Metrics) -> list[tuple[str, str]]:
    return [
        ("Final value", money(result, metrics.finalValue)),
        ("Total return", formatPercent(metrics.totalReturn)),
        ("Maximum drawdown", formatPercent(metrics.maxDrawdown)),
        ("Sharpe ratio", decimal(metrics.sharpeRatio)),
    ]


# the completed and open round trips as display rows, at most 500 of them
def tradeRows(result: BacktestResult) -> list[dict[str, str]]:
    rows = []
    for trip in result.strategyRun.trips[:MAXTRADES]:
        rows.append(
            {
                "entry": formatDate(trip.entryDay),
                "exit": "still open" if trip.isOpen else formatDate(trip.exitDay),
                "days": str(trip.daysHeld),
                "paid": money(result, trip.paid),
                "received": money(result, trip.received),
                "profit": money(result, trip.profit),
                "returnRate": formatPercent(trip.returnRate),
            }
        )
    return rows


# where the money went: each kind of charge added up over all the strategy's trades
def costRows(result: BacktestResult) -> list[tuple[str, str]]:
    fills = result.strategyRun.engine.fills
    parts = {
        "Brokerage": sum(fill.costs.brokerage for fill in fills),
        "Exchange and regulator fees": sum(fill.costs.exchange for fill in fills),
        "Tax on fees (GST)": sum(fill.costs.taxOnFees for fill in fills),
        "Taxes on buys and sells": sum(fill.costs.sideTax for fill in fills),
        "Fixed fees per sell": sum(fill.costs.fixed for fill in fills),
        "Slippage": result.strategyRun.metrics.slippageCost or 0.0,
    }
    return [(name, money(result, amount, 2)) for name, amount in parts.items()]


# the charges in the settings as display rows
def chargeRows(result: BacktestResult) -> list[tuple[str, str]]:
    costs = result.settings.costs
    cap = (
        "no cap"
        if costs.brokerageCap is None
        else f"capped at {money(result, costs.brokerageCap, 2)}"
    )
    return [
        ("Brokerage", f"{rate(costs.brokerageRate)} per order, {cap}"),
        ("Taxes on buys", rate(costs.buyTaxRate)),
        ("Taxes on sells", rate(costs.sellTaxRate)),
        ("Exchange and regulator fees", rate(costs.exchangeFeeRate)),
        ("Tax on fees", rate(costs.taxOnFeesRate)),
        ("Fixed fee per sell", money(result, costs.sellFeePerOrder, 2)),
        ("Slippage", rate(result.settings.slippageRate)),
    ]


# the price adjustment, taken from the notes made while loading
def adjustmentText(result: BacktestResult) -> str:
    adjusted = [note for note in result.prices.notes if "adjusted" in note]
    return adjusted[0] if adjusted else "No adjustment was recorded."


# every setting and fact about the data as display rows
def settingRows(result: BacktestResult, command: str | None) -> list[tuple[str, str]]:
    settings = result.settings
    frame = result.prices.frame
    allDays = [stamp.date() for stamp in frame.index]
    rows = [
        ("Preset", settings.presetName),
        ("Starting cash", money(result, settings.startingCash)),
        ("Shares", "whole shares only" if settings.wholeShares else "fractional shares allowed"),
        ("Trading days per year", str(settings.tradingDaysPerYear)),
        ("Risk-free rate", rate(settings.riskFreeRate)),
        ("Benchmark", result.benchmark.label if result.benchmark else "none"),
        ("Simulations", f"{settings.simulations:,}"),
        ("Block length", f"{settings.blockLength} trading days"),
        ("Seed", str(settings.seed)),
        ("Data source", result.prices.source),
        (
            "Data range",
            f"{formatDate(allDays[0])} to {formatDate(allDays[-1])}, {len(allDays):,} bars",
        ),
        ("Bars tested", f"{len(result.days):,}"),
        ("Price adjustment", adjustmentText(result)),
        ("Costs checked on", settings.costsCheckedOn or "not given"),
        ("backtestlab version", result.version),
    ]
    return rows + ([("Command", command)] if command else [])


# the Monte Carlo tables as display rows
def robustnessRows(result: BacktestResult) -> dict[str, Any]:
    check = result.monteCarlo
    if check is None:
        return {}
    spreads = [
        ("Total return, strategy", check.strategy.totalReturn),
        ("Total return, buy and hold", check.buyAndHold.totalReturn),
        ("Maximum drawdown, strategy", check.strategy.maxDrawdown),
        ("Maximum drawdown, buy and hold", check.buyAndHold.maxDrawdown),
    ]
    return {
        "percentiles": [
            (name, formatPercent(spread.p5), formatPercent(spread.p50), formatPercent(spread.p95))
            for name, spread in spreads
        ],
        "chances": [
            (
                "Chance the strategy ends with a loss",
                formatPercent(check.strategy.probabilityOfLoss, 0),
            ),
            (
                "Chance buy and hold ends with a loss",
                formatPercent(check.buyAndHold.probabilityOfLoss, 0),
            ),
            (
                "Chance the strategy beats buy and hold",
                formatPercent(check.probabilityBeatsHold, 0),
            ),
        ],
        "simulations": f"{check.simulations:,}",
        "blockLength": str(check.blockLength),
    }


# the cost sensitivity table as display rows, with buy and hold at normal costs at the end
def sensitivityRows(result: BacktestResult) -> list[tuple[str, str, str, str]]:
    names = {
        0.0: "Strategy, no costs",
        1.0: "Strategy, normal costs",
        2.0: "Strategy, double costs",
    }
    rows = [
        (
            names[row.multiplier],
            formatPercent(row.totalReturn),
            percent(row.annualisedReturn),
            decimal(row.sharpeRatio),
        )
        for row in result.sensitivity
    ]
    held = result.holdRun.metrics
    rows.append(
        (
            "Buy and hold, normal costs",
            formatPercent(held.totalReturn),
            percent(held.annualisedReturn),
            decimal(held.sharpeRatio),
        )
    )
    return rows


# everything the template shows, already turned into text
def reportContext(result: BacktestResult, command: str | None) -> dict[str, Any]:
    first, last = result.days[0], result.days[-1]
    return {
        "title": strategyLabel(result.strategy),
        "source": result.prices.source,
        "period": f"{formatDate(first)} to {formatDate(last)}",
        "created": datetime.now().strftime("%d %b %Y at %H:%M").lstrip("0"),
        "warnings": result.warnings,
        "summary": summarySentences(result),
        "strategyCards": keyCards(result, result.strategyRun.metrics),
        "holdCards": keyCards(result, result.holdRun.metrics),
        "charts": allCharts(result),
        "metricRows": metricRows(result),
        "benchmarkLabel": result.benchmark.label if result.benchmark else None,
        "robustness": robustnessRows(result),
        "sensitivity": sensitivityRows(result),
        "trades": tradeRows(result),
        "tradeCount": len(result.strategyRun.trips),
        "maxTrades": MAXTRADES,
        "costs": costRows(result),
        "charges": chargeRows(result),
        "costNotes": result.settings.costNotes,
        "settings": settingRows(result, command),
        "version": result.version,
    }


# the report page as text
def renderReport(result: BacktestResult, command: str | None = None) -> str:
    with (files("backtestlab") / "templates" / "report.html").open("r", encoding="utf-8") as file:
        template = jinja2.Template(file.read(), autoescape=True)
    return str(template.render(reportContext(result, command)))


# write the report to a file, making its folder first if needed
def writeReport(result: BacktestResult, path: str | Path, command: str | None = None) -> None:
    target = Path(path)
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    with target.open("w", encoding="utf-8") as file:
        file.write(renderReport(result, command))
