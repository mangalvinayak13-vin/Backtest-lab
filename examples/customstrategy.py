import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from backtestlab.api import SettingsError, Strategy, loadCsv, presets, runBacktest, writeReport


# invested while the close is above its own moving average, otherwise in cash
@dataclass(frozen=True)
class AboveAverage(Strategy):
    description: ClassVar[str] = "Invested while the close is above its moving average."
    window: int = 100

    # the average needs this many closes before the first decision
    @property
    def warmupBars(self) -> int:
        return self.window

    # an average of fewer than 2 closes makes no sense
    def check(self) -> None:
        if self.window < 2:
            raise SettingsError(f"window must be at least 2, but it is {self.window}.")

    # fully invested when today's close is above the average, otherwise all cash
    def decide(self, history: pd.DataFrame) -> float:
        closes = history["close"]
        return 1.0 if closes.iloc[-1] > closes.tail(self.window).mean() else 0.0


# run the custom strategy on the sample prices and write the report into a folder
def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("customstrategy")
    sample = Path(sys.argv[0]).resolve().parent.parent / "data" / "sampleprices.csv"
    result = runBacktest(loadCsv(sample), AboveAverage(window=100), presets.DEFAULT)
    writeReport(result, folder / "report.html")
    metrics = result.strategyRun.metrics
    print(f"{metrics.completedTrades} trades, total return {metrics.totalReturn:.1%}")
    print(f"Report saved to {folder / 'report.html'}")


main()
