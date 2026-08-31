# Regime-Based Momentum Strategy — FX Majors

A Hidden Markov Model (HMM) classifies major FX pairs (EUR/USD, USD/JPY) into
latent market regimes in real time; a momentum signal is then gated, sized,
and stopped-out based on the model's regime read.

## Method

### 1. Regime detection (`hmm_regime.py`) — 3-state HMM

A **3-state** Gaussian HMM is fit on `(log return, realized volatility)`,
separating:

- `trend_high_vol` — directional, volatile
- `trend_low_vol` — directional, quiet
- `range` — non-directional

A 2-state model conflates "am I trending" with "how volatile is it," which
then gets double-counted once position sizing *also* scales by realized vol.
Separating them lets the strategy size a calm trend and a volatile trend
differently rather than treating "trend" as one bucket.

- Transition matrix `A`: `P(S_t = j | S_{t-1} = i)`
- Emissions: `x_t | S_t = i ~ N(mu_i, Sigma_i)`
- Parameters estimated via Baum-Welch (EM); state probabilities via the
  forward algorithm (filtered, not smoothed — no future data used).
- **Walk-forward re-estimation**: refit every ~63 trading days on an
  expanding window, so no future data leaks into past regime calls.
- State labels are assigned automatically each refit by ranking states on
  `|mean return|` (trend vs range) and then `mean realized_vol` (high vs low
  vol among the trend states) — not hardcoded to a fixed state index, since
  which index means what can shift between refits.

### 2. Signal, sizing & regime-conditional stop-loss (`backtest.py`)

- Momentum direction: sign of cumulative log return over a lookback window.
- Trade only when `P(trend_high_vol) + P(trend_low_vol) >= p_trend_threshold`.
- Size = `clip(target_vol / realized_vol, 0, max_leverage) * P(trend)`.
- **Stop-loss is regime-conditional, not a fixed percentage**:
  - `range` → any open position is closed immediately — the model no longer
    believes there's a trend to ride.
  - `trend_high_vol` → wide stop (a pullback is more likely just noise inside
    a strong, volatile trend).
  - `trend_low_vol` → tighter stop (the same-sized pullback is a bigger
    relative signal that a quiet trend may be exhausted).
  - Stop level = a multiple of realized volatility **at entry** (daily-scaled),
    checked against cumulative unrealized log-return since entry. This is a
    sequential/path-dependent rule (implemented as a single pass, not a
    vector op).
- Transaction costs charged in bps of turnover.

### 3. Walk-forward hyperparameter search (`hyperparam_search.py`)

Grid search over `momentum_window x p_trend_threshold`, validated the same
way as the refit-cadence optimization in the BTC/Gold ARIMA/GARCH pipeline:

- Expanding training window, fixed-size out-of-sample test block per fold.
- Best params picked by **in-sample** Sharpe on the training slice only.
- Those params are then applied to the **next, unseen** test block and
  scored out-of-sample — every reported OOS metric is genuinely OOS.
- A `full_sample_heatmap()` helper is included too, but it's explicitly
  labeled diagnostic-only (it has look-ahead in the parameter choice) — useful
  for sanity-checking the grid range, never for picking a "final" parameter.

`main.py` runs this search per pair, then re-runs the final backtest using
the most frequently chosen parameters across folds (a simple, defensible way
to pick one parameter set from a walk-forward study without cherry-picking
the single best fold).

## Usage

```bash
pip install -r requirements.txt
python main.py
```

Set `RUN_GRID_SEARCH = False` in `main.py` for a faster run using default
parameters — the grid search is the slowest step (multiple HMM-free but
repeated backtests per fold).

Outputs:
- `regime_momentum_summary.csv` — strategy vs buy & hold metrics, both pairs
- `regime_momentum_results.png` — equity curves, regime shading, stop-out markers
- `grid_search_EURUSD.csv`, `grid_search_USDJPY.csv` — per-fold walk-forward results

## Known limitations / next steps

- The stop-loss's mark-to-market uses a same-day return proxy
  (`current_pos * ret[t]`) rather than the same t→t+1 execution lag used for
  the rest of the backtest. This is a standard simplification for risk
  control (react same-day, execute same-day) but means the stop-loss P&L
  tracking and the accounted strategy return aren't on identical timing —
  worth tightening if this becomes an execution-relevant deliverable rather
  than a research prototype.
- Grid search currently optimizes two parameters (`momentum_window`,
  `p_trend_threshold`); the stop-loss multipliers themselves are not yet part
  of the search space.
- HMM state count is fixed at 3; a model-selection step (BIC/AIC across
  n_states) would make that choice data-driven rather than assumed.
