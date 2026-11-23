import pytest

from backtestlab import api


# every error the library raises can be caught with the one base class
@pytest.mark.parametrize("error", [api.DataError, api.StrategyError, api.SettingsError])
def testEveryErrorIsABacktestLabError(error: type[Exception]) -> None:
    assert issubclass(error, api.BacktestLabError)


# the version comes from the installed package
def testVersionIsAvailable() -> None:
    assert api.VERSION.count(".") >= 1
