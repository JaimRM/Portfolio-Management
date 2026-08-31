"""
main.py
-------
Runs the full regime-momentum pipeline for EUR/USD and USD/JPY:
  1. 3-state HMM regime detection (trend_high_vol / trend_low_vol / range)
  2. Momentum signal gated + sized by regime confidence
  3. Regime-conditional stop-loss
  4. Walk-forward hyperparameter grid search (diagnostic, printed to console
     and saved to CSV per pair)
  5. Final backtest run with the most frequently chosen walk-forward params

Prints a performance comparison table (strategy vs buy & hold) and saves a
chart with equity curves + regime shading.
"""

import matplotlib.pyplot as plt
import pandas as pd

from backtest import BacktestConfig, generate_signals, performance_summary, run_backtest
from data_loader import load_fx_data
from hmm_regime import RegimeConfig, walk_forward_regimes
from hyperparam_search import walk_forward_grid_search

TICKERS = {
    "EURUSD=X": "EUR/USD",
    "USDJPY=X": "USD/JPY",
}

START_DATE = "2012-01-01"
RUN_GRID_SEARCH = True   # set False to skip (grid search is the slowest step)


def run_pipeline(ticker: str, config: BacktestConfig) -> pd.DataFrame:
    df = load_fx_data(ticker, start=START_DATE)
    df = walk_forward_regimes(df, RegimeConfig())
    df = generate_signals(df, config)
    df = run_backtest(df, config)
    return df


def main():
    results = {}
    metrics_table = {}
    grid_summaries = {}

    for ticker, label in TICKERS.items():
        print(f"\n=== {label} ===")
        print("Fetching data + running walk-forward HMM regime detection...")
        raw = load_fx_data(ticker, start=START_DATE)
        regimes = walk_forward_regimes(raw, RegimeConfig())

        chosen_config = BacktestConfig()  # sensible defaults, used if grid search is skipped

        if RUN_GRID_SEARCH:
            print("Running walk-forward hyperparameter grid search...")
            folds = walk_forward_grid_search(regimes, base_config=BacktestConfig())
            grid_summaries[label] = folds
            folds.to_csv(f"grid_search_{label.replace('/', '')}.csv", index=False)

            if len(folds) > 0:
                best_mw = int(folds["best_momentum_window"].mode()[0])
                best_th = float(folds["best_p_trend_threshold"].mode()[0])
                mean_oos_sharpe = folds["oos_Sharpe"].mean()
                print(f"  Most frequently chosen: momentum_window={best_mw}, "
                      f"p_trend_threshold={best_th} | Mean OOS Sharpe across folds: {mean_oos_sharpe:.3f}")
                chosen_config = BacktestConfig(momentum_window=best_mw, p_trend_threshold=best_th)
            else:
                print("  Not enough data for walk-forward folds; using default params.")

        print(f"Running final backtest with momentum_window={chosen_config.momentum_window}, "
              f"p_trend_threshold={chosen_config.p_trend_threshold}...")
        signals = generate_signals(regimes, chosen_config)
        df = run_backtest(signals, chosen_config)
        results[label] = df

        strat = performance_summary(df["strategy_ret"])
        bh = performance_summary(df["log_ret"])
        metrics_table[f"{label} - Strategy"] = strat
        metrics_table[f"{label} - Buy&Hold"] = bh

        print(f"  Stopped out on {int(df['stopped_out'].sum())} bars "
              f"({df['stopped_out'].mean():.2%} of days)")
        print("  Regime distribution:")
        print(regimes["regime_label"].value_counts(normalize=True).to_string())

    summary = pd.DataFrame(metrics_table).T
    print("\n=== Performance Summary ===")
    print(summary.round(4).to_string())
    summary.to_csv("regime_momentum_summary.csv")

    # --- Plot: equity curves + regime shading for each pair ---
    fig, axes = plt.subplots(len(results), 1, figsize=(11, 5 * len(results)), sharex=False)
    if len(results) == 1:
        axes = [axes]

    for ax, (label, df) in zip(axes, results.items()):
        ax.plot(df.index, df["equity_curve"], label="Regime-Momentum Strategy", linewidth=1.6)
        ax.plot(df.index, df["buy_hold_curve"], label="Buy & Hold", linewidth=1.2, alpha=0.7)

        trend_mask = df["regime_label"].isin(["trend_high_vol", "trend_low_vol", "trend"])
        ax.fill_between(df.index, ax.get_ylim()[0], ax.get_ylim()[1],
                         where=trend_mask, alpha=0.08, color="green",
                         transform=ax.get_xaxis_transform(), label="Trend regime")

        stop_points = df.index[df["stopped_out"]]
        if len(stop_points) > 0:
            ax.scatter(stop_points, df.loc[stop_points, "equity_curve"],
                        color="red", s=10, zorder=5, label="Stopped out")

        ax.set_title(f"{label}: Regime-Momentum Strategy vs Buy & Hold")
        ax.set_ylabel("Growth of 1")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig("regime_momentum_results.png", dpi=150)
    print("\nSaved: regime_momentum_summary.csv, regime_momentum_results.png, "
          "grid_search_<PAIR>.csv per pair")


if __name__ == "__main__":
    main()
