import os
import shutil
import sys
import tempfile
from pathlib import Path

from backtestlab.cli import main as runCli

SNAPSHOT = Path("tests") / "snapshots" / "macrossover.json"
ARGUMENTS = [
    "run",
    "--csv",
    "data/sampleprices.csv",
    "--strategy",
    "ma-crossover",
    "--benchmark",
    "none",
]


# the repository folder is one level above scripts
def findRoot() -> Path:
    return Path(sys.argv[0]).resolve().parent.parent


# run the snapshot command and keep its results file as the new snapshot
def main() -> int:
    root = findRoot()
    os.chdir(root)
    with tempfile.TemporaryDirectory() as folder:
        code = runCli([*ARGUMENTS, "--output", str(Path(folder) / "report.html")])
        if code != 0:
            return code
        shutil.copyfile(Path(folder) / "report.json", root / SNAPSHOT)
    print(f"Updated {SNAPSHOT}")
    return 0


sys.exit(main())
