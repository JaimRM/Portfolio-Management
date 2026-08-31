"""Trading signal generation.

Position is defined on the SPREAD itself:
    +1  "long the spread"  -> long y,  short beta * x   (enter when z < -entry)
    -1  "short the spread" -> short y, long  beta * x   (enter when z > +entry)
     0  flat

Exit on reversion to the mean (|z| < exit_zscore) or on a hard stop
(|z| > stop_zscore), which protects against the cointegration relationship
itself breaking down -- the single biggest risk in stat-arb.

Implemented as an explicit state machine rather than a vectorized formula:
position transitions are path-dependent (you can't know today's position
without knowing yesterday's), so a loop is the correct and most readable
tool here. At daily/hourly bar counts this is O(n) and trivially fast;
for tick-level data, vectorize with numba.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import StrategyConfig


def generate_positions(zscore: pd.Series, cfg: StrategyConfig) -> pd.Series:
    z = zscore.to_numpy()
    n = len(z)
    pos = np.zeros(n)
    state = 0.0

    for i in range(n):
        zi = z[i]
        if np.isnan(zi):
            pos[i] = state
            continue

        if state == 0.0:
            if zi > cfg.entry_zscore:
                state = -1.0
            elif zi < -cfg.entry_zscore:
                state = 1.0
        else:
            if abs(zi) > cfg.stop_zscore:
                state = 0.0  # stop-loss: relationship likely broken
            elif state == 1.0 and zi >= -cfg.exit_zscore:
                state = 0.0  # reverted to mean, take profit
            elif state == -1.0 and zi <= cfg.exit_zscore:
                state = 0.0

        pos[i] = state

    return pd.Series(pos, index=zscore.index, name="position")
