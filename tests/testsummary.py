from dataclasses import replace

from helpers import Scripted, exampleBars, plainSettings

from backtestlab.backtest import BacktestResult, runBacktest
from backtestlab.prices import PriceData
from backtestlab.strategies import BuyAndHold
from backtestlab.summary import assetName, summarySentences


# the four example bars give these exact sentences, without the reshuffle sentence
def testSentencesForTheExampleBars() -> None:
    result = runBacktest(exampleBars(), BuyAndHold(), plainSettings())
    assert summarySentences(result) == [
        "Over 0.0 years (1 Jan 2024 to 4 Jan 2024), the buy and hold turned 1,000 into 973, "
        "a loss of 2.7%.",
        "Simply holding the asset would have lost 2.7%.",
        "The strategy's worst fall from a peak was 4.4%, against 4.4% for holding.",
        "It completed 0 trades and paid 0 in costs and taxes.",
    ]


# a gain is called a gain, and holding that made money says made
def testGainWording() -> None:
    rising = replace(exampleBars(), source="TCS.NS (Yahoo Finance)")
    frame = rising.frame.copy()
    frame["close"] = [100.0, 104.0, 108.0, 112.0]
    frame["high"] = [101.0, 105.0, 109.0, 113.0]
    result = runBacktest(PriceData(frame, rising.source, ()), BuyAndHold(), plainSettings())
    sentences = summarySentences(result)
    assert "a gain of" in sentences[0]
    assert sentences[1].startswith("Simply holding TCS.NS would have made")


# the sample run has five sentences, including the reshuffle one, in rupees
def testSampleSentences(sampleResult: BacktestResult) -> None:
    sentences = summarySentences(sampleResult)
    assert len(sentences) == 5
    assert "turned ₹1,00,000 into" in sentences[0]
    assert sentences[4].startswith("In 1,000 reshuffled versions of its daily returns")


# one trade is singular
def testOneTrade() -> None:
    result = runBacktest(exampleBars(), Scripted((1.0, 0.0)), plainSettings())
    assert "It completed 1 trade and" in summarySentences(result)[3]


# the asset is the ticker for a download and "the asset" for a file
def testAssetName() -> None:
    assert assetName("RELIANCE.NS (Yahoo Finance)") == "RELIANCE.NS"
    assert assetName("data/sampleprices.csv") == "the asset"
