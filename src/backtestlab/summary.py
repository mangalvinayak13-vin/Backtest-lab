from backtestlab.backtest import BacktestResult
from backtestlab.formatting import formatDate, formatMoney, formatPercent
from backtestlab.strategy import isShortForm, strategyLabel

YAHOO = " (Yahoo Finance)"


# money in the run's currency and grouping
def moneyText(result: BacktestResult, amount: float) -> str:
    return formatMoney(amount, result.settings.currencySymbol, result.settings.grouping)


# the name of the asset for a sentence: the ticker, or "the asset" for a file
def assetName(source: str) -> str:
    return source.removesuffix(YAHOO) if source.endswith(YAHOO) else "the asset"


# the first sentence: the period, and what the strategy turned the cash into
def openingSentence(result: BacktestResult) -> str:
    metrics = result.strategyRun.metrics
    first, last = result.days[0], result.days[-1]
    years = (last - first).days / 365.25
    change = "a gain" if metrics.totalReturn >= 0 else "a loss"
    label = strategyLabel(result.strategy)
    startsShort = isShortForm(label.split()[0])
    name = label if startsShort else label[0].lower() + label[1:]
    size = formatPercent(abs(metrics.totalReturn))
    return (
        f"Over {years:.1f} years ({formatDate(first)} to {formatDate(last)}), the {name} turned "
        f"{moneyText(result, metrics.startingValue)} into {moneyText(result, metrics.finalValue)}, "
        f"{change} of {size}."
    )


# the second sentence: what simply holding would have done
def holdingSentence(result: BacktestResult) -> str:
    held = result.holdRun.metrics.totalReturn
    verb = "made" if held >= 0 else "lost"
    asset = assetName(result.prices.source)
    return f"Simply holding {asset} would have {verb} {formatPercent(abs(held))}."


# the third sentence: the worst fall of each
def fallSentence(result: BacktestResult) -> str:
    mine = formatPercent(abs(result.strategyRun.metrics.maxDrawdown))
    theirs = formatPercent(abs(result.holdRun.metrics.maxDrawdown))
    return f"The strategy's worst fall from a peak was {mine}, against {theirs} for holding."


# the fourth sentence: trades and costs
def tradeSentence(result: BacktestResult) -> str:
    metrics = result.strategyRun.metrics
    count = metrics.completedTrades or 0
    noun = "trade" if count == 1 else "trades"
    paid = moneyText(result, metrics.costsPaid or 0.0)
    return f"It completed {count} {noun} and paid {paid} in costs and taxes."


# the fifth sentence: what the reshuffles said, when they ran
def reshuffleSentence(result: BacktestResult) -> list[str]:
    check = result.monteCarlo
    if check is None:
        return []
    loss = formatPercent(check.strategy.probabilityOfLoss, 0)
    beat = formatPercent(check.probabilityBeatsHold, 0)
    return [
        f"In {check.simulations:,} reshuffled versions of its daily returns it ended with a loss "
        f"{loss} of the time and beat holding {beat} of the time."
    ]


# three to five plain sentences that sum up the run
def summarySentences(result: BacktestResult) -> list[str]:
    sentences = [openingSentence(result), holdingSentence(result), fallSentence(result)]
    return [*sentences, tradeSentence(result), *reshuffleSentence(result)]
