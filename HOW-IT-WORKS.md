# How backtestlab works

This is how I would explain the project to a classmate. Every finance or programming word is explained the first time it comes up, and there is a glossary at the end.

## 1. What this project does

A backtest replays a trading rule on old prices to see what it would have earned. backtestlab takes daily prices (from a CSV file or from Yahoo Finance) and a rule, which I call a strategy. It replays the strategy one day at a time with real trading costs, and compares the result with simply buying on the first day and holding. Then it checks how much the result depended on luck and writes an HTML report and a JSON results file.

## 2. What happens in one backtest

```
backtestlab run --csv prices.csv --strategy ma-crossover
        |
        v
  read the options (arguments.py, cli.py)
        |
        v
  load and check the prices (csvsource.py or yahoosource.py, then prices.py)
        |
        v
  choose the test window (window.py)
        |
        v
  replay the strategy and buy and hold, day by day (engine.py, trades.py)
        |
        v
  work out the numbers (metrics.py, benchmark.py)
        |
        v
  robustness checks and warnings (montecarlo.py, sensitivity.py, diagnostics.py)
        |
        v
  write report.html and report.json (report.py, charts.py, resultsfile.py)
```

1. The command line options are read and turned into settings (a preset plus any changes).
2. The strategy is built from its name and parameters, and checked.
3. The prices are loaded and checked. Bad data stops here with a clear message.
4. The test window is chosen, leaving enough history before it for the strategy's warm-up.
5. The engine replays the strategy, and then buy and hold, over exactly the same days.
6. The numbers are worked out for both, and for a market index if there is one.
7. The Monte Carlo check and the cost check run, and the warnings are collected.
8. The report and the results file are written, and a short summary is printed.

## 3. Each part of the code

All the code is in `src/backtestlab/`. Each file has one job.

- `errors.py`: one base error, `BacktestLabError`, and three kinds below it: `DataError` (bad prices), `StrategyError` (a strategy misbehaved) and `SettingsError` (a bad setting or option). The command catches the base error, so any of them shows up as one "Error: ..." line with no traceback.
- `prices.py`: `PriceData`, which holds the table of prices (one row per day, the date as the index), where it came from and any notes. In go raw rows from a loader, out comes a checked `PriceData`.
- `pricewarnings.py`: the checks that only warn, such as a 40% jump in one day.
- `csvsource.py`: `loadCsv` reads a CSV file, and `saveCsv` writes one back.
- `yahoosource.py`: `downloadPrices` gets prices from Yahoo Finance. It is the only file that uses yfinance.
- `strategy.py`: the `Strategy` base class, `checkTarget`, which makes sure a decision is a number from 0 to 1, and `strategyLabel`, which gives a strategy a readable name.
- `strategies.py`: `BuyAndHold`, `MovingAverageCrossover`, the registry that maps names like `ma-crossover` to them, and the reading of `--param` values.
- `settings.py`: `CostModel` (the charges) and `Settings` (everything a run needs), each with a `check()` method.
- `presets.py`: the two ready-made settings, `DEFAULT` and `INDIA`.
- `costs.py`: the charges on one order, and the biggest order the cash can pay for.
- `window.py`: which days are tested. In go the prices, the warm-up and the dates, out comes the first and last bar.
- `engine.py`: the day-by-day replay. In go prices, a strategy, settings and the window. Out come a row per day (cash, shares, equity, target), the trades and the skipped orders.
- `trades.py`: turns trades into round trips, from the first buy until everything is sold.
- `benchmark.py`: lines up a market index with the test days.
- `metrics.py`: total return, Sharpe ratio, maximum drawdown and the rest.
- `montecarlo.py`: the reshuffling check.
- `sensitivity.py`: the same run with costs times 0, 1 and 2.
- `diagnostics.py`: every warning, with its limits at the top of the file.
- `backtest.py`: `runBacktest`, which does all of the above and returns one `BacktestResult`.
- `summary.py`: the summary sentences.
- `formatting.py`: money (₹1,84,213), percentages (84.2%) and dates (2 Jan 2024).
- `charts.py`: the five charts, as SVG text.
- `report.py` and `templates/report.html`: the HTML page.
- `resultsfile.py`: the JSON file.
- `arguments.py`: reads the command line options.
- `terminal.py`: what is printed after a run.
- `cli.py`: the `backtestlab` command.
- `api.py`: the names people are meant to import, and `VERSION`.

Outside the package, `scripts/check.py` runs every check, `scripts/makesampledata.py` makes the sample prices and `scripts/updatesnapshot.py` refreshes the snapshot test.

## 4. The rules that keep results honest

Decide at the close, trade at the next open. Each day the engine does two things in this order. At the open, if the strategy asked for a change at the previous close, it trades at today's open price. At the close, it writes down the cash, shares and equity (cash plus the shares at the closing price), and then asks the strategy what to do tomorrow. So a decision can never use a price it couldn't have known. The decision on the last day is never carried out, because there is no next day.

The strategy only sees the past. It gets a copy of the history up to and including today. A test multiplies every price after a date by 3 and checks that nothing up to that date changes. Another test hands the strategy a history it scribbles over, and checks the engine's data is untouched.

Costs are always included. Every trade pays brokerage, taxes and fees, and slippage (getting a slightly worse price than the open). The engine never spends more cash than it has.

The engine only trades when the target changes. If the strategy says "fully invested" every day, it buys once and holds. It doesn't keep trading just because prices moved.

The window and the warm-up. A 200-day average can't be worked out until there are 200 days of prices. The test starts on the first day that has enough history before it, and a warning says so if that is later than you asked for. The earlier days are still given to the strategy. That is the warm-up.

The comparison is fair. Buy and hold runs through the same engine, on the same days, with the same costs and the same whole-share rule. That is the main question the report answers: did the strategy beat simply holding?

A small example. Opens and closes: day 1 (100, 100), day 2 (102, 104), day 3 (106, 103), day 4 (101, 99). Starting cash 1,000, no costs, whole shares, and a strategy that always says fully invested. At the close of day 1 it says 1. At the open of day 2 the engine buys 9 shares at 102 (918), leaving 82. Equity at each close is 1,000, 1,018, 1,009 and 973, a fall of 2.7%. With fractional shares it would buy 9.80392157 shares and end at 970.59.

## 5. Every number in the report

All of them come from the equity at each close of the test, E[0] on the first day up to E[T] on the last. The daily return is r = E[today] / E[yesterday] - 1. P is the number of trading days in a year, 252 by default.

- Total return: E[T] / E[0] - 1. Equity going from 100 to 108.9 is 8.9%.
- Annualised return: the steady yearly growth that gives the same total, (E[T] / E[0]) to the power of (1 / years) - 1, with years counted as calendar days / 365.25. Going from 100 to 121 in 2 years is 10% a year.
- Annualised volatility: the sample standard deviation of r times the square root of P. It says how bumpy the ride was. Returns of +10%, -10%, +10% have a standard deviation of 0.1155, and times 15.87 (the square root of 252) that is 183.3%.
- Sharpe ratio: (average r minus the daily risk-free rate) / standard deviation of r, times the square root of P. It is return for each unit of bumpiness. The same three returns give 4.58. It is "not available" when the returns never vary.
- Maximum drawdown: the biggest fall from an earlier high. For 100, 120, 90, 95, 130, 117 it is 120 to 90, which is -25%. The report shows the dates of the peak and the bottom.
- Time in the market: the share of days with shares held at the close.
- Completed trades: finished round trips. A round trip starts with the first buy and ends when every share is sold. Extra buys and part sells in between belong to the same one.
- Win rate: the share of completed round trips with a profit above 0. Profits of +10, -5, +3 and 0 give 50%, because 0 isn't a win.
- Costs paid: every charge added up.
- Slippage cost: for each trade, the gap between the fill price and the open price, times the shares.

A round trip's profit is what came in from selling (after charges) minus what was paid for buying (including charges). Its return is the profit divided by what was paid. A position still held at the end is valued at the last close and shown as open.

The market index, if there is one, is only a reference, so no costs are charged on it. Its closes are scaled to start at the same starting cash. On a day it has no price, the last known one is used, never a later one.

## 6. The Monte Carlo check

The check takes the daily returns the strategy really earned and reshuffles them in blocks of 20 trading days (about a month). Each simulation picks random starting days, takes the 20 days after each one (wrapping round to the start if it runs off the end) and joins the blocks until it is as long as the real test. It does this 1,000 times. Blocks are used instead of single days so that calm and wild stretches stay together, the way they do in real markets.

The same random days are used for the strategy and for buy and hold, so each simulation compares them fairly on the same mix of days.

From the 1,000 results the report shows the 5th, 50th and 95th percentile of the total return and of the maximum drawdown, the chance of ending with a loss, and the chance that the strategy beat buy and hold. A fan chart shows the spread of paths and a histogram shows how often each total return came up.

What it can't tell you: it doesn't run the strategy on new prices, and it can't predict the future. It only shows how much the result depended on the particular order and mix of days that happened. With fewer than 60 daily returns it is skipped. The same seed always gives the same numbers.

## 7. How costs are calculated

Each order pays:

- brokerage: a percentage of the order, with an optional cap per order;
- exchange fees: a percentage of the order;
- tax on fees: a percentage of brokerage plus exchange fees (GST in India);
- a tax on buys only or sells only (stamp duty on buys, STT on both in India);
- a fixed fee per sell order (the depository charge in India).

With the `india` preset, a buy worth ₹1,00,000 costs:

| Charge | Amount |
|---|---|
| Brokerage: 0.1% is ₹100, but the cap is ₹20 | ₹20 |
| Exchange and SEBI fees: 0.00317% | ₹3.17 |
| GST: 18% of ₹23.17 | ₹4.1706 |
| STT 0.1% and stamp duty 0.015% | ₹115 |
| Total | ₹142.3406 |

A sell of the same size pays ₹100 STT and no stamp duty, plus the ₹15.34 depository charge, so ₹142.6806.

Slippage is the idea that you don't get exactly the open price. Buys are filled at the open times (1 + slippage) and sells at the open times (1 - slippage). With 0.05% slippage, a buy at an open of 102 is filled at 102.051.

A buy is cut down to what the cash can pay for after every charge. An order whose charges are bigger than its own value is skipped, and so is a buy that can't pay for even one share. Both are recorded and warned about.

The cost check reruns the strategy with every charge and the slippage times 0, 1 and 2. GST isn't multiplied, because it already grows with the fees it is charged on. If the result falls apart when costs double, the strategy depends on cheap trading.

## 8. How to write your own strategy

1. Make a frozen dataclass that inherits from `Strategy`. Its fields are its parameters.
2. Give it a `description`.
3. If it needs history before its first decision, give it a `warmupBars` property.
4. If some parameter values make no sense, raise `SettingsError` from `check()`.
5. Write `decide(history)`. `history` is a table of every bar up to and including today, with the columns `open`, `high`, `low`, `close` and sometimes `volume`. Return a number from 0 (all cash) to 1 (fully invested).

```python
@dataclass(frozen=True)
class AboveAverage(Strategy):
    description: ClassVar[str] = "Invested while the close is above its moving average."
    window: int = 100

    @property
    def warmupBars(self) -> int:
        return self.window

    def decide(self, history: pd.DataFrame) -> float:
        closes = history["close"]
        return 1.0 if closes.iloc[-1] > closes.tail(self.window).mean() else 0.0
```

Then run it with `runBacktest(prices, AboveAverage(window=100))`. The full version, with comments and a `check()`, is `examples/customstrategy.py`.

## 9. Common backtesting mistakes and how this project avoids them

- Look-ahead, using information you couldn't have had yet. Here a decision made at a close is only carried out at the next open, and the strategy only ever receives the past. Tests check both.
- Ignoring costs. Every trade pays charges and slippage, and the cost check shows what happens if they are higher.
- Overfitting, tuning a rule until it fits the past perfectly. backtestlab can't stop you doing this, but the Monte Carlo check and the warnings about short tests and few trades make a lucky result easier to spot.
- Survivorship bias, testing only companies that are still around today, which makes the past look better than it was. This project tests one asset at a time and can't fix it, so it is listed under limitations.
- Unadjusted prices. A 1:1 bonus issue halves the price overnight, which looks like a crash. Yahoo prices are adjusted, an Adj Close column in a CSV is used to adjust, and a move of more than 35% in a day gives a warning.
- Too few trades. A win rate from 3 trades means very little, so there is a warning below 20.

## 10. Limitations

- Long only: no short selling and no borrowing.
- One asset at a time, with daily prices only.
- Adjusted prices are rescaled using dividends and splits that came later, so a rule based on an exact price level (like "buy below ₹500") behaves differently from how it would have at the time.
- Survivorship bias, as above.
- No tax on gains.
- Cash that isn't invested earns nothing.
- Broker minimum charges and official rounding rules are ignored.
- Yahoo Finance data is unofficial and can have gaps or mistakes.

## 11. Python ideas used in this project

Dataclasses. A dataclass writes the constructor for you from the fields. `frozen=True` means a value can't be changed after it is made, which is why settings and results are safe to pass around.

Abstract base classes. `Strategy` inherits from `ABC` and marks `decide` as abstract, so Python refuses to create a strategy that forgot to write it.

Type hints. Every function says what it takes and returns, and mypy checks them in strict mode.

pathlib. Paths are `Path` objects instead of text, so `folder / "report.html"` works on Windows, macOS and Linux.

Exceptions with a shared base class. `except BacktestLabError` catches every error the library raises on purpose and nothing else, so real bugs still show their traceback.

No underscores. The project has a rule that the underscore character appears nowhere, and a test checks it. Living with it changes a few things:

- Names are camelCase (`shortWindow`) and classes are PascalCase (`MovingAverageCrossover`).
- Python normally marks a package with a special init file whose name has double underscores. There is none here. A folder of modules still works as a package, called a namespace package.
- The command starts through a console script entry in `pyproject.toml`, so there is no special main file.
- The command line parser is written by hand in `arguments.py`, because the usual library's methods have underscores in their names.
- Test files are named `testsomething.py`, and `scripts/check.py` gives them to pytest by name.
- Some library functions have underscores, so I use other ones, for example `Path.open` and `.read()`, and `generator.normal()` for random numbers.
- matplotlib names the parts of its SVG charts with underscores, so the report removes those names. Nothing refers to them.

## 12. Frequently asked questions

Why trade at the next open and not at the close? The close is only known when the day is over. A rule that sees the close can't also have traded at it.

Why does the strategy often lose to buy and hold? Rising markets reward being invested all the time. A strategy that steps out misses some of the best days, pays costs on every trade and leaves cash idle. On TCS from 2018 to 2024 the 50/200 crossover made 162.6% against 253.7% for holding.

Why do the Monte Carlo numbers change with the seed? The seed decides which random blocks are picked. A different seed picks different blocks, so the numbers move a little. The same seed always gives exactly the same numbers.

Why are some numbers "not available"? A Sharpe ratio needs returns that vary, and a win rate needs at least one completed trade. Showing 0 instead would be wrong.

Why whole shares by default? You can't buy 9.8 shares on an Indian exchange. Use `--fractional-shares` to see the result without that limit.

## 13. Glossary

- Adjusted prices: old prices rescaled so that splits, bonus issues and dividends don't look like jumps.
- Annualised: turned into a yearly figure.
- Backtest: replaying a trading rule on old prices.
- Benchmark: a market index used as a reference, such as NIFTY 50.
- Block bootstrap: making new sequences by joining random blocks of real days.
- Brokerage: what the broker charges per order.
- Close, open, high, low: the last, first, highest and lowest price of a day.
- Drawdown: a fall from an earlier high.
- Equity: cash plus the value of the shares held.
- Fill: a trade that happened, at a fill price.
- GST: goods and services tax, 18% on brokerage and fees in India.
- Look-ahead: using information you couldn't have had yet.
- Percentile: the 5th percentile is the value that 5% of results fall below.
- Round trip: from the first buy until every share is sold.
- Sharpe ratio: return for each unit of bumpiness.
- Slippage: getting a slightly worse price than the one quoted.
- STT: securities transaction tax in India.
- Volatility: how much the returns jump around.
- Warm-up: the history a strategy needs before its first decision.
