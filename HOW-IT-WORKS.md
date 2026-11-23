# How backtestlab works

This file explains the project the way I would explain it to a classmate. It only describes what the code does today, and I add to it as each part is built.

## What this project does

A backtest replays a trading rule on old prices to see what it would have earned. backtestlab will take daily prices and a rule, run the replay with real trading costs, compare it with simply holding the asset, and write a report. Only the first small piece exists so far: the command, the error classes and the checks.

## What exists so far

`errors.py` has one base error, `BacktestLabError`, and three kinds below it: `DataError` (bad prices), `StrategyError` (a bad rule) and `SettingsError` (a bad setting or option). The command catches the base error, so any of them shows up as a short "Error: ..." line with no traceback.

`api.py` is the front door of the library. It re-exports the names people are meant to use, and it holds `VERSION`, which is read from the installed package.

`cli.py` is the command. `main` takes a list of arguments and returns an exit code: 0 for success and 1 for a mistake. Because it takes the list directly, tests can call it without starting a new process.

`scripts/check.py` runs ruff (lint and format), mypy in strict mode, and pytest with coverage. It prints which ones passed and exits with 1 if any failed.

## Why there are no underscores anywhere

This project has a rule: the underscore character appears nowhere, not in code, file names, docs or the report. A test (`tests/testrules.py`) fails if it finds one. It also fails on docstrings and on comments that tell a tool to be quiet.

Living with the rule changes a few habits:
- Names use camelCase for variables and functions (`shortWindow`) and PascalCase for classes (`MovingAverageCrossover`).
- Python normally marks a package with a special `init` file whose name has double underscores. This project has none. A folder of modules still works as a package.
- The command is started by a console script entry in `pyproject.toml`, so there is no special main file either.
- Test files are named `testsomething.py`. pytest only finds those by itself if the names have an underscore, so `scripts/check.py` gives pytest every test file by name.
- Some standard library functions have underscores in their names, such as the shortcut that reads a whole text file in one call. I use other routes, for example `Path.open` followed by `.read()`.

## Python ideas used so far

Type hints: every function says what it takes and returns, and mypy checks them.

Exceptions with a shared base class: `except BacktestLabError` catches every error the library raises on purpose, and nothing else.
