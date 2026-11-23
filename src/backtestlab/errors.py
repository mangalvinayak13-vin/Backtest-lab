# the base for every error the library raises on purpose
class BacktestLabError(Exception):
    pass


# the price data is missing, broken or unusable
class DataError(BacktestLabError):
    pass


# a strategy has bad parameters or returned a bad value
class StrategyError(BacktestLabError):
    pass


# a setting or a command line option is wrong
class SettingsError(BacktestLabError):
    pass
