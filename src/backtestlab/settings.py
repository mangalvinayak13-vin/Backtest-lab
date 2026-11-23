import math
from dataclasses import dataclass

from backtestlab.errors import SettingsError


# the charges on an order, with every rate written as a fraction (0.001 is 0.1%)
@dataclass(frozen=True)
class CostModel:
    brokerageRate: float = 0.001
    brokerageCap: float | None = None
    buyTaxRate: float = 0.0
    sellTaxRate: float = 0.0
    exchangeFeeRate: float = 0.0
    taxOnFeesRate: float = 0.0
    sellFeePerOrder: float = 0.0

    # complain if a rate is not from 0 up to 1, or an amount is below 0
    def check(self) -> None:
        rates = {
            "brokerageRate": self.brokerageRate,
            "buyTaxRate": self.buyTaxRate,
            "sellTaxRate": self.sellTaxRate,
            "exchangeFeeRate": self.exchangeFeeRate,
            "taxOnFeesRate": self.taxOnFeesRate,
        }
        for name, rate in rates.items():
            checkRate(name, rate)
        amounts = {"brokerageCap": self.brokerageCap, "sellFeePerOrder": self.sellFeePerOrder}
        for name, amount in amounts.items():
            if amount is not None and not (math.isfinite(amount) and amount >= 0):
                raise SettingsError(f"{name} must be 0 or more, but it is {amount}.")


# everything a run needs to know, apart from the prices and the strategy
@dataclass(frozen=True)
class Settings:
    presetName: str = "default"
    currencySymbol: str = ""
    grouping: str = "western"
    startingCash: float = 100000.0
    costs: CostModel = CostModel()
    slippageRate: float = 0.0005
    wholeShares: bool = True
    tradingDaysPerYear: int = 252
    riskFreeRate: float = 0.0
    benchmarkTicker: str | None = None
    benchmarkLabel: str | None = None
    costNotes: tuple[str, ...] = ()
    costsCheckedOn: str | None = None
    simulations: int = 1000
    blockLength: int = 20
    seed: int = 42

    # complain if any setting is out of range, before anything runs
    def check(self) -> None:
        if not (math.isfinite(self.startingCash) and self.startingCash > 0):
            raise SettingsError(f"Starting cash must be above 0, but it is {self.startingCash}.")
        checkRate("slippageRate", self.slippageRate)
        self.costs.check()
        if self.grouping not in ("indian", "western"):
            raise SettingsError(f"grouping must be indian or western, but it is {self.grouping}.")
        if self.tradingDaysPerYear < 1:
            raise SettingsError("tradingDaysPerYear must be at least 1.")
        if not -1 < self.riskFreeRate < 1:
            raise SettingsError(
                f"riskFreeRate must be between -1 and 1, but it is {self.riskFreeRate}."
            )
        if not 100 <= self.simulations <= 5000:
            raise SettingsError(
                f"simulations must be from 100 to 5000, but it is {self.simulations}."
            )
        if self.blockLength < 1:
            raise SettingsError(f"blockLength must be at least 1, but it is {self.blockLength}.")


# a rate must be at least 0 and below 1
def checkRate(name: str, rate: float) -> None:
    if not 0 <= rate < 1:
        raise SettingsError(f"{name} must be from 0 up to (not including) 1, but it is {rate}.")
