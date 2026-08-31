"""Spread construction and Ornstein-Uhlenbeck (OU) mean-reversion dynamics.

The spread S_t = y_t - beta * x_t - alpha is modelled as an OU process:

    dS_t = theta * (mu - S_t) * dt + sigma * dW_t

which has a well-known exact discretization. We estimate it via the
Euler-Maruyama-consistent AR(1) regression:

    S_t - S_{t-1} = a + b * S_{t-1} + eps_t

with b = -theta * dt  =>  theta = -b / dt
     a =  theta * mu * dt  =>  mu = -a / b

theta > 0 is required for genuine mean reversion. The half-life,
ln(2) / theta, is the expected number of periods for the spread to close
half the distance back to its long-run mean -- it is the natural holding
period / lookback-window scale for the strategy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True)
class OUParameters:
    theta: float        # speed of mean reversion
    mu: float            # long-run equilibrium level of the spread
    sigma: float          # instantaneous volatility (diffusion coefficient)
    half_life: float       # ln(2) / theta, in periods (e.g. trading days)


def compute_spread(
    y: pd.Series,
    x: pd.Series,
    hedge_ratio: float,
    intercept: float = 0.0,
) -> pd.Series:
    spread = y - hedge_ratio * x - intercept
    spread.name = "spread"
    return spread


def rolling_zscore(spread: pd.Series, window: int) -> pd.Series:
    """Standardize the spread against its own trailing rolling statistics.

    Using a rolling (not full-sample) window keeps the signal reactive to
    regime shifts and avoids look-ahead bias in a walk-forward backtest.
    """
    mean = spread.rolling(window).mean()
    std = spread.rolling(window).std()
    z = (spread - mean) / std
    z.name = "zscore"
    return z


def estimate_ou_parameters(spread: pd.Series, dt: float = 1.0) -> OUParameters:
    """Fit OU parameters to a spread series via AR(1) regression.

    Returns theta=0.0 and half_life=inf if no significant mean reversion
    is detected (b >= 0), signalling the pair should be filtered out.
    """
    s_lag = spread.shift(1).dropna()
    s_now = spread.loc[s_lag.index]
    delta = s_now - s_lag

    x_const = sm.add_constant(s_lag.values)
    model = sm.OLS(delta.values, x_const).fit()
    a, b = model.params

    if b >= 0:
        return OUParameters(
            theta=0.0,
            mu=float(spread.mean()),
            sigma=float(spread.std()),
            half_life=np.inf,
        )

    theta = -b / dt
    mu = -a / b
    resid_std = float(np.std(model.resid))
    # Stationary-variance-consistent diffusion coefficient for the OU SDE.
    sigma = resid_std * np.sqrt(2 * theta / (1 - np.exp(-2 * theta * dt)))
    half_life = float(np.log(2) / theta)

    return OUParameters(theta=float(theta), mu=float(mu), sigma=float(sigma), half_life=half_life)
