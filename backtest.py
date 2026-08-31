"""Backtest engine: turns (prices, hedge ratio, positions) into an equity
curve and standard risk/return metrics.

Key correctness details that matter at institutional grade:
  - Signal-to-fill lag: today's position is applied to TOMORROW's return
    (`.shift(1)`), so there is no look-ahead bias.
  - Dollar-neutral leg weights derived from the hedge ratio, so the
    strategy return is a true market-neutral spread return, not a raw
    price-difference return.
  - Transaction costs charged proportionally to position turnover on both
    legs, in basis points, every time the position changes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    trades: int
    total_return: float
    annualized_return: float
    annualized_vol: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float

    def summary(self) -> str:
        return (
            f"Total return:       {self.total_return:8.2%}\n"
            f"Annualized return:  {self.annualized_return:8.2%}\n"
            f"Annualized vol:     {self.annualized_vol:8.2%}\n"
            f"Sharpe ratio:       {self.sharpe_ratio:8.2f}\n"
            f"Max drawdown:       {self.max_drawdown:8.2%}\n"
            f"Win rate:           {self.win_rate:8.2%}\n"
            f"Trades:             {self.trades:8d}"
        )


def run_backtest(
    price_y: pd.Series,
    price_x: pd.Series,
    hedge_ratio: float,
    positions: pd.Series,
    capital: float = 1_000_000.0,
    transaction_cost_bps: float = 5.0,
    periods_per_year: int = 252,
) -> BacktestResult:
    df = pd.DataFrame({"y": price_y, "x": price_x, "pos": positions}).dropna()

    # Dollar-neutral leg weights: 1 share of y vs hedge_ratio shares of x,
    # normalized so gross exposure sums to 1.
    gross_notional = 1.0 + abs(hedge_ratio)
    w_y = 1.0 / gross_notional
    w_x = -hedge_ratio / gross_notional

    ret_y = df["y"].pct_change()
    ret_x = df["x"].pct_change()
    spread_return = w_y * ret_y + w_x * ret_x

    # Yesterday's position earns today's return -- avoids look-ahead bias.
    strategy_return = df["pos"].shift(1) * spread_return

    position_change = df["pos"].diff().abs().fillna(0.0)
    cost = position_change * (transaction_cost_bps / 10_000.0) * 2  # both legs
    strategy_return = strategy_return.fillna(0.0) - cost

    equity_curve = capital * (1.0 + strategy_return).cumprod()
    trades = int((position_change > 0).sum())

    n_periods = len(strategy_return)
    total_return = equity_curve.iloc[-1] / capital - 1.0
    annualized_return = (1.0 + total_return) ** (periods_per_year / n_periods) - 1.0
    annualized_vol = strategy_return.std() * np.sqrt(periods_per_year)
    sharpe = annualized_return / annualized_vol if annualized_vol > 0 else np.nan

    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    max_dd = float(drawdown.min())

    active = df["pos"].shift(1) != 0
    win_rate = float((strategy_return[active] > 0).mean()) if active.sum() > 0 else np.nan

    return BacktestResult(
        equity_curve=equity_curve,
        returns=strategy_return,
        trades=trades,
        total_return=float(total_return),
        annualized_return=float(annualized_return),
        annualized_vol=float(annualized_vol),
        sharpe_ratio=float(sharpe),
        max_drawdown=max_dd,
        win_rate=win_rate,
    )
