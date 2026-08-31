"""Scan a universe of price series for statistically tradeable pairs."""

from __future__ import annotations

import itertools

import pandas as pd

from .cointegration import test_cointegration
from .config import ScreeningConfig
from .spread_analysis import compute_spread, estimate_ou_parameters


def screen_pairs(prices: pd.DataFrame, cfg: ScreeningConfig) -> pd.DataFrame:
    """Test every ticker combination in `prices` and rank the survivors.

    A pair passes if it is cointegrated at `cfg.significance_level` AND its
    OU half-life falls inside [min_half_life_days, max_half_life_days] --
    too fast to trade profitably net of costs, too slow to be capital
    efficient, are both filtered out.

    IMPORTANT -- multiple testing: screening N tickers means testing
    N*(N-1)/2 pairs simultaneously. At a flat 5% significance level, a
    universe of just 10 tickers (45 pairs) has a high probability of at
    least one spurious "cointegrated" pair purely by chance, even among
    unrelated random walks. With `bonferroni_correction=True` (default),
    the effective significance threshold is divided by the number of
    pairs tested, which is the standard conservative correction. This
    reduces false positives but is not a substitute for requiring an
    economic rationale (same sector, shared risk factors, a share class
    relationship, etc.) before trusting a statistical pair.
    """
    tickers = list(prices.columns)
    pairs = list(itertools.combinations(tickers, 2))
    n_tests = max(len(pairs), 1)
    effective_significance = cfg.significance_level / n_tests if cfg.bonferroni_correction else cfg.significance_level

    rows = []
    for y_ticker, x_ticker in pairs:
        y, x = prices[y_ticker], prices[x_ticker]

        result = test_cointegration(y, x, significance=effective_significance)
        if not result.is_cointegrated:
            continue

        spread = compute_spread(y, x, result.hedge_ratio, result.intercept)
        ou = estimate_ou_parameters(spread)
        if not (cfg.min_half_life_days <= ou.half_life <= cfg.max_half_life_days):
            continue

        rows.append(
            {
                "pair": f"{y_ticker}/{x_ticker}",
                "y": y_ticker,
                "x": x_ticker,
                "eg_pvalue": result.eg_pvalue,
                "adf_pvalue_resid": result.adf_pvalue_resid,
                "hedge_ratio": result.hedge_ratio,
                "half_life_days": ou.half_life,
                "theta": ou.theta,
            }
        )

    columns = ["pair", "y", "x", "eg_pvalue", "adf_pvalue_resid", "hedge_ratio", "half_life_days", "theta"]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values("eg_pvalue").reset_index(drop=True)
