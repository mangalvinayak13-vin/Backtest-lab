# Does a moving average crossover beat buy and hold once costs and luck are counted?

After my launch post, a reader asked how many of my strategies still beat buy and hold once the charges and the Monte Carlo spread are in. They also suggested comparing the worst fall and the time under water, testing the long window's neighbours, and keeping the same seed. This page is the full breakdown I promised.

The short answer: in the 12 tests I promised (TCS, Reliance and HDFC Bank, a 50-day short window against long windows of 100, 150, 175 and 200 days, 2018 to 2024), buy and hold made more money every time. Holding made 61.4 to 219.8 percentage points more. In 1,000 reshuffled versions of each test, the crossover finished ahead 0.3% to 18.3% of the time.

Everything here comes from one script, [`crossover.py`](crossover.py), which runs [backtestlab](../../README.md) on prices I saved from Yahoo Finance. Every number is also in [`results.csv`](results.csv), one row per backtest.

## Setup

- Strategy: the moving average crossover in backtestlab. It holds the stock while the average close of the last 50 days is above the average close of the last 100, 150, 175 or 200 days, and holds cash otherwise. It decides at the close and trades at the next day's open.
- Stocks: TCS.NS, RELIANCE.NS and HDFCBANK.NS on the NSE.
- Period: 1 Jan 2018 to 31 Dec 2024. Each price file starts in June 2016, so even the longest window has its full history on the first day of the test.
- Settings: backtestlab's `india` preset with nothing changed, except the seed in the seed check and fractional shares for the index in the last check. That means ₹1,00,000 to start, whole shares only, 0.05% slippage on every trade, 1,000 Monte Carlo runs in blocks of 20 trading days, seed 42, and "NIFTY 50 (price index, excludes dividends)" as the market comparison.
- Charges (checked on 23 Nov 2026):
  - Brokerage: 0.1% per order, capped at ₹20 (a typical discount broker; Zerodha charges ₹0 for delivery).
  - STT: 0.1% on buys and on sells.
  - Stamp duty: 0.015% on buys.
  - Exchange and SEBI charges: NSE 0.00307% + SEBI 0.0001%, on both sides.
  - GST: 18% on brokerage, exchange and SEBI charges.
  - DP charge: ₹15.34 per sell, GST included.
  - Checked on 23 Nov 2026 against zerodha.com/charges and groww.in/pricing. Check your own broker's charges.
- Data: daily prices from Yahoo Finance, adjusted for splits and dividends, downloaded once on 26 Nov 2026 and saved as CSV files. Every backtest reads those files, so the numbers can be rebuilt exactly. The price files are not in this repository, because Yahoo's terms don't allow sharing its data.

## What each number means

- Total return: the value on the last day divided by ₹1,00,000, minus 1.
- Strategy minus hold: the strategy's total return minus buy and hold's, in percentage points. Negative means holding made more.
- Buy and hold: buying the same stock on the second day of the test with the same money, charges and whole-share rule, then never selling.
- NIFTY 50: the index scaled to ₹1,00,000 on the first day, with no costs. It is a price index, so it leaves out dividends.
- Annualised return: the yearly growth rate that gives the same total return over the test.
- Volatility: how much the daily returns jump around, scaled to a year.
- Sharpe ratio: average daily return divided by how much it jumps around, scaled to a year (with a 0% risk-free rate). Higher is better.
- Worst fall: the biggest drop from a high to a later low, in percent, with the dates of the high and the low.
- Worst fall in 2020: the same, but the high and the low both have to be inside 2020 (inside 2008 for the 2008 to 2017 tests).
- Longest time under water: the longest run of trading days on which the value was below an earlier high. A run that hadn't ended by 31 Dec 2024 still counts and is marked. My first count, which I posted, used calendar days from the high to the day the value got back to it, so both counts are shown.
- Stretch with the 2020 low: the run of trading days below an earlier high that contains the day of the worst 2020 low.
- Time in the market: the share of days on which the strategy held the stock at the close.
- Round trips: completed buy-then-sell pairs. Win rate is the share of round trips that made money after costs.
- Charges and taxes, and slippage: everything paid on all trades, in rupees.
- Chance of beating buy and hold: how often, out of 1,000 reshuffles, the strategy's total return came out higher than holding's (see the Monte Carlo note below).
- Costs ×0, ×1 and ×2: the same strategy run again with every charge, tax and the slippage set to zero, left as they are, and doubled.

## Part 1: the 12 tests I promised

![Strategy minus buy and hold for the 12 tests](charts/heatmap2018.png)

### Returns

| Stock | Windows | Strategy final value | Strategy return | Buy and hold return | NIFTY 50 return | Strategy minus hold (points) |
|---|---|---|---|---|---|---|
| TCS | 50/100 | ₹2,10,482 | 110.5% | 253.7% | 124.5% | -143.2 |
| TCS | 50/150 | ₹2,18,557 | 118.6% | 253.7% | 124.5% | -135.1 |
| TCS | 50/175 | ₹1,95,092 | 95.1% | 253.7% | 124.5% | -158.6 |
| TCS | 50/200 | ₹2,62,618 | 162.6% | 253.7% | 124.5% | -91.1 |
| Reliance | 50/100 | ₹1,10,608 | 10.6% | 199.1% | 124.5% | -188.5 |
| Reliance | 50/150 | ₹79,272 | -20.7% | 199.1% | 124.5% | -219.8 |
| Reliance | 50/175 | ₹1,16,589 | 16.6% | 199.1% | 124.5% | -182.5 |
| Reliance | 50/200 | ₹1,39,663 | 39.7% | 199.1% | 124.5% | -159.4 |
| HDFC Bank | 50/100 | ₹1,39,447 | 39.4% | 100.9% | 124.5% | -61.4 |
| HDFC Bank | 50/150 | ₹1,19,844 | 19.8% | 100.9% | 124.5% | -81.0 |
| HDFC Bank | 50/175 | ₹1,20,265 | 20.3% | 100.9% | 124.5% | -80.6 |
| HDFC Bank | 50/200 | ₹1,22,832 | 22.8% | 100.9% | 124.5% | -78.1 |

### Risk and return per year (strategy / buy and hold)

| Stock | Windows | Annualised return | Volatility | Sharpe ratio |
|---|---|---|---|---|
| TCS | 50/100 | 11.2% / 19.8% | 19.5% / 24.3% | 0.66 / 0.88 |
| TCS | 50/150 | 11.8% / 19.8% | 20.4% / 24.3% | 0.66 / 0.88 |
| TCS | 50/175 | 10.0% / 19.8% | 20.6% / 24.3% | 0.58 / 0.88 |
| TCS | 50/200 | 14.8% / 19.8% | 21.2% / 24.3% | 0.77 / 0.88 |
| Reliance | 50/100 | 1.5% / 16.9% | 20.4% / 28.9% | 0.17 / 0.70 |
| Reliance | 50/150 | -3.3% / 16.9% | 22.6% / 28.9% | -0.04 / 0.70 |
| Reliance | 50/175 | 2.2% / 16.9% | 24.9% / 28.9% | 0.22 / 0.70 |
| Reliance | 50/200 | 4.9% / 16.9% | 25.5% / 28.9% | 0.32 / 0.70 |
| HDFC Bank | 50/100 | 4.9% / 10.5% | 17.1% / 24.9% | 0.37 / 0.53 |
| HDFC Bank | 50/150 | 2.6% / 10.5% | 17.8% / 24.9% | 0.24 / 0.53 |
| HDFC Bank | 50/175 | 2.7% / 10.5% | 18.5% / 24.9% | 0.24 / 0.53 |
| HDFC Bank | 50/200 | 3.0% / 10.5% | 18.2% / 24.9% | 0.26 / 0.53 |

### Worst falls

![Worst fall for the whole period and inside 2020](charts/worstfall.png)

| Stock | Windows | Worst fall, strategy | Worst fall, buy and hold | Worst fall in 2020, strategy | Worst fall in 2020, buy and hold |
|---|---|---|---|---|---|
| TCS | 50/100 | -36.3% (1 Oct 2018 to 16 Mar 2020) | -27.1% (31 Oct 2019 to 19 Mar 2020) | -24.3% (8 Jan 2020 to 16 Mar 2020) | -26.6% (8 Jan 2020 to 19 Mar 2020) |
| TCS | 50/150 | -36.7% (31 Oct 2019 to 24 Jul 2020) | -27.1% (31 Oct 2019 to 19 Mar 2020) | -33.7% (8 Jan 2020 to 24 Jul 2020) | -26.6% (8 Jan 2020 to 19 Mar 2020) |
| TCS | 50/175 | -41.9% (1 Oct 2018 to 24 Jul 2020) | -27.1% (31 Oct 2019 to 19 Mar 2020) | -32.2% (8 Jan 2020 to 24 Jul 2020) | -26.6% (8 Jan 2020 to 19 Mar 2020) |
| TCS | 50/200 | -27.5% (31 Oct 2019 to 24 Jul 2020) | -27.1% (31 Oct 2019 to 19 Mar 2020) | -27.1% (8 Jan 2020 to 24 Jul 2020) | -26.6% (8 Jan 2020 to 19 Mar 2020) |
| Reliance | 50/100 | -33.1% (16 Sep 2020 to 7 Feb 2023) | -45.0% (19 Dec 2019 to 23 Mar 2020) | -20.4% (16 Sep 2020 to 3 Nov 2020) | -44.0% (17 Jan 2020 to 23 Mar 2020) |
| Reliance | 50/150 | -52.3% (28 Aug 2018 to 19 Mar 2020) | -45.0% (19 Dec 2019 to 23 Mar 2020) | -41.8% (17 Jan 2020 to 19 Mar 2020) | -44.0% (17 Jan 2020 to 23 Mar 2020) |
| Reliance | 50/175 | -46.1% (3 May 2019 to 23 Mar 2020) | -45.0% (19 Dec 2019 to 23 Mar 2020) | -44.0% (17 Jan 2020 to 23 Mar 2020) | -44.0% (17 Jan 2020 to 23 Mar 2020) |
| Reliance | 50/200 | -45.7% (3 May 2019 to 23 Mar 2020) | -45.0% (19 Dec 2019 to 23 Mar 2020) | -44.0% (17 Jan 2020 to 23 Mar 2020) | -44.0% (17 Jan 2020 to 23 Mar 2020) |
| HDFC Bank | 50/100 | -28.8% (16 Feb 2021 to 4 Jun 2024) | -40.9% (23 Dec 2019 to 24 Mar 2020) | -12.2% (14 Jan 2020 to 3 Aug 2020) | -40.3% (14 Jan 2020 to 24 Mar 2020) |
| HDFC Bank | 50/150 | -32.7% (2 Jul 2019 to 24 Sep 2020) | -40.9% (23 Dec 2019 to 24 Mar 2020) | -26.5% (14 Jan 2020 to 24 Sep 2020) | -40.3% (14 Jan 2020 to 24 Mar 2020) |
| HDFC Bank | 50/175 | -40.8% (23 Dec 2019 to 24 Sep 2020) | -40.9% (23 Dec 2019 to 24 Mar 2020) | -40.2% (14 Jan 2020 to 24 Sep 2020) | -40.3% (14 Jan 2020 to 24 Mar 2020) |
| HDFC Bank | 50/200 | -35.7% (23 Dec 2019 to 24 Sep 2020) | -40.9% (23 Dec 2019 to 24 Mar 2020) | -35.0% (14 Jan 2020 to 24 Sep 2020) | -40.3% (14 Jan 2020 to 24 Mar 2020) |

### Time under water (trading days)

| Stock | Windows | Longest under water, strategy | Longest under water, buy and hold | Same in calendar days (strategy / hold) | Stretch with the 2020 low (strategy / hold) |
|---|---|---|---|---|---|
| TCS | 50/100 | 559 | 472 | 830 / 697 | 559 / 166 |
| TCS | 50/150 | 496 | 472 | 732 / 697 | 444 / 166 |
| TCS | 50/175 | 715 | 472 | 1061 / 697 | 715 / 166 |
| TCS | 50/200 | 491 | 472 | 725 / 697 | 293 / 166 |
| Reliance | 50/100 | 1060 (still under at the end) | 302 | 1567 / 446 | 1060 (still under at the end) / 117 |
| Reliance | 50/150 | 1563 (still under at the end) | 302 | 2317 / 446 | 1563 (still under at the end) / 117 |
| Reliance | 50/175 | 1400 (still under at the end) | 302 | 2069 / 446 | 1400 (still under at the end) / 117 |
| Reliance | 50/200 | 739 | 302 | 1091 / 446 | 739 / 117 |
| HDFC Bank | 50/100 | 955 (still under at the end) | 314 | 1414 / 461 | 314 / 218 |
| HDFC Bank | 50/150 | 393 | 314 | 581 / 461 | 393 / 218 |
| HDFC Bank | 50/175 | 737 | 314 | 1085 / 461 | 737 / 218 |
| HDFC Bank | 50/200 | 833 | 314 | 1228 / 461 | 833 / 218 |

### Trading and costs

| Stock | Windows | Time in the market | Round trips | Win rate | Charges and taxes | Slippage |
|---|---|---|---|---|---|---|
| TCS | 50/100 | 71.0% | 10 | 40.0% | ₹4,277 | ₹1,645 |
| TCS | 50/150 | 78.0% | 5 | 80.0% | ₹2,192 | ₹831 |
| TCS | 50/175 | 80.7% | 6 | 50.0% | ₹2,396 | ₹894 |
| TCS | 50/200 | 85.2% | 3 | 66.7% | ₹1,526 | ₹588 |
| Reliance | 50/100 | 62.5% | 13 | 46.2% | ₹4,140 | ₹1,496 |
| Reliance | 50/150 | 70.7% | 12 | 41.7% | ₹3,149 | ₹1,078 |
| Reliance | 50/175 | 77.3% | 7 | 71.4% | ₹2,121 | ₹757 |
| Reliance | 50/200 | 82.3% | 6 | 66.7% | ₹1,966 | ₹717 |
| HDFC Bank | 50/100 | 67.5% | 8 | 50.0% | ₹2,886 | ₹1,059 |
| HDFC Bank | 50/150 | 70.2% | 7 | 57.1% | ₹2,319 | ₹832 |
| HDFC Bank | 50/175 | 72.6% | 5 | 60.0% | ₹1,643 | ₹584 |
| HDFC Bank | 50/200 | 71.4% | 5 | 80.0% | ₹1,570 | ₹551 |

### Monte Carlo

![Chance of beating buy and hold](charts/montecarlo.png)

| Stock | Windows | Chance of beating buy and hold | 5th percentile final value | Median final value | 95th percentile final value |
|---|---|---|---|---|---|
| TCS | 50/100 | 4.1% | ₹88,869 | ₹2,12,245 | ₹4,82,905 |
| TCS | 50/150 | 3.3% | ₹79,970 | ₹2,16,784 | ₹5,65,038 |
| TCS | 50/175 | 1.4% | ₹72,588 | ₹1,94,787 | ₹5,01,640 |
| TCS | 50/200 | 7.1% | ₹1,01,106 | ₹2,59,698 | ₹6,70,972 |
| Reliance | 50/100 | 3.6% | ₹47,284 | ₹1,12,609 | ₹2,54,327 |
| Reliance | 50/150 | 0.3% | ₹27,144 | ₹80,576 | ₹2,19,530 |
| Reliance | 50/175 | 0.8% | ₹35,106 | ₹1,15,382 | ₹3,40,896 |
| Reliance | 50/200 | 1.2% | ₹43,320 | ₹1,41,053 | ₹4,29,264 |
| HDFC Bank | 50/100 | 18.3% | ₹68,662 | ₹1,38,012 | ₹2,76,843 |
| HDFC Bank | 50/150 | 6.0% | ₹53,485 | ₹1,21,758 | ₹2,42,875 |
| HDFC Bank | 50/175 | 4.5% | ₹47,631 | ₹1,25,488 | ₹2,80,447 |
| HDFC Bank | 50/200 | 6.8% | ₹50,835 | ₹1,25,365 | ₹2,71,176 |

The Monte Carlo check in two sentences: it takes the daily returns that the strategy and buy and hold actually earned, cuts them into 20-day blocks and shuffles the same blocks for both, 1,000 times, to see how often the strategy finishes ahead. It doesn't test new prices or new signals, so it shows how much the result depends on the order of these particular days, and it can't say whether the rule will work in the future.

### Costs ×0, ×1 and ×2

![Total return with costs times 0, 1 and 2](charts/costs.png)

| Stock | Windows | Return, costs ×0 | ×1 | ×2 | Annualised ×0 / ×1 / ×2 | Sharpe ×0 / ×1 / ×2 | Buy and hold return |
|---|---|---|---|---|---|---|---|
| TCS | 50/100 | 117.9% | 110.5% | 102.0% | 11.8% / 11.2% / 10.6% | 0.68 / 0.66 / 0.63 | 253.7% |
| TCS | 50/150 | 124.2% | 118.6% | 114.3% | 12.2% / 11.8% / 11.5% | 0.68 / 0.66 / 0.65 | 253.7% |
| TCS | 50/175 | 100.1% | 95.1% | 91.7% | 10.4% / 10.0% / 9.7% | 0.59 / 0.58 / 0.56 | 253.7% |
| TCS | 50/200 | 165.9% | 162.6% | 158.6% | 15.0% / 14.8% / 14.5% | 0.78 / 0.77 / 0.76 | 253.7% |
| Reliance | 50/100 | 16.1% | 10.6% | 5.1% | 2.2% / 1.5% / 0.7% | 0.21 / 0.17 / 0.14 | 199.1% |
| Reliance | 50/150 | -17.0% | -20.7% | -24.5% | -2.6% / -3.3% / -3.9% | -0.01 / -0.04 / -0.07 | 199.1% |
| Reliance | 50/175 | 20.0% | 16.6% | 13.7% | 2.6% / 2.2% / 1.9% | 0.23 / 0.22 / 0.20 | 199.1% |
| Reliance | 50/200 | 43.3% | 39.7% | 36.8% | 5.3% / 4.9% / 4.6% | 0.33 / 0.32 / 0.31 | 199.1% |
| HDFC Bank | 50/100 | 44.0% | 39.4% | 35.1% | 5.3% / 4.9% / 4.4% | 0.40 / 0.37 / 0.34 | 100.9% |
| HDFC Bank | 50/150 | 23.2% | 19.8% | 16.4% | 3.0% / 2.6% / 2.2% | 0.26 / 0.24 / 0.21 | 100.9% |
| HDFC Bank | 50/175 | 22.7% | 20.3% | 17.7% | 3.0% / 2.7% / 2.4% | 0.25 / 0.24 / 0.22 | 100.9% |
| HDFC Bank | 50/200 | 25.7% | 22.8% | 20.4% | 3.3% / 3.0% / 2.7% | 0.27 / 0.26 / 0.24 | 100.9% |

### Warnings from backtestlab

| Stock | Windows | Warnings from backtestlab |
|---|---|---|
| TCS | 50/100 | Only 10 completed trades. A win rate based on so few trades is unreliable. |
| TCS | 50/150 | Only 5 completed trades. A win rate based on so few trades is unreliable. |
| TCS | 50/175 | Only 6 completed trades. A win rate based on so few trades is unreliable. |
| TCS | 50/200 | Only 3 completed trades. A win rate based on so few trades is unreliable. |
| Reliance | 50/100 | Only 13 completed trades. A win rate based on so few trades is unreliable. |
| Reliance | 50/150 | Only 12 completed trades. A win rate based on so few trades is unreliable. |
| Reliance | 50/175 | Only 7 completed trades. A win rate based on so few trades is unreliable. |
| Reliance | 50/200 | Only 6 completed trades. A win rate based on so few trades is unreliable. |
| HDFC Bank | 50/100 | Only 8 completed trades. A win rate based on so few trades is unreliable. |
| HDFC Bank | 50/150 | Only 7 completed trades. A win rate based on so few trades is unreliable. |
| HDFC Bank | 50/175 | Only 5 completed trades. A win rate based on so few trades is unreliable. |
| HDFC Bank | 50/200 | Only 5 completed trades. A win rate based on so few trades is unreliable. |

### Growth of ₹1,00,000, 50/200 against buy and hold

![Growth of 1 lakh](charts/growth.png)

### Every 50/200 round trip

TCS

| Bought | Sold | Days held | Result after costs |
|---|---|---|---|
| 2 Jan 2018 | 18 Mar 2020 | 806 | +32.3% |
| 10 Jul 2020 | 9 May 2022 | 668 | +56.5% |
| 5 Jan 2023 | 19 May 2023 | 134 | -1.8% |
| 7 Jun 2023 | still held at the end | 573 | +29.7% |

Reliance

| Bought | Sold | Days held | Result after costs |
|---|---|---|---|
| 2 Jan 2018 | 9 Sep 2019 | 615 | +34.9% |
| 23 Oct 2019 | 25 Mar 2020 | 154 | -32.2% |
| 15 Jun 2020 | 8 Apr 2021 | 297 | +28.5% |
| 28 Jun 2021 | 28 Oct 2022 | 487 | +16.1% |
| 13 Dec 2022 | 6 Feb 2023 | 55 | -11.7% |
| 27 Jun 2023 | 24 Oct 2024 | 485 | +16.3% |

HDFC Bank

| Bought | Sold | Days held | Result after costs |
|---|---|---|---|
| 2 Jan 2018 | 12 Nov 2018 | 314 | +5.3% |
| 21 Dec 2018 | 19 Mar 2020 | 454 | -20.3% |
| 24 Sep 2020 | 29 Sep 2020 | 5 | +1.5% |
| 6 Oct 2020 | 21 Jan 2022 | 472 | +32.2% |
| 12 Sep 2022 | 28 Sep 2023 | 381 | +3.1% |
| 20 Jun 2024 | still held at the end | 194 | +6.0% |

### 2020: when the 50/200 crossover left the market and when it came back

| Stock | Sold (out of the market) | Bought back | Holding gained in between |
|---|---|---|---|
| TCS | 18 Mar 2020 | 10 Jul 2020 | +32.9% |
| Reliance | 25 Mar 2020 | 15 Jun 2020 | +63.9% |
| HDFC Bank | 19 Mar 2020 | 24 Sep 2020 | +22.6% |
| HDFC Bank | 29 Sep 2020 | 6 Oct 2020 | +7.3% |

"Holding gained in between" is the change in the stock's opening price from the day the strategy sold to the day it bought back. It is what the strategy missed (or avoided, when it is negative) by being in cash.

## What I found

1. Buy and hold won all 12 tests, by 61.4 to 219.8 percentage points. In this strong uptrend the crossover sold after falls and bought back only after prices had recovered. In 2020 the three 50/200 runs sold between 18 Mar 2020 and 25 Mar 2020, close to the low, and bought back between 15 Jun 2020 and 24 Sep 2020. Holding gained 22.6% to 63.9% while they waited in cash.
2. Charges are not the reason. With every cost set to zero, none of the 12 settings beat buy and hold. Removing all costs added only 2.4 to 7.4 points to the strategy's return. The loss comes from the timing.
3. The protection on the way down was small and patchy. The crossover's worst fall was more than 1 point smaller than holding's in 4 of 12 tests over 2018 to 2024, and in 6 of 12 inside 2020. Its longest time under water was longer than holding's in all 12 tests, counted in trading days or in calendar days. Sitting in cash at a lower value is still time under water.
4. The loss holds across the plateau. Over the wider grid of 69 short and long windows, none beat buy and hold. Because so many settings were tried, a single winner here could have been luck, so I don't pick a best setting.
5. The older period with the 2008 crash looks different. From 2008 to 2017 the crossover beat holding in 3 of 12 tests and cut the 2008 fall by more than 1 point in 12 of 12. The drawdown case is real in a long, deep crash, but it wasn't enough to win most of the time, and the longest time under water was still longer than holding's in 11 of 12.
6. On a stock that collapsed, the crossover helped. On YES Bank it beat holding in 4 of 4 tests, but it still lost 42.9% to 79.2% while holding lost 93.5%. My three main stocks all did well over these years, which flatters buy and hold.

## Extra checks I added (not part of what I promised)

### 1. Zero costs

This is the "Costs ×0" column in the costs table above. None of the 12 settings beat buy and hold even with no charges, taxes or slippage, so the late entries cause the loss.

### 2. Other seeds

The seed only changes the Monte Carlo draw, never the backtest itself. Across seeds 1 to 5, the chance of beating buy and hold stayed between 0.0% and 21.8%, and no test moved by more than 3.5 points between seeds. None of the conclusions depend on the seed.

| Stock | Windows | Seed 42 | Seeds 1 to 5 |
|---|---|---|---|
| TCS | 50/100 | 4.1% | 3.5% to 4.9% |
| TCS | 50/150 | 3.3% | 3.6% to 4.3% |
| TCS | 50/175 | 1.4% | 1.3% to 1.9% |
| TCS | 50/200 | 7.1% | 7.1% to 8.6% |
| Reliance | 50/100 | 3.6% | 3.4% to 4.2% |
| Reliance | 50/150 | 0.3% | 0.0% to 0.3% |
| Reliance | 50/175 | 0.8% | 0.2% to 0.8% |
| Reliance | 50/200 | 1.2% | 0.8% to 1.7% |
| HDFC Bank | 50/100 | 18.3% | 19.9% to 21.8% |
| HDFC Bank | 50/150 | 6.0% | 5.3% to 8.0% |
| HDFC Bank | 50/175 | 4.5% | 4.1% to 6.8% |
| HDFC Bank | 50/200 | 6.8% | 7.5% to 9.8% |

### 3. Interest on idle cash (my assumption, worked out outside backtestlab)

backtestlab pays nothing on cash. To see whether that matters, I took each day's cash balance from the backtest and added interest at 6% a year, compounded daily over 252 trading days. I did the same for buy and hold, which keeps a little cash left over after buying whole shares. This is a rough estimate: in reality the interest would also change how many shares the next buy gets.

| Stock | Windows | Strategy minus hold, cash at 0% | Same with cash at 6% | Strategy return with 6% | Buy and hold return with 6% |
|---|---|---|---|---|---|
| TCS | 50/100 | -143.2 | -117.7 | 136.7% | 254.4% |
| TCS | 50/150 | -135.1 | -115.2 | 139.2% | 254.4% |
| TCS | 50/175 | -158.6 | -142.9 | 111.4% | 254.4% |
| TCS | 50/200 | -91.1 | -75.3 | 179.1% | 254.4% |
| Reliance | 50/100 | -188.5 | -170.7 | 28.6% | 199.3% |
| Reliance | 50/150 | -219.8 | -210.1 | -10.7% | 199.3% |
| Reliance | 50/175 | -182.5 | -171.5 | 27.8% | 199.3% |
| Reliance | 50/200 | -159.4 | -149.2 | 50.1% | 199.3% |
| HDFC Bank | 50/100 | -61.4 | -42.3 | 58.9% | 101.2% |
| HDFC Bank | 50/150 | -81.0 | -66.1 | 35.1% | 101.2% |
| HDFC Bank | 50/175 | -80.6 | -66.9 | 34.3% | 101.2% |
| HDFC Bank | 50/200 | -78.1 | -63.4 | 37.8% | 101.2% |

It narrows the gap but changes none of the 12 results. In the 2008 to 2017 tests below, the same estimate would turn 4 of 12 losses into wins, because the strategy spent long periods in cash.

### 4. A wider plateau of windows

Short windows of 10, 20, 50 and 100 days against long windows of 100, 125, 150, 175, 200 and 250 days, keeping the short one below the long one. That is 23 pairs per stock, so I don't present a best one.

![TCS plateau](charts/plateautcs.png)

![Reliance plateau](charts/plateaureliance.png)

![HDFC Bank plateau](charts/plateauhdfcbank.png)

### 5. A period with a long crash: 2008 to 2017

The same 12 tests from 1 Jan 2008 to 31 Dec 2017, with 2008 in place of 2020 for the crash-year columns.

![2008 to 2017 next to 2018 to 2024](charts/periods.png)

| Stock | Windows | Strategy return | Buy and hold return | NIFTY 50 return | Strategy minus hold (points) | Worst fall in 2008 (strategy / hold) | Chance of beating hold | Round trips |
|---|---|---|---|---|---|---|---|---|
| TCS | 50/100 | 300.4% | 519.0% | 71.4% | -218.6 | -29.5% / -56.7% | 23.1% | 12 |
| TCS | 50/150 | 483.5% | 519.0% | 71.4% | -35.5 | -7.8% / -56.7% | 46.0% | 8 |
| TCS | 50/175 | 586.5% | 519.0% | 71.4% | +67.6 | 0.0% / -56.7% | 57.5% | 4 |
| TCS | 50/200 | 539.0% | 519.0% | 71.4% | +20.1 | 0.0% / -56.7% | 51.4% | 4 |
| Reliance | 50/100 | 62.4% | 41.5% | 71.4% | +20.9 | -31.4% / -68.1% | 56.8% | 16 |
| Reliance | 50/150 | 20.1% | 41.5% | 71.4% | -21.5 | -33.2% / -68.1% | 42.4% | 12 |
| Reliance | 50/175 | 20.7% | 41.5% | 71.4% | -20.8 | -33.2% / -68.1% | 40.9% | 12 |
| Reliance | 50/200 | 20.8% | 41.5% | 71.4% | -20.7 | -33.2% / -68.1% | 41.8% | 10 |
| HDFC Bank | 50/100 | 100.7% | 478.9% | 71.4% | -378.2 | -47.0% / -53.8% | 4.4% | 12 |
| HDFC Bank | 50/150 | 218.6% | 478.9% | 71.4% | -260.4 | -31.4% / -53.8% | 18.9% | 8 |
| HDFC Bank | 50/175 | 209.2% | 478.9% | 71.4% | -269.7 | -31.4% / -53.8% | 16.6% | 6 |
| HDFC Bank | 50/200 | 266.2% | 478.9% | 71.4% | -212.7 | -31.4% / -53.8% | 24.5% | 6 |

Time under water, 2008 to 2017:

| Stock | Windows | Longest under water, strategy | Longest under water, buy and hold | Same in calendar days (strategy / hold) | Stretch with the 2008 low (strategy / hold) |
|---|---|---|---|---|---|
| TCS | 50/100 | 797 (still under at the end) | 384 | 1185 / 576 | 246 / 384 |
| TCS | 50/150 | 797 (still under at the end) | 384 | 1185 / 576 | 218 / 384 |
| TCS | 50/175 | 698 (still under at the end) | 384 | 1032 / 576 | 0 / 384 |
| TCS | 50/200 | 698 (still under at the end) | 384 | 1032 / 576 | 0 / 384 |
| Reliance | 50/100 | 2054 | 2331 | 3040 / 3462 | 300 / 2331 |
| Reliance | 50/150 | 2397 | 2331 | 3559 / 3462 | 2397 / 2331 |
| Reliance | 50/175 | 2397 | 2331 | 3559 / 3462 | 2397 / 2331 |
| Reliance | 50/200 | 2397 | 2331 | 3559 / 3462 | 2397 / 2331 |
| HDFC Bank | 50/100 | 652 | 452 | 973 / 679 | 652 / 452 |
| HDFC Bank | 50/150 | 488 | 452 | 721 / 679 | 339 / 452 |
| HDFC Bank | 50/175 | 531 | 452 | 798 / 679 | 531 / 452 |
| HDFC Bank | 50/200 | 457 | 452 | 680 / 679 | 453 / 452 |

### 6. Two more assets: an index fund and a stock that collapsed

I meant to use NIFTYBEES.NS, a NIFTY 50 ETF, but its Yahoo prices are broken around a unit split. backtestlab flagged it: "The close moved by more than 35% in one day on 2019-12-19 (-89.9%), 2019-12-23 (+896.9%). This is often a split or bonus issue that was not adjusted for." So I used the NIFTY 50 index itself (^NSEI) in its place. The index level was over 10,000, so one whole unit would have used about a tenth of the money. A real ETF unit costs far less, so for this one asset I allowed fractional shares. The index has no price on 1 Jan 2018, so these tests start on 2 Jan 2018. It leaves out dividends, and the charges are the stock charges from the india preset.

I picked YES Bank on purpose, because it collapsed in 2020 and shows the other side: my three main stocks all did well, and testing only stocks that did well (survivorship bias) makes buy and hold look better than it would have looked at the time. YES Bank's big one-day moves in March 2020 are real (a bank rescue), and backtestlab warns about them because moves that size are usually data errors.

| Asset | Windows | Strategy return | Buy and hold return | Strategy minus hold (points) | Worst fall (strategy / hold) | Chance of beating hold | Round trips | Warnings |
|---|---|---|---|---|---|---|---|---|
| NIFTY 50 | 50/100 | 75.9% | 125.1% | -49.2 | -23.9% / -38.4% | 18.2% | 8 | few-trades window-moved |
| NIFTY 50 | 50/150 | 16.1% | 125.1% | -109.0 | -43.8% / -38.4% | 0.0% | 6 | few-trades window-moved |
| NIFTY 50 | 50/175 | 17.3% | 125.1% | -107.9 | -45.7% / -38.4% | 0.1% | 5 | few-trades window-moved |
| NIFTY 50 | 50/200 | 27.4% | 125.1% | -97.7 | -43.0% / -38.4% | 0.2% | 5 | few-trades window-moved |
| YES Bank | 50/100 | -79.2% | -93.5% | +14.3 | -85.1% / -97.1% | 79.3% | 10 | few-trades data-note |
| YES Bank | 50/150 | -68.7% | -93.5% | +24.8 | -81.1% / -97.1% | 87.9% | 8 | few-trades data-note |
| YES Bank | 50/175 | -64.8% | -93.5% | +28.7 | -79.1% / -97.1% | 89.6% | 6 | few-trades data-note |
| YES Bank | 50/200 | -42.9% | -93.5% | +50.6 | -61.5% / -97.1% | 93.4% | 6 | few-trades data-note |

## Checks on the numbers

For the 50/200 test on each stock I worked out three numbers again without the engine: the buy and hold return from the opening and closing prices and the charge formula, the number of times the 50-day average crossed above the 200-day one (with pandas' own rolling averages), and the worst fall straight from the equity curve. All of them match backtestlab.

| Stock | Number | Worked out by hand | From backtestlab | Match |
|---|---|---|---|---|
| TCS | buy and hold return | 2.536860113 | 2.536860113 | yes |
| TCS | crossovers into the market | 4 | 4 | yes |
| TCS | worst fall | -0.2753214061 | -0.2753214061 | yes |
| Reliance | buy and hold return | 1.991008745 | 1.991008745 | yes |
| Reliance | crossovers into the market | 6 | 6 | yes |
| Reliance | worst fall | -0.4572749373 | -0.4572749373 | yes |
| HDFC Bank | buy and hold return | 1.008826999 | 1.008826999 | yes |
| HDFC Bank | crossovers into the market | 6 | 6 | yes |
| HDFC Bank | worst fall | -0.3568369471 | -0.3568369471 | yes |

The 50/200 numbers also match what I wrote before:

| Stock | Strategy (earlier / now) | Buy and hold (earlier / now) | Round trips (earlier / now) |
|---|---|---|---|
| TCS | 162.6% / 162.6% | 253.7% / 253.7% | 3 / 3 |
| Reliance | 39.7% / 39.7% | 199.1% / 199.1% | 6 / 6 |
| HDFC Bank | 22.8% / 22.8% | 100.9% / 100.9% | 5 / 5 |
| NIFTY 50 |  | 124.5% / 124.5% |  |

I ran the script twice and `results.csv` came out identical both times.

## Limitations

- The 12 promised tests have only 3 to 13 round trips each, so the win rates in particular mean very little. backtestlab warns about this in every test.
- Survivorship bias: TCS, Reliance and HDFC Bank are big, successful companies today. I picked them knowing that, and the YES Bank check shows how different a failed stock looks.
- The NIFTY 50 comparison uses the price index, which leaves out dividends (roughly 1% to 1.5% a year), so it makes the index look worse than a real index fund. Buy and hold of each stock does include dividends, because Yahoo's prices are adjusted for them.
- Yahoo Finance data is unofficial and can be revised. My numbers match my earlier run, but a later download could differ slightly.
- Long only, one stock at a time, daily prices, no tax on gains and no interest on cash (except in the estimate above).
- Past results don't predict future ones. This is for education only and is not investment advice.

## Rebuild everything

```
python -m pip install -e ".[dev]"
python experiments/crossover/crossover.py download
python experiments/crossover/crossover.py run
```

The first command after the install downloads the prices (once). The second runs all 149 backtests from the saved files and rewrites `results.csv`, the charts and this page. It takes about two minutes.
