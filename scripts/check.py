import os
import subprocess
import sys
from pathlib import Path

FOLDERS = ("src", "tests", "scripts", "examples")


# the repository folder is one level above scripts
def findRoot() -> Path:
    return Path(sys.argv[0]).resolve().parent.parent


# only give mypy folders that really hold python files
def pythonFolders(root: Path) -> list[str]:
    return [name for name in FOLDERS if any((root / name).rglob("*.py"))]


# the environment every tool runs in, with no bytecode folders and mypy finding src
def makeEnvironment(root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["MYPYPATH"] = str(root / "src")
    return environment


# pytest is given every test file by name, because the file names have no underscores
def testFiles(root: Path) -> list[str]:
    return sorted(str(Path("tests") / path.name) for path in (root / "tests").glob("test*.py"))


# the name and the command of each check
def buildSteps(root: Path) -> list[tuple[str, list[str]]]:
    python = sys.executable
    mypyFlags = ["--strict", "--explicit-package-bases", "--disable-error-code", "import-untyped"]
    pytestFlags = [
        "-p",
        "no:cacheprovider",
        "--rootdir",
        str(root),
        "--cov=src/backtestlab",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
    ]
    return [
        ("ruff check", [python, "-m", "ruff", "check", "--no-cache", "."]),
        ("ruff format", [python, "-m", "ruff", "format", "--check", "--no-cache", "."]),
        (
            "mypy",
            [python, "-m", "mypy", *mypyFlags, "--cache-dir", os.devnull, *pythonFolders(root)],
        ),
        ("pytest", [python, "-m", "pytest", *pytestFlags, *testFiles(root)]),
    ]


# run one check and say whether it passed
def runStep(name: str, command: list[str], root: Path) -> bool:
    print(f"\n=== {name} ===", flush=True)
    result = subprocess.run(command, cwd=root, env=makeEnvironment(root), check=False)
    return result.returncode == 0


# run every check, print a summary and return the exit code
def main() -> int:
    root = findRoot()
    results = [(name, runStep(name, command, root)) for name, command in buildSteps(root)]
    print("\n=== summary ===")
    for name, passed in results:
        print(f"{name}: {'passed' if passed else 'FAILED'}")
    failed = [name for name, passed in results if not passed]
    return 1 if failed else 0


sys.exit(main())
