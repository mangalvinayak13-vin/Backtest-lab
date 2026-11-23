from importlib.metadata import version

from backtestlab.errors import BacktestLabError as BacktestLabError
from backtestlab.errors import DataError as DataError
from backtestlab.errors import SettingsError as SettingsError
from backtestlab.errors import StrategyError as StrategyError

VERSION = version("backtestlab")
