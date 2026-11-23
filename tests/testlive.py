import os

import pytest

from backtestlab.yahoosource import downloadPrices


# a real download of one ticker, only when BACKTESTLABLIVE is set to 1
@pytest.mark.skipif(os.environ.get("BACKTESTLABLIVE") != "1", reason="set BACKTESTLABLIVE=1 to run")
def testRealDownload() -> None:
    data = downloadPrices("TCS.NS", "2024-01-02", "2024-01-31")
    assert len(data.frame) > 10
    assert float(data.frame["close"].iloc[0]) > 0
