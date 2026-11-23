from importlib.metadata import version

from backtestlab import presets as presets
from backtestlab.backtest import runBacktest as runBacktest
from backtestlab.csvsource import loadCsv as loadCsv
from backtestlab.errors import BacktestLabError as BacktestLabError
from backtestlab.errors import DataError as DataError
from backtestlab.errors import SettingsError as SettingsError
from backtestlab.errors import StrategyError as StrategyError
from backtestlab.report import writeReport as writeReport
from backtestlab.resultsfile import writeResultsFile as writeResultsFile
from backtestlab.settings import CostModel as CostModel
from backtestlab.settings import Settings as Settings
from backtestlab.strategies import BuyAndHold as BuyAndHold
from backtestlab.strategies import MovingAverageCrossover as MovingAverageCrossover
from backtestlab.strategy import Strategy as Strategy
from backtestlab.yahoosource import downloadPrices as downloadPrices

VERSION = version("backtestlab")
