# Progress

My log of every change and why, newest first.

## 23 Nov 2026: project skeleton

What I did: set up the empty project so that later parts have somewhere to go. The `backtestlab` command now exists and answers `--version` and `--help`. A wrong option gives a one-line error and exit code 1. I also wrote the check script, the CI workflow, the licence and a short README.

Why: I want the checks (ruff, mypy, pytest and coverage) and the no-underscore test running from day one, so every later change is checked the same way.

Files:
- `pyproject.toml`: dependencies, the build backend and the ruff settings.
- `src/backtestlab/errors.py`: the error classes.
- `src/backtestlab/api.py`: the public names and `VERSION`.
- `src/backtestlab/cli.py`: the command line.
- `scripts/check.py`: runs every check with one command.
- `tests/conftest.py`: the `workdir` fixture, a temporary folder for one test.
- `tests/testrules.py`: fails on underscores, docstrings and comments that silence a tool.
- `.github/workflows/ci.yml`: runs the check script on every push.

Try it:
- `source .venv/bin/activate`
- `backtestlab --version`
- `python scripts/check.py`
- To stop Python from making its `pycache` folders when I run things myself, I add this line to my shell settings and open a new terminal: `echo 'export PYTHONDONTWRITEBYTECODE=1' >> ~/.zshrc`

Checks: 15 tests pass, coverage is 100%, ruff and mypy are clean.

Still open:
- The CI workflow has not run yet because nothing is on GitHub.
- The CI check has no smoke test of the command on the sample data yet. That comes with the sample data.
- The licence uses my git user name. I may change it to my full name.
- The `--help` text only lists what exists now. I will write the full text when the `run` command is built.

## Ideas for later

Nothing yet.
