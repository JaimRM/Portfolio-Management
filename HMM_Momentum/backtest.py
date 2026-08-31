"""
backtest.py
-----------
Momentum signal conditioned on HMM regime probability, volatility-targeted
position sizing, a REGIME-CONDITIONAL STOP-LOSS, and a backtest with standard
risk/performance metrics (Sharpe, Sortino, max drawdown, Calmar).

Position sizing
----------------
    raw_size_t   = target_vol / realized_vol_t
    size_t       = clip(raw_size_t, 0, max_leverage) * p_trend_t * sign(momentum_t)

This scales exposure DOWN when: (a) realized vol is high (vol targeting), and
(b) the HMM is unsure we're in a trending regime (regime confidence scaling).

Regime-conditional stop-loss
------------------------------
A fixed-% stop-loss is the wrong tool here because "how much adverse move is
tolerable" genuinely depends on the regime you're trading in:
  - trend_high_vol : wide stop (a 2% pullback is noise inside a strong trend)
  - trend_low_vol   : tighter stop (the same 2% pullback is a bigger signal
                       that the trend may be exhausted)
  - range           : any open position is force-closed immediately — the
                       model no longer believes there IS a trend to ride
The stop level is expressed as a multiple of the realized volatility AT ENTRY
(daily-scaled), tracked against cumulative unrealized log-return since entry.
This is a sequential (path-dependent) rule, so it's implemented as a single
pass over the series rather than a pure vector op — still O(n).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    momentum_window: int = 20        # lookback for momentum sign, in days
    p_trend_threshold: float = 0.55  # only trade if P(trend) exceeds this
    target_vol: float = 0.10         # annualized vol target for the position
    max_leverage: float = 3.0
    cost_bps: float = 1.0            # round-trip cost in bps per unit of turnover
    trading_days: int = 252

    # --- regime-conditional stop-loss ---
    use_stop_loss: bool = True
    stop_mult_trend_high_vol: float = 3.0   # widest stop: give the trend room
    stop_mult_trend_low_vol: float = 1.75   # tighter: same move means more in a quiet regime
    stop_mult_trend_default: float = 2.25   # used for a plain 2-state 'trend' label
    exit_immediately_on_range: bool = True  # force flat the instant regime -> range


def generate_signals(df: pd.DataFrame, config: BacktestConfig = BacktestConfig()) -> pd.DataFrame:
    """
    Requires df to already contain 'p_trend' and 'regime_label'
    (from hmm_regime.walk_forward_regimes) plus 'log_ret' and 'realized_vol'.
    """
    out = df.copy()

    # Momentum direction: sign of cumulative log return over the lookback window
    momentum = out["log_ret"].rolling(config.momentum_window).sum()
    direction = np.sign(momentum)

    # Only take a position when the regime model is confident we're trending
    trend_gate = (out["p_trend"] >= config.p_trend_threshold).astype(float)

    raw_size = config.target_vol / out["realized_vol"].replace(0, np.nan)
    size = raw_size.clip(upper=config.max_leverage) * out["p_trend"] * trend_gate

    out["direction"] = direction
    out["position_raw"] = (size * direction).fillna(0.0)
    out = out.dropna(subset=["position_raw"])
    return out


def apply_regime_stop_loss(df: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """
    Sequential pass that overrides 'position_raw' with a stop-adjusted
    'position' column. If use_stop_loss is False, 'position' == 'position_raw'.
    """
    out = df.copy()

    if not config.use_stop_loss:
        out["position"] = out["position_raw"]
        out["stopped_out"] = False
        return out

    desired = out["position_raw"].values
    ret = out["log_ret"].values
    vol = out["realized_vol"].values
    labels = out["regime_label"].values if "regime_label" in out.columns else np.array(["trend"] * len(out))

    n = len(out)
    final_pos = np.zeros(n)
    stopped_out = np.zeros(n, dtype=bool)

    current_pos = 0.0
    unrealized = 0.0          # cumulative log-return since entry, approx (same-day proxy)
    entry_vol = np.nan        # realized vol at the moment the trade was opened

    stop_mult_map = {
        "trend_high_vol": config.stop_mult_trend_high_vol,
        "trend_low_vol": config.stop_mult_trend_low_vol,
        "trend": config.stop_mult_trend_default,
    }

    for t in range(n):
        label = labels[t]
        target = desired[t]

        if current_pos != 0.0:
            # mark-to-market the open trade using today's return
            unrealized += current_pos * ret[t]

            force_flat = False
            if config.exit_immediately_on_range and label == "range":
                force_flat = True
            else:
                mult = stop_mult_map.get(label, config.stop_mult_trend_default)
                daily_vol = entry_vol / np.sqrt(config.trading_days) if entry_vol and entry_vol > 0 else np.nan
                stop_level = -mult * daily_vol if not np.isnan(daily_vol) else -np.inf
                if unrealized <= stop_level:
                    force_flat = True

            if force_flat:
                current_pos = 0.0
                unrealized = 0.0
                entry_vol = np.nan
                stopped_out[t] = True
                final_pos[t] = 0.0
                continue

        # no active stop triggered this bar -> follow the signal
        if target == 0.0:
            current_pos = 0.0
            unrealized = 0.0
            entry_vol = np.nan
        elif current_pos == 0.0:
            # fresh entry
            current_pos = target
            unrealized = 0.0
            entry_vol = vol[t] if not np.isnan(vol[t]) else np.nan
        else:
            # already holding in the same direction: allow sizing to update,
            # but keep the running unrealized P&L and original entry_vol
            current_pos = target

        final_pos[t] = current_pos

    out["position"] = final_pos
    out["stopped_out"] = stopped_out
    return out


def run_backtest(df: pd.DataFrame, config: BacktestConfig = BacktestConfig()) -> pd.DataFrame:
    """
    Backtest. Position at time t is applied to the return realized from
    t to t+1 (i.e. we trade on the close, avoiding look-ahead: signal at t
    uses info up to t, return credited is the NEXT day's return).
    """
    out = apply_regime_stop_loss(df, config)
    out["position_lag"] = out["position"].shift(1).fillna(0.0)  # avoid same-bar lookahead

    strategy_ret = out["position_lag"] * out["log_ret"]

    turnover = out["position_lag"].diff().abs().fillna(out["position_lag"].abs())
    costs = turnover * (config.cost_bps / 10_000)

    out["strategy_ret"] = strategy_ret - costs
    out["equity_curve"] = np.exp(out["strategy_ret"].cumsum())
    out["buy_hold_curve"] = np.exp(out["log_ret"].cumsum())

    return out


def performance_summary(returns: pd.Series, trading_days: int = 252) -> dict:
    """Standard performance metrics on a daily log-return series."""
    returns = returns.dropna()
    ann_ret = returns.mean() * trading_days
    ann_vol = returns.std() * np.sqrt(trading_days)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan

    downside = returns[returns < 0]
    downside_vol = downside.std() * np.sqrt(trading_days) if len(downside) > 0 else np.nan
    sortino = ann_ret / downside_vol if downside_vol and downside_vol > 0 else np.nan

    equity = np.exp(returns.cumsum())
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_dd = drawdown.min()

    calmar = ann_ret / abs(max_dd) if max_dd < 0 else np.nan

    return {
        "Annualized Return": ann_ret,
        "Annualized Vol": ann_vol,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Max Drawdown": max_dd,
        "Calmar": calmar,
        "Hit Rate": (returns > 0).mean(),
    }


if __name__ == "__main__":
    from data_loader import load_fx_data
    from hmm_regime import walk_forward_regimes

    df = load_fx_data("EURUSD=X", start="2015-01-01")
    df = walk_forward_regimes(df)
    df = generate_signals(df)
    df = run_backtest(df)

    strat_metrics = performance_summary(df["strategy_ret"])
    bh_metrics = performance_summary(df["log_ret"])

    print("--- Strategy (with regime-conditional stop-loss) ---")
    for k, v in strat_metrics.items():
        print(f"{k}: {v:.4f}")
    print(f"Bars stopped out: {int(df['stopped_out'].sum())} ({df['stopped_out'].mean():.2%})")

    print("\n--- Buy & Hold ---")
    for k, v in bh_metrics.items():
        print(f"{k}: {v:.4f}")
