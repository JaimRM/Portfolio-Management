"""End-to-end example: screen a universe, pick the top pair, backtest it.

Run:
    python -m pairs_trading.main
"""

from __future__ import annotations

from . import (
    BacktestConfig,
    ScreeningConfig,
    StrategyConfig,
    compute_spread,
    fetch_close_prices,
    generate_positions,
    rolling_zscore,
    run_backtest,
    screen_pairs,
    test_cointegration,
)


def main() -> None:
    # Classic candidates for cointegration: same-sector, similar-beta names.
    universe = ["KO", "PEP", "GLD", "SLV", "XOM", "CVX"]
    prices = fetch_close_prices(universe, start="2019-01-01")

    screening_cfg = ScreeningConfig()
    candidates = screen_pairs(prices, screening_cfg)
    print("=== Cointegrated pairs found ===")
    print(candidates.to_string(index=False))

    if candidates.empty:
        print("No tradeable pairs at this significance level. Widen the universe or threshold.")
        return

    best = candidates.iloc[0]
    y_ticker, x_ticker = best["y"], best["x"]
    print(f"\n=== Backtesting best pair: {y_ticker} / {x_ticker} ===")

    y, x = prices[y_ticker], prices[x_ticker]
    coint_result = test_cointegration(y, x, significance=screening_cfg.significance_level)

    strategy_cfg = StrategyConfig()
    spread = compute_spread(y, x, coint_result.hedge_ratio, coint_result.intercept)
    zscore = rolling_zscore(spread, strategy_cfg.zscore_window)
    positions = generate_positions(zscore, strategy_cfg)

    backtest_cfg = BacktestConfig()
    result = run_backtest(
        price_y=y,
        price_x=x,
        hedge_ratio=coint_result.hedge_ratio,
        positions=positions,
        capital=backtest_cfg.capital,
        transaction_cost_bps=backtest_cfg.transaction_cost_bps,
        periods_per_year=backtest_cfg.periods_per_year,
    )

    print(result.summary())


if __name__ == "__main__":
    main()
