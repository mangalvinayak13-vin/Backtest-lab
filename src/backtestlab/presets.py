from backtestlab.settings import CostModel, Settings

DEFAULT = Settings(
    presetName="default",
    costs=CostModel(brokerageRate=0.001),
)

INDIA = Settings(
    presetName="india",
    currencySymbol="₹",
    grouping="indian",
    startingCash=100000.0,
    costs=CostModel(
        brokerageRate=0.001,
        brokerageCap=20.0,
        buyTaxRate=0.00115,
        sellTaxRate=0.001,
        exchangeFeeRate=0.0000317,
        taxOnFeesRate=0.18,
        sellFeePerOrder=15.34,
    ),
    benchmarkTicker="^NSEI",
    benchmarkLabel="NIFTY 50 (price index, excludes dividends)",
    costNotes=(
        "Brokerage: 0.1% per order, capped at ₹20 (a typical discount broker; "
        "Zerodha charges ₹0 for delivery).",
        "STT: 0.1% on buys and on sells.",
        "Stamp duty: 0.015% on buys.",
        "Exchange and SEBI charges: NSE 0.00307% + SEBI 0.0001%, on both sides.",
        "GST: 18% on brokerage, exchange and SEBI charges.",
        "DP charge: ₹15.34 per sell, GST included.",
        "Checked on 23 Nov 2026 against zerodha.com/charges and groww.in/pricing. "
        "Check your own broker's charges.",
    ),
    costsCheckedOn="2026-11-23",
)
