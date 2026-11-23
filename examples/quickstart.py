import sys
from pathlib import Path

from backtestlab.api import MovingAverageCrossover, loadCsv, presets, runBacktest, writeReport


# run the crossover on the sample prices with the india preset and write the report
def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path()
    sample = Path(sys.argv[0]).resolve().parent.parent / "data" / "sampleprices.csv"
    strategy = MovingAverageCrossover(shortWindow=50, longWindow=200)
    prices = loadCsv(sample)
    result = runBacktest(prices, strategy, presets.INDIA)
    writeReport(result, folder / "report.html")
    metrics = result.strategyRun.metrics
    print(f"Total return {metrics.totalReturn:.1%}, report saved to {folder / 'report.html'}")


main()
