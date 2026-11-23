import pytest

from backtestlab.api import VERSION
from backtestlab.cli import main


# the version flag prints the name and the installed version
def testVersionPrintsNameAndVersion(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"backtestlab {VERSION}"


# the help flag prints the usage lines
def testHelpPrintsUsage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "Usage:" in capsys.readouterr().out


# running with no arguments shows the help instead of failing
def testNoArgumentsShowsHelp(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "Usage:" in capsys.readouterr().out


# a wrong option gives a one-line error and exit code 1, with no traceback
def testUnknownOptionGivesErrorAndExitCodeOne(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--nonsense"]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("Error: unknown command or option '--nonsense'")
    assert "Traceback" not in captured.err


# with no argument list, main reads the real command line
def testMainReadsTheRealCommandLine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["backtestlab", "--version"])
    assert main() == 0
    assert capsys.readouterr().out.strip() == f"backtestlab {VERSION}"
