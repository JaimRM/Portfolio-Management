# Statistical Arbitrage — Pairs Trading

Cointegration-based pairs trading engine: screens a universe for
statistically valid pairs, models the spread as an Ornstein-Uhlenbeck
process, generates z-score entry/exit signals, and backtests with
transaction costs and no look-ahead bias.

## Architecture

```
pairs_trading/
├── config.py             ScreeningConfig, StrategyConfig, BacktestConfig
├── data_loader.py         price data (yfinance; can swap for Bloomberg/internal feed)
├── cointegration.py       Engle-Granger test + OLS hedge ratio
├── spread_analysis.py     spread, rolling z-score, OU parameter estimation
├── screener.py             scans a universe, ranks tradeable pairs
├── strategy.py              z-score state machine -> position series
├── backtest.py              vectorized P&L, Sharpe, drawdown, win rate
└── main.py                    example end-to-end run
```

## The math

**1. Cointegration (Engle-Granger, two-step).**
Two I(1) (random-walk) price series `y_t`, `x_t` are cointegrated if some
linear combination is stationary:

```
y_t = alpha + beta * x_t + eps_t,      eps_t ~ I(0)
```

`beta` is estimated by OLS (the hedge ratio); `eps_t` (the spread) is
then tested for a unit root via Augmented Dickey-Fuller. We require both
`statsmodels.tsa.stattools.coint` (correct MacKinnon critical values) and
a direct ADF on the residuals to reject the null of a unit root.

**2. Spread dynamics (Ornstein-Uhlenbeck).**
```
dS_t = theta (mu - S_t) dt + sigma dW_t
```
Estimated via the AR(1) regression `S_t - S_{t-1} = a + b S_{t-1} + eps`,
giving `theta = -b/dt`, `mu = -a/b`, and half-life `= ln(2)/theta`; the
expected number of periods for the spread to revert halfway to its mean.
This half-life is the natural scale for both the z-score lookback window
and the expected holding period.

**3. Signal.** Rolling z-score of the spread; enter at `|z| > entry`,
exit at `|z| < exit`, hard stop at `|z| > stop` (protects against the
cointegration relationship itself breaking down).

## Known statistical risk: spurious cointegration

Screening N tickers tests `N(N-1)/2` pairs simultaneously. At a flat 5%
significance level this produces false positives at a much higher rate
than 5% overall. `ScreeningConfig.bonferroni_correction` (on by default)
divides the significance threshold by the number of pairs tested.

**This is not sufficient on its own.** Engle-Granger/ADF tests have
known finite-sample size distortion. Even fully independent random
walks can occasionally clear a Bonferroni-corrected threshold (verified
in `test_pipeline.py`). We should never select a pair by p-value alone; always
require an economic rationale (same sector, shared risk factor, ADR /
share-class relationship) on top of the statistical filter.

## Usage

```bash
pip install -r requirements.txt
python -m pairs_trading.main
```

```python
from pairs_trading import (
    fetch_close_prices, screen_pairs, test_cointegration,
    compute_spread, rolling_zscore, generate_positions, run_backtest,
    ScreeningConfig, StrategyConfig, BacktestConfig,
)

prices = fetch_close_prices(["KO", "PEP"], start="2019-01-01")
candidates = screen_pairs(prices, ScreeningConfig())

y, x = prices["KO"], prices["PEP"]
coint = test_cointegration(y, x)
spread = compute_spread(y, x, coint.hedge_ratio, coint.intercept)
z = rolling_zscore(spread, window=21)
positions = generate_positions(z, StrategyConfig())

result = run_backtest(y, x, coint.hedge_ratio, positions, **BacktestConfig().__dict__)
print(result.summary())
```

## Design notes / next steps for production

- **Hedge ratio drift**: this implementation uses a static, full-sample
  OLS beta. In production, re-estimate on a rolling or Kalman-filtered
  basis (`BacktestConfig.hedge_ratio_window` is a placeholder for this)
  so the hedge tracks a slowly time-varying relationship.
- **Walk-forward validation**: screen on an in-sample window, trade
  out-of-sample, and re-screen periodically. This codebase screens and
  backtests on the same window for clarity.
- **Execution realism**: costs here are a flat bps/turnover proxy; a
  production version should model bid-ask spread and market impact
  separately, especially for less liquid legs.
- **Portfolio level**: run the screener across sectors, allocate capital
  across the surviving pairs with a risk budget (e.g. equal risk
  contribution on each pair's OU-implied volatility), not equal notional.
