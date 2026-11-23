import sys

from backtestlab.api import VERSION
from backtestlab.errors import BacktestLabError, SettingsError

HELPLINES = (
    "backtestlab: an honest backtester for daily prices",
    "",
    "Usage:",
    "  backtestlab --version",
    "  backtestlab --help",
    "",
    "The run and strategies commands are not built yet.",
)


# print the help text
def showHelp() -> int:
    print("\n".join(HELPLINES))
    return 0


# print the version number
def showVersion() -> int:
    print(f"backtestlab {VERSION}")
    return 0


# pick the command from the arguments and run it
def runCommand(arguments: list[str]) -> int:
    if not arguments or arguments[0] == "--help":
        return showHelp()
    if arguments[0] == "--version":
        return showVersion()
    raise SettingsError(f"unknown command or option '{arguments[0]}'. Try backtestlab --help")


# the entry point of the command, returns the exit code
def main(arguments: list[str] | None = None) -> int:
    if arguments is None:
        arguments = sys.argv[1:]
    try:
        return runCommand(arguments)
    except BacktestLabError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
