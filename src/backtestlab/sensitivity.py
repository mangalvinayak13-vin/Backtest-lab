from dataclasses import dataclass, replace

from backtestlab.engine import runEngine
from backtestlab.metrics import curveMetrics
from backtestlab.prices import PriceData
from backtestlab.pricewarnings import indexDays
from backtestlab.settings import CostModel, Settings
from backtestlab.strategy import Strategy
from backtestlab.window import Window

MULTIPLIERS = (0.0, 1.0, 2.0)


# the results of one run with the costs multiplied
@dataclass(frozen=True)
class SensitivityRow:
    multiplier: float
    totalReturn: float
    annualisedReturn: float | None
    sharpeRatio: float | None


# the cost model with its charges multiplied, but not the tax on fees, which grows with the fees
def scaleCosts(model: CostModel, factor: float) -> CostModel:
    cap = None if model.brokerageCap is None else model.brokerageCap * factor
    return replace(
        model,
        brokerageRate=model.brokerageRate * factor,
        brokerageCap=cap,
        buyTaxRate=model.buyTaxRate * factor,
        sellTaxRate=model.sellTaxRate * factor,
        exchangeFeeRate=model.exchangeFeeRate * factor,
        sellFeePerOrder=model.sellFeePerOrder * factor,
    )


# the settings with every cost and the slippage multiplied
def scaleSettings(settings: Settings, factor: float) -> Settings:
    return replace(
        settings,
        costs=scaleCosts(settings.costs, factor),
        slippageRate=settings.slippageRate * factor,
    )


# run the strategy again with the costs times 0, 1 and 2
def runSensitivity(
    prices: PriceData, strategy: Strategy, settings: Settings, window: Window
) -> tuple[SensitivityRow, ...]:
    rows = []
    for factor in MULTIPLIERS:
        result = runEngine(prices, strategy, scaleSettings(settings, factor), window)
        equity = [float(value) for value in result.bars["equity"].values]
        metrics = curveMetrics(indexDays(result.bars), equity, settings)
        rows.append(
            SensitivityRow(
                factor, metrics.totalReturn, metrics.annualisedReturn, metrics.sharpeRatio
            )
        )
    return tuple(rows)
