import pytest

from backtestlab.arguments import parseOptions
from backtestlab.errors import SettingsError


# values, repeated parameters and flags are all read
def testReadsEveryKindOfOption() -> None:
    options = parseOptions(
        ["--csv", "a.csv", "--param", "x=1", "--param=y=2", "--fractional-shares", "--seed=7"]
    )
    assert options.get("--csv") == "a.csv"
    assert options.get("--seed") == "7"
    assert options.get("--ticker") is None
    assert options.repeated["--param"] == ["x=1", "y=2"]
    assert "--fractional-shares" in options.flags


# an unknown option lists the valid ones
def testUnknownOption() -> None:
    with pytest.raises(
        SettingsError, match=r"unknown option '--tickr'. Valid options: --ticker, --csv"
    ):
        parseOptions(["--tickr", "TCS.NS"])


# a word that isn't an option is an error too
def testStrayWord() -> None:
    with pytest.raises(SettingsError, match=r"unknown option 'TCS\.NS'"):
        parseOptions(["TCS.NS"])


# an option without its value is an error, also when the next word is another option
def testMissingValue() -> None:
    with pytest.raises(SettingsError, match="the option --csv needs a value"):
        parseOptions(["--csv"])
    with pytest.raises(SettingsError, match="the option --csv needs a value"):
        parseOptions(["--csv", "--strategy", "ma-crossover"])


# an option given twice is an error
def testRepeatedOption() -> None:
    with pytest.raises(SettingsError, match="--seed was given more than once"):
        parseOptions(["--seed", "1", "--seed", "2"])


# a flag can't be given a value
def testFlagWithValue() -> None:
    with pytest.raises(SettingsError, match="unknown option '--fractional-shares=yes'"):
        parseOptions(["--fractional-shares=yes"])
