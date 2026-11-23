import json
import math
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from backtestlab.backtest import BacktestResult, RunSummary
from backtestlab.engine import Fill
from backtestlab.strategy import strategyLabel

SCHEMAVERSION = 1


# turn a value into something json can hold: dates as ISO text, tuples as lists
def plain(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [plain(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"a result value is {value}, which json can't hold")
    return value


# one fill with every charge spelled out
def fillData(fill: Fill) -> dict[str, Any]:
    data = asdict(fill)
    data["totalCosts"] = fill.costs.total
    return data


# the trades, fills and numbers of one run
def runData(run: RunSummary) -> dict[str, Any]:
    return {
        "metrics": asdict(run.metrics),
        "trades": [asdict(trip) for trip in run.trips],
        "fills": [fillData(fill) for fill in run.engine.fills],
        "skippedOrders": [asdict(order) for order in run.engine.skipped],
    }


# the Monte Carlo summary without the raw simulations
def monteCarloData(result: BacktestResult) -> dict[str, Any] | None:
    check = result.monteCarlo
    if check is None:
        return None
    return {
        "simulations": check.simulations,
        "blockLength": check.blockLength,
        "seed": check.seed,
        "strategy": asdict(check.strategy),
        "buyAndHold": asdict(check.buyAndHold),
        "probabilityBeatsHold": check.probabilityBeatsHold,
    }


# the price data and the window that was tested
def dataInformation(result: BacktestResult) -> dict[str, Any]:
    days = [stamp.date() for stamp in result.prices.frame.index]
    return {
        "source": result.prices.source,
        "firstDate": days[0],
        "lastDate": days[-1],
        "bars": len(days),
        "notes": result.prices.notes,
    }


# everything in the results file, as plain data
def resultsData(result: BacktestResult) -> dict[str, Any]:
    benchmark = result.benchmark
    data = {
        "schemaVersion": SCHEMAVERSION,
        "version": result.version,
        "createdAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "strategy": strategyLabel(result.strategy),
        "settings": asdict(result.settings),
        "data": dataInformation(result),
        "window": {
            "firstDate": result.days[0],
            "lastDate": result.days[-1],
            "bars": len(result.days),
        },
        "strategyRun": runData(result.strategyRun),
        "buyAndHoldRun": runData(result.holdRun),
        "benchmark": None
        if benchmark is None
        else {"label": benchmark.label, "metrics": asdict(benchmark.metrics)},
        "monteCarlo": monteCarloData(result),
        "costSensitivity": [asdict(row) for row in result.sensitivity],
        "equity": {
            "dates": result.days,
            "strategy": result.strategyRun.equity(),
            "buyAndHold": result.holdRun.equity(),
            "benchmark": None if benchmark is None else benchmark.values,
        },
        "warnings": [asdict(warning) for warning in result.warnings],
    }
    plainData: dict[str, Any] = plain(data)
    return plainData


# write the results file as indented json
def writeResultsFile(result: BacktestResult, path: str | Path) -> None:
    target = Path(path)
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    with target.open("w", encoding="utf-8") as file:
        file.write(json.dumps(resultsData(result), indent=2) + "\n")
