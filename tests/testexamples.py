import subprocess
import sys
from pathlib import Path

import pytest


# run one example script with a work folder as its output folder
def runExample(root: Path, name: str, folder: Path) -> str:
    script = root / "examples" / name
    command = [sys.executable, str(script), str(folder)]
    return subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True).stdout


# the quick start example runs on the sample data and writes a report
def testQuickstartRuns(pytestconfig: pytest.Config, workdir: Path) -> None:
    out = runExample(pytestconfig.rootpath, "quickstart.py", workdir)
    assert (workdir / "report.html").exists()
    assert "Total return" in out


# the custom strategy example runs on the sample data and writes a report
def testCustomStrategyRuns(pytestconfig: pytest.Config, workdir: Path) -> None:
    out = runExample(pytestconfig.rootpath, "customstrategy.py", workdir / "custom")
    assert (workdir / "custom" / "report.html").exists()
    assert "trades, total return" in out
