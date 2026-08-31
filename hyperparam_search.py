"""
hyperparam_search.py
---------------------
Walk-forward grid search over (momentum_window, p_trend_threshold).

Design: HMM regime detection (walk_forward_regimes) is run ONCE up front —
it doesn't depend on these two hyperparameters, so re-running it inside the
grid search would just waste time re-fitting the same models. Only signal
generation + backtest are re-run per parameter combo.

Validation scheme (walk-forward, not k-fold):
  Fold 1: train on [0, T0)          -> pick best params by in-sample Sharpe
          test on  [T0, T0+step)    -> apply those params out-of-sample
  Fold 2: train on [0, T0+step)     -> re-pick best params
          test on  [T0+step, T0+2*step)
  ... expanding window, fixed-size OOS test blocks.

This mirrors the refit-cadence optimization already used in the BTC/Gold
ARIMA/GARCH pipeline: parameters are re-selected periodically using only
information available up to that point, and every OOS metric reported is
genuinely out-of-sample.
"""

from dataclasses import replace
from itertools import product

import numpy as np
import pandas as pd

from backtest import BacktestConfig, generate_signals, performance_summary, run_backtest

DEFAULT_GRID = {
    "momentum_window": [10, 20, 30, 40],
    "p_trend_threshold": [0.50, 0.55, 0.60, 0.65, 0.70],
}


def _sharpe_for_params(df_slice: pd.DataFrame, momentum_window: int, p_trend_threshold: float,
                        base_config: BacktestConfig) -> float:
    cfg = replace(base_config, momentum_window=momentum_window, p_trend_threshold=p_trend_threshold)
    try:
        sig = generate_signals(df_slice, cfg)
        bt = run_backtest(sig, cfg)
        metrics = performance_summary(bt["strategy_ret"])
        return metrics["Sharpe"] if not np.isnan(metrics["Sharpe"]) else -np.inf
    except Exception:
        return -np.inf


def walk_forward_grid_search(df: pd.DataFrame,
                              grid: dict = DEFAULT_GRID,
                              base_config: BacktestConfig = BacktestConfig(),
                              min_train_size: int = 500,
                              test_size: int = 252) -> pd.DataFrame:
    """
    df must already contain 'p_trend' and 'regime_label' (output of
    hmm_regime.walk_forward_regimes) so the same regime path is reused
    across every parameter combination and every fold.

    Returns a DataFrame, one row per fold, with the chosen params and the
    resulting OUT-OF-SAMPLE performance metrics.
    """
    n = len(df)
    combos = list(product(grid["momentum_window"], grid["p_trend_threshold"]))

    if min_train_size >= n:
        raise ValueError("min_train_size exceeds available data length.")

    fold_results = []
    train_end = min_train_size

    while train_end + 1 < n:
        test_end = min(train_end + test_size, n)

        train_slice = df.iloc[:train_end]

        # 1. Select best params on the training slice (in-sample Sharpe)
        scores = {
            (mw, th): _sharpe_for_params(train_slice, mw, th, base_config)
            for mw, th in combos
        }
        best_params = max(scores, key=scores.get)
        best_mw, best_th = best_params

        # 2. Apply those params OUT-OF-SAMPLE on the test slice.
        #    Signals need the momentum rolling window's warm-up, so we pass
        #    everything up to test_end and only score the test_end tail.
        eval_slice = df.iloc[:test_end]
        cfg = replace(base_config, momentum_window=best_mw, p_trend_threshold=best_th)
        sig = generate_signals(eval_slice, cfg)
        bt = run_backtest(sig, cfg)

        oos_mask = bt.index >= df.index[train_end]
        oos_returns = bt.loc[oos_mask, "strategy_ret"]
        oos_metrics = performance_summary(oos_returns)

        fold_results.append({
            "fold_start": df.index[train_end],
            "fold_end": df.index[test_end - 1],
            "best_momentum_window": best_mw,
            "best_p_trend_threshold": best_th,
            "in_sample_sharpe": scores[best_params],
            **{f"oos_{k}": v for k, v in oos_metrics.items()},
        })

        train_end = test_end

    return pd.DataFrame(fold_results)


def full_sample_heatmap(df: pd.DataFrame, grid: dict = DEFAULT_GRID,
                         base_config: BacktestConfig = BacktestConfig()) -> pd.DataFrame:
    """
    Diagnostic only (NOT walk-forward, has look-ahead in parameter choice):
    Sharpe for every (momentum_window, p_trend_threshold) combo on the FULL
    sample. Useful to sanity-check the grid range and spot flat/unstable
    regions, but never use this to pick a single 'final' parameter set.
    """
    rows = []
    for mw, th in product(grid["momentum_window"], grid["p_trend_threshold"]):
        sharpe = _sharpe_for_params(df, mw, th, base_config)
        rows.append({"momentum_window": mw, "p_trend_threshold": th, "sharpe": sharpe})
    table = pd.DataFrame(rows)
    return table.pivot(index="momentum_window", columns="p_trend_threshold", values="sharpe")


if __name__ == "__main__":
    from data_loader import load_fx_data
    from hmm_regime import walk_forward_regimes

    df = load_fx_data("EURUSD=X", start="2012-01-01")
    df = walk_forward_regimes(df)

    print("Full-sample Sharpe heatmap (diagnostic only, has look-ahead):")
    print(full_sample_heatmap(df).round(3))

    print("\nWalk-forward grid search (genuinely out-of-sample):")
    folds = walk_forward_grid_search(df)
    print(folds.round(4).to_string(index=False))

    print(f"\nMean OOS Sharpe across folds: {folds['oos_Sharpe'].mean():.4f}")
    print(f"Most frequently chosen params: "
          f"momentum_window={folds['best_momentum_window'].mode()[0]}, "
          f"p_trend_threshold={folds['best_p_trend_threshold'].mode()[0]}")
