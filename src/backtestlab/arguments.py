from dataclasses import dataclass

from backtestlab.errors import SettingsError

VALUEOPTIONS = (
    "--ticker",
    "--csv",
    "--strategy",
    "--start",
    "--end",
    "--preset",
    "--cash",
    "--benchmark",
    "--simulations",
    "--seed",
    "--output",
    "--save-data",
    "--date-format",
)
REPEATOPTIONS = ("--param",)
FLAGOPTIONS = ("--fractional-shares",)


# the options given to the run command
@dataclass(frozen=True)
class Options:
    values: dict[str, str]
    repeated: dict[str, list[str]]
    flags: frozenset[str]

    # the value of an option, or None when it was not given
    def get(self, name: str) -> str | None:
        return self.values.get(name)


# an error for an option that this command doesn't know
def unknownOption(text: str) -> SettingsError:
    valid = ", ".join(VALUEOPTIONS + REPEATOPTIONS + FLAGOPTIONS)
    return SettingsError(f"unknown option '{text}'. Valid options: {valid}.")


# split --name=value into its two parts, or give the name and None
def splitOption(text: str) -> tuple[str, str | None]:
    name, separator, value = text.partition("=")
    return (name, value) if separator else (text, None)


# the value after an option, which must be there and must not be another option
def nextValue(arguments: list[str], position: int, name: str) -> str:
    if position >= len(arguments) or arguments[position].startswith("--"):
        raise SettingsError(f"the option {name} needs a value.")
    return arguments[position]


# read the arguments after the command into options, a short loop over the list
def parseOptions(arguments: list[str]) -> Options:
    values: dict[str, str] = {}
    repeated: dict[str, list[str]] = {name: [] for name in REPEATOPTIONS}
    flags: set[str] = set()
    position = 0
    while position < len(arguments):
        name, value = splitOption(arguments[position])
        position += 1
        if name in FLAGOPTIONS and value is None:
            flags.add(name)
            continue
        if name not in VALUEOPTIONS + REPEATOPTIONS:
            raise unknownOption(arguments[position - 1])
        if value is None:
            value = nextValue(arguments, position, name)
            position += 1
        if name in REPEATOPTIONS:
            repeated[name].append(value)
        elif name in values:
            raise SettingsError(f"the option {name} was given more than once.")
        else:
            values[name] = value
    return Options(values, repeated, frozenset(flags))
