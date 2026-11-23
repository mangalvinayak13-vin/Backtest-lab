from pathlib import Path

import pytest

from backtestlab import api


# the data loaders can be used from the public api
def testLoadersAreInTheApi(pytestconfig: pytest.Config) -> None:
    data = api.loadCsv(Path(pytestconfig.rootpath) / "data" / "sampleprices.csv")
    assert len(data.frame) == 1305
    assert callable(api.downloadPrices)
