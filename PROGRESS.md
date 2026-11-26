# Progress

My log of every change and why, newest first.

## 27 Nov 2026: four bugs and some smaller fixes

What I did: fixed four bugs that I reproduced, and tidied five smaller things.

What was wrong:
- `--output res.json` gave the report and the results file the same name, so the JSON was written over the HTML and the run still said it had saved both. A name ending in `.json` (in any case) is now refused before anything is loaded.
- When `--output` or `--save-data` was a folder, I got a Python traceback. The command now prints one "Error: could not write ..." line with the name of the file.
- On a CSV with an unadjusted 50% drop, the "Price adjustment" row showed the jump warning, because I picked any note with the word "adjusted" in it. It now matches only the two notes the loaders write, which both live in `prices.py`.
- `--start 2020-06-06` (a Saturday) on the sample data warned that "the data starts later", although it begins in 2019. The warning now appears only when the warm-up moves the start, or the start is before the first date in the data.

How the tests missed them: no test used a `.json` or folder output, a loaded CSV with a jump in the report, or a start on a missing day inside the data. There are tests for each of these now.

The smaller things:
- A test of `--save-data` loaded the saved file twice and compared the two, so wrong saved prices would have passed. It now compares with the prices the fake Yahoo made, and I checked that it fails if the prices are saved with only two decimals.
- A class called `MyRSIRule` showed as "My r s i rule". It is "My RSI rule" now, and the summary sentence keeps the capitals when the name starts with a short form.
- The README named Zerodha, Groww and Angel One as the sources for the charges, but the note in `presets.py` left out Angel One. I added it there and to the same line in the crossover `RESULTS.md`.
- I deleted `experiments/requirements.txt`. Its only line asked for python-pptx, which no committed code imports.
- The README now says to clone the repository before trying the commands that use `data/sampleprices.csv`.

Files: `cli.py`, `prices.py`, `csvsource.py`, `yahoosource.py`, `report.py`, `window.py`, `strategy.py`, `summary.py`, `presets.py`, five test files, `README.md`, `HOW-IT-WORKS.md`, `experiments/crossover/RESULTS.md` and `experiments/requirements.txt` (deleted).

Try it: `backtestlab run --csv data/sampleprices.csv --strategy buy-and-hold --start 2020-06-06`

Checks: 336 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean.

Still open: nothing for this part.

## 26 Nov 2026: tidying how the files talk about my post drafts

What I did: renamed the local drafts folder to `experiments/crossover/drafts/`, and reworded one comment in `figures.py` and two lines in the entry below.

Why: so no file or folder here names the site where I plan to post.

Files: `.gitignore`, `PROGRESS.md` and `experiments/crossover/figures.py`.

Try it: `python scripts/check.py`

Checks: 325 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean.

Still open: nothing for this part.

## 26 Nov 2026: the full crossover results

What I did: added `experiments/crossover/`, which reruns the moving average crossover tests I shared after my launch post and writes `results.csv`, nine charts and `RESULTS.md`. It covers the 12 tests I promised (50/100, 50/150, 50/175 and 50/200 on TCS, Reliance and HDFC Bank, 2018 to 2024) and some extra checks: zero costs, seeds 1 to 5, 6% interest on idle cash, 69 window pairs, 2008 to 2017, the NIFTY 50 index and YES Bank. I also added the report screenshot `docs/report.png` and a short README section that links to the results.

Why: I promised a full breakdown, and every number in it has to be something anyone can rebuild. The experiment only uses backtestlab's own functions, so it also tests the library on real data.

Files:
- `experiments/crossover/crossover.py`: the script. `download` saves the prices once, `run` rebuilds everything from them in about two minutes.
- `plan.py` (which runs), `pricefiles.py` (saving and loading the prices), `measures.py` (time under water, the crash-year fall, interest on cash and time out of the market, which backtestlab doesn't report), `records.py` (one row of `results.csv`), `crosscheck.py` (three numbers worked out again by hand), `figures.py` (the charts), `page.py` and `template.md` (`RESULTS.md`).
- `scripts/check.py`: mypy now checks `experiments` too.
- `pyproject.toml`: `print` is allowed in `experiments`, and ruff allows the × sign.
- `.gitignore`: the saved prices, the per-run reports and my post drafts stay out of git.

Try it:
- `python experiments/crossover/crossover.py download`
- `python experiments/crossover/crossover.py run`

What I found: the 50/200 numbers are the same as in my real-data check below (TCS 162.6% against 253.7%, Reliance 39.7% against 199.1%, HDFC Bank 22.8% against 100.9%). Buy and hold won all 12 tests, and none of them wins even with zero costs. The NIFTYBEES prices on Yahoo have an unadjusted unit split in December 2019, so the experiment uses the NIFTY 50 index instead and says so. The `^NSEI` data also has no bar on 1 Jan 2018.

Checks: running the script three times gave the same `results.csv` byte for byte, and the nine hand-worked checks match the tool. 325 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean.

Still open: nothing in the library changed. Time under water and a crash-year fall would be useful in the report itself (see the ideas below).

## 25 Nov 2026: saying in the README how the project is tested

What I did: added a "How it's tested" section to the README. I also confirmed that the ci run for the last commit (`58c760b`) passed on all five jobs, including Windows, which closes the open point in the entry below.

Why: all the jobs are green now, so someone visiting the page should be able to see what the green badge covers.

Files: `README.md` and `PROGRESS.md`.

Try it: `python scripts/check.py`

Checks: 325 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean.

Still open: the README links to `docs/report.png`, which I haven't added yet, so the picture doesn't show. (Added on 26 Nov.)

## 24 Nov 2026: fixing the Windows ci failure

What I did: fixed two problems that only showed up on the Windows ci job. The other four jobs (Ubuntu on Python 3.12, 3.13 and 3.14, and macOS) already passed.

What was wrong and how I found it:
- The snapshot test failed because the data source was written as `data\sampleprices.csv` on Windows and `data/sampleprices.csv` everywhere else. `loadCsv` now writes the path with forward slashes, so the report and the results file look the same on every system.
- Two command line tests changed into their temporary folder, and Windows can't delete a folder that is the current folder, so the clean-up failed with a `PermissionError`. Those tests now stay in the repository folder and only write their files into the temporary one.

Files: `src/backtestlab/csvsource.py` and `tests/testcli.py`.

Tests that prevent it: the snapshot test already covers the path, and it only fails on Windows, so ci is what protects it. I can't run Windows here, so the next ci run is the real check.

Checks: 325 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean.

Still open: confirm the Windows job is green after the next push.

## 24 Nov 2026: examples, README, notes and a real-data check

What I did: wrote the two examples, the full README and a complete HOW-IT-WORKS.md, then checked everything against real prices and a fresh install.

Why: this is the last step before publishing. Every command in the README has to work as written, and the numbers have to make sense on real data, not only on the sample.

Files:
- `examples/quickstart.py` and `examples/customstrategy.py`, and `tests/testexamples.py`, which runs both.
- `README.md` and `HOW-IT-WORKS.md`.
- `.gitignore`, `pyproject.toml` and `tests/testrules.py` (see the bug fix below).

Try it:
- `python examples/quickstart.py`
- `python examples/customstrategy.py`

Real-data check (india preset, 1 Jan 2018 to 31 Dec 2024, 50/200 crossover):

| Ticker | Strategy | Buy and hold | Trades | Time with download |
|---|---|---|---|---|
| TCS.NS | 162.6% | 253.7% | 3 | 3.1 s |
| RELIANCE.NS | 39.7% | 199.1% | 6 | 2.7 s |
| HDFCBANK.NS | 22.8% | 100.9% | 5 | 2.6 s |

NIFTY 50 made 124.5% over the same days. Buy and hold is close to last close / first open - 1 (for TCS 256.7% against 253.7%). The gap is the ₹141 of charges on the buy, the slippage, and ₹897 of cash left over after buying whole shares, which earned nothing while the stock went up 3.6 times. RELIANCE's 1:1 bonus issue in October 2024 gave no jump warning, because Yahoo's prices are adjusted. A 10-year run of TCS (2,467 trading days) took 3.1 seconds including both downloads, well under the 10-second target.

Bug fix: `.gitignore` has the line `report.html` so that generated reports stay out of git, but that line also matched the report template, `src/backtestlab/templates/report.html`. The template would never have been committed, and `pip install` would have left it out, so every report would have failed with a missing file. I found it by installing into a fresh virtual environment and running the quick start. I added a `!src/backtestlab/templates/report.html` line to `.gitignore`, and a new test in `tests/testrules.py` fails if any file in the package is ignored by git. After the fix, a fresh `pip install .` runs both README quick starts exactly as written.

Checks: 325 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean. A search of every file git would include finds no em or en dashes and none of the words on my list of words to avoid.

Decisions:
- The examples print a one-line result, so `examples/*` is allowed to use `print`, like `scripts/*`. This is the one change from the ruff settings in my plan.
- Each example takes an optional output folder, so the test can write into a temporary one.
- The README links to `docs/report.png`, which I still need to take as a screenshot of a real report.

Still open:
- Take the screenshot `docs/report.png` (I'll use the TCS.NS report).
- Check that the GitHub username in the README badges and install line is right.
- Push to GitHub and check that CI is green on Linux, Windows and macOS.

## 24 Nov 2026: the command line and the public api

What I did: built `backtestlab run` and `backtestlab strategies`, with a small argument reader I wrote by hand, and filled in the public api in `api.py`. I also added the end-to-end snapshot test, the script that updates the snapshot, and a smoke test in CI that runs the command on the sample data.

Why: the command is how most people will use this. Every mistake someone can make on the command line (an unknown option, both `--ticker` and `--csv`, a bad parameter) now gives one clear line starting with "Error:" and exit code 1, never a traceback. The snapshot test makes sure the numbers don't change by accident.

Files:
- `src/backtestlab/arguments.py`: reads the options. It knows which options take a value, which are flags and which can repeat.
- `src/backtestlab/cli.py`: the commands. It builds the settings from the preset and the options, loads the data and the benchmark, runs the backtest and writes the files.
- `src/backtestlab/terminal.py`: what is printed after a run (the results table, warnings, summary and disclaimer).
- `src/backtestlab/csvsource.py`: now also has `saveCsv`, for `--save-data`.
- `src/backtestlab/api.py`: `loadCsv`, `downloadPrices`, `runBacktest`, `writeReport`, `writeResultsFile`, `Strategy`, `BuyAndHold`, `MovingAverageCrossover`, `Settings`, `CostModel`, `presets`, the errors and `VERSION`.
- `scripts/updatesnapshot.py` and `tests/snapshots/macrossover.json`.
- `tests/testcli.py`, `testarguments.py`, `testterminal.py` and `testsnapshot.py`.
- `.github/workflows/ci.yml`: the smoke test step.

Try it:
- `backtestlab strategies`
- `backtestlab run --csv data/sampleprices.csv --strategy ma-crossover --param shortWindow=20 --param longWindow=100`
- `backtestlab run --ticker TCS.NS --strategy ma-crossover --preset india --start 2018-01-01 --end 2024-12-31`

Checks: 322 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean. The whole suite takes about 25 seconds with coverage.

Decisions:
- An option can be written as `--seed 3` or `--seed=3`. A value that starts with `--` is treated as a missing value, so `--csv --strategy x` gives "the option --csv needs a value".
- `--cash` accepts commas, so `--cash 2,00,000` works.
- When `--benchmark` names a different index from the preset's, the label becomes that ticker.
- If the benchmark can't be downloaded, the run goes on and a `benchmark-missing` warning says why.
- The ten-year default before `--end` is 3,652 days, which avoids trouble with 29 February.
- The snapshot ignores `createdAt` and `version`, the two values that change between runs. The data source is a relative path, so the test and the script both run from the repository folder.

Still open: CI has still not run, because nothing is on GitHub yet.

## 24 Nov 2026: the report and the results file

What I did: wrote `runBacktest`, which ties every part together, and the two outputs: a self-contained HTML report and a JSON results file. The report has the warnings, a plain summary, key numbers, five SVG charts, the metrics table with an explanation of each number, the robustness checks, the trades, every setting and a disclaimer.

Why: the report is what people will actually look at, so it has to be honest and easy to read. It has no JavaScript and loads nothing from the internet, so it opens offline and can be emailed as one file. The JSON file holds the same results for anyone who wants to check them with their own code.

Files:
- `src/backtestlab/backtest.py`: `runBacktest` and `BacktestResult`. I wrote it in this step instead of the next one, because the report needs the full result.
- `src/backtestlab/summary.py`: the 3 to 5 summary sentences.
- `src/backtestlab/charts.py`: the five charts, drawn with matplotlib's Figure and saved as SVG text.
- `src/backtestlab/report.py` and `src/backtestlab/templates/report.html`: the page.
- `src/backtestlab/resultsfile.py`: the JSON file.
- `tests/conftest.py` now also has `sampleResult`, one backtest of the sample data shared by many tests.
- `tests/testbacktest.py`, `testsummary.py`, `testcharts.py`, `testreport.py` and `testresultsfile.py`, plus a new check in `testrules.py`.

Try it:
- `python -c "from backtestlab.api import loadCsv; from backtestlab.backtest import runBacktest; from backtestlab.report import writeReport; from backtestlab.strategies import MovingAverageCrossover; from backtestlab.presets import INDIA; writeReport(runBacktest(loadCsv('data/sampleprices.csv'), MovingAverageCrossover(), INDIA), 'report.html')"`
- `open report.html`

Checks: 290 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean. The whole run (backtest, Monte Carlo, cost check, charts and report) takes under a second on the sample data.

Decisions:
- matplotlib names the parts of an SVG with ids like `line2d` followed by a number and a joining character, which the no-underscore rule doesn't allow. Nothing refers to those group ids, so `cleanSvg` removes them, along with the file header, the metadata and comments. The clip and glyph ids stay. The rules test now writes a real report and results file and checks them too.
- The SVG metadata date is switched off and the hash salt is fixed, so the same result always draws the same charts.
- A strategy's name in the report comes from how Python prints it, so `MovingAverageCrossover(shortWindow=50, longWindow=200)` becomes "Moving average crossover (shortWindow=50, longWindow=200)". A strategy that isn't a dataclass is called "Custom strategy".
- On the sample data the crossover loses 31.6% and buy and hold loses 23.6%. The sample is made up, and I'm keeping it as it is: the report should show a strategy losing to holding just as clearly as one winning.

Still open: the screenshot for the README will be of a real run, taken at the end.

## 24 Nov 2026: robustness checks and warnings

What I did: wrote the Monte Carlo check, the cost sensitivity table and the warnings. I also wrote `formatting.py` now instead of later, because the warnings need to show money (₹24,150) and dates (3 Mar 2021) the same way the report will.

Why: one backtest is one path through history. The Monte Carlo check asks how much the result depends on the exact order of good and bad days. The cost table asks if the strategy still works when charges are higher than expected. The warnings say plainly when a result shouldn't be trusted, for example when there are only 7 trades.

Files:
- `src/backtestlab/montecarlo.py`: the paired block bootstrap, with the percentiles, the chance of a loss, the chance of beating buy and hold and the bands for the fan chart.
- `src/backtestlab/sensitivity.py`: the same run with costs times 0, 1 and 2.
- `src/backtestlab/diagnostics.py`: every warning, with the limits (3 years, 20 trades, 5% of cash) at the top of the file.
- `src/backtestlab/formatting.py`: money with Indian or western grouping, percentages and dates. Date writing moved here from `dates.py`.
- `tests/testmontecarlo.py`, `testsensitivity.py`, `testdiagnostics.py` and `testformatting.py`.

Try it: `python -m pytest -p no:cacheprovider tests/testmontecarlo.py -v`

Checks: 250 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean.

Decisions:
- The pairing test uses a strategy that earns 0.1% more than holding every day. With the same days drawn for both, it must win in every simulation, and it does (100%). Unpaired draws would not give that.
- Data notes from loading (for example the Adj Close adjustment) appear as warnings with the code `data-note`, last in the list.

Still open: nothing for this part.

## 23 Nov 2026: metrics and the market benchmark

What I did: wrote `metrics.py`, which works out the numbers for a run (total return, annualised return, volatility, Sharpe ratio, maximum drawdown with its dates, time in the market, completed trades, win rate, costs paid and slippage cost). I also wrote `benchmark.py`, which lines a market index up with the test dates and scales it to start at the starting cash.

Why: the report has to show the same numbers for the strategy, for buy and hold and for the index, worked out the same way. Where a number can't be worked out (a Sharpe ratio when every day has the same return, a win rate with no trades) it is `None` and the report will say "not available". It is never nan or infinity.

Files:
- `src/backtestlab/metrics.py`: `Metrics`, `curveMetrics` (needs only dates and equity, so it works for the index too) and `runMetrics` (adds the trading numbers).
- `src/backtestlab/benchmark.py`: `alignBenchmark`.
- `tests/testmetrics.py` and `tests/testbenchmark.py`.

Try it: `python -m pytest -p no:cacheprovider tests/testmetrics.py tests/testbenchmark.py`

Checks: 213 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean. Worked example 4 gives the exact numbers (volatility 183.30% and Sharpe 4.5826 for equity 100, 110, 99, 108.9; a drawdown of -25% for 100, 120, 90, 95, 130, 117; a win rate of 50%).

Decisions:
- A Sharpe ratio is "not available" when the spread of returns is below 1e-12, not only when it is exactly 0, because a steady 1% a day still leaves a tiny rounding error.
- An annualised return that would be too huge to show (a 1000x gain in one day) is `None` instead of infinity.
- If the index has no price on or before the first test date, it is left out with a `benchmark-missing` warning. A later price is never used for an earlier date.

Still open: nothing for this part.

## 23 Nov 2026: the engine, costs and settings

What I did: wrote the part that replays a strategy over old prices. It has the settings and presets (`default` and `india`), the cost rules, the choice of the test window, the day-by-day engine and the round trips built from the trades. I also moved the date parsing into `dates.py`, because the window and the Yahoo loader both need it.

Why: this is the core of the project, so it has the most tests. The rules that keep it honest are in the code and each one has a test: a decision at the close is carried out at the next open, the strategy only gets a copy of the past, charges come out of the cash, and cash and shares can't go below zero.

Files:
- `src/backtestlab/settings.py` and `presets.py`: `CostModel`, `Settings`, `DEFAULT` and `INDIA`.
- `src/backtestlab/costs.py`: the charges on an order and the biggest order the cash can pay for.
- `src/backtestlab/window.py`: which bars are tested, with the warm-up.
- `src/backtestlab/engine.py`: the loop, the fills and the skipped orders.
- `src/backtestlab/trades.py`: round trips.
- `src/backtestlab/runwarning.py` and `dates.py`: a warning with a code and message, and date helpers.
- `tests/helpers.py`: shared test code (the example bars, a scripted strategy, random prices).
- `tests/testengine.py`, `testcosts.py`, `testwindow.py`, `testtrades.py`, `testsettings.py` and `testproperties.py`.

Try it:
- `python -c "from backtestlab.api import loadCsv; from backtestlab.engine import runEngine; from backtestlab.strategies import BuyAndHold; from backtestlab.presets import DEFAULT; from backtestlab.window import chooseWindow; p = loadCsv('data/sampleprices.csv'); print(runEngine(p, BuyAndHold(), DEFAULT, chooseWindow(p, 0)).bars.tail())"`

Checks: 195 tests pass and 1 is skipped, coverage is 100%, ruff and mypy are clean. The tests include worked examples 1 to 3 (final equity 973 with whole shares, 970.588235 with fractional shares, and a profit of 33.192018 with costs), a look-ahead test that multiplies all later prices by 3, a check against a separate formula on the sample data, and Hypothesis tests on random prices.

Decisions:
- `target` in the bar table is the target in force during that bar, which was decided at the previous close.
- A buy that is cut to nothing is recorded as `unaffordable`, including the case where not even one share fits the cash.
- Tiny float errors could leave cash at -1e-13 after a buy, so cash after a buy is never allowed below 0.
- The mypy search path now includes `tests`, so tests can import `helpers.py`.

Still open: `Settings.check()` is not called by anything yet. `runBacktest` will call it.

## 23 Nov 2026: strategies

What I did: wrote the `Strategy` base class, the two built-in strategies (`BuyAndHold` and `MovingAverageCrossover`), a registry that maps command line names to them, and the code that turns `--param name=value` texts into real values. I also wrote `checkTarget`, which the engine will use to make sure every decision is a real number from 0 to 1.

Why: the engine only needs to know that a strategy has a `decide` method that takes the past and returns a number. Keeping the rule that small means a strategy is about 10 lines, and the engine can never be handed future prices, because `decide` only receives history up to today.

Files:
- `src/backtestlab/strategy.py`: the base class and `checkTarget`.
- `src/backtestlab/strategies.py`: the two strategies, the registry and the parameter reading.
- `tests/teststrategies.py`: hand-worked examples (closes 1 to 5 with windows 2 and 5 give averages 4.5 and 3), and every error message.

Try it: `python -c "from backtestlab.strategies import makeStrategy; print(makeStrategy('ma-crossover', ['shortWindow=20', 'longWindow=100']))"`

Checks: all tests pass, coverage is 100%, ruff and mypy are clean.

Still open: `backtestlab strategies` (which lists names, descriptions and parameters) comes with the command line.

## 23 Nov 2026: loading and checking price data

What I did: wrote the code that reads daily prices from a CSV file or from Yahoo Finance and checks them. Both sources turn into the same `PriceData` object, a table with one row per day, plus a note on where it came from and a list of notes about anything odd. Bad data stops with a clear error that names the dates. Odd but usable data (a day that jumps 40%, a gap of three weeks) only adds a warning. I also wrote a script that makes a synthetic sample file of about five years of prices, and I added `loadCsv` and `downloadPrices` to the public api.

Why: every later part (strategies, engine, metrics) trusts that the prices are clean. If a zero price or a swapped date gets through, every number after it is wrong and nothing says so. Checking in one place, with the same rules for both sources, keeps that simple. The sample file is made up, because Yahoo's terms don't allow me to put its data in the repository.

Files:
- `src/backtestlab/prices.py`: `PriceData`, the raw `Row`, and the rules that stop, drop or sort.
- `src/backtestlab/pricewarnings.py`: the warnings that don't stop anything.
- `src/backtestlab/csvsource.py`: `loadCsv`, with headers, dates and numbers read by hand.
- `src/backtestlab/yahoosource.py`: `downloadPrices`, the only file that imports yfinance.
- `scripts/makesampledata.py` and `data/sampleprices.csv`: the synthetic sample.
- `tests/testprices.py`, `testcsvsource.py`, `testyahoosource.py`, `testsampledata.py`, `testapi.py` and `testlive.py`.

Try it:
- `python -c "from backtestlab.api import loadCsv; print(loadCsv('data/sampleprices.csv').frame.tail())"`
- `python scripts/makesampledata.py` (writes the same file again)
- `BACKTESTLABLIVE=1 python -m pytest -p no:cacheprovider tests/testlive.py` downloads one real ticker.

Checks: 74 tests pass and 1 is skipped (the live one), coverage is 100%, ruff and mypy are clean. I also ran one real yfinance call for TCS.NS. It gave flat columns (Open, High, Low, Close, Volume), no separate adjusted close column, dates in the Asia/Kolkata time zone, and the end date was left out, as I expected.

Still open:
- The Yahoo tests use a fake Ticker. Only the live test touches the network.
- `raise ... from error` keeps the original error as the cause, but I can't test that without writing the double-underscore name, so it is not tested.
- A date like `01/02/2024` is rejected on purpose, because I can't tell if it is 1 February or 2 January.

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

- More built-in strategies, such as a simple momentum rule or a volatility filter.
- A `--quiet` option that prints only the results table.
- An option to earn a fixed interest rate on idle cash.
- Showing the cost sensitivity as a small chart as well as a table.
- Time under water (the longest stretch below an earlier high) next to maximum drawdown in the report and the summary.
- A sweep command that runs a grid of strategy settings and draws the heatmap, warning that a best cell may be luck.
- A total return index (with dividends) as the market benchmark, if a reliable free source exists.
