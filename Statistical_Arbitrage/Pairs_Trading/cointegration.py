"""Cointegration testing.

Two price series are cointegrated if a linear combination of them is
stationary, even though each series individually is a non-stationary I(1)
random walk. This is the statistical basis for pairs trading: a stationary
spread is mean-reverting by definition, which is what we trade.

Method: Engle-Granger two-step procedure.
    1. OLS regress y_t = alpha + beta * x_t + eps_t   -> hedge ratio (beta)
    2. Test residuals eps_t for a unit root (ADF). Stationary residuals
       => cointegrated pair.

We report both statsmodels' `coint` (which uses the correct Engle-Granger
critical values / MacKinnon p-values) and a direct ADF test on the OLS
residuals, and require both to agree before flagging a pair as tradeable.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint


@dataclass(frozen=True)
class CointegrationResult:
    ticker_y: str
    ticker_x: str
    eg_stat: float
    eg_pvalue: float
    hedge_ratio: float     # beta: shares of x per share of y in the spread
    intercept: float
    adf_stat_resid: float
    adf_pvalue_resid: float
    is_cointegrated: bool


def estimate_hedge_ratio(y: pd.Series, x: pd.Series) -> tuple[float, float]:
    """Static OLS hedge ratio: y = alpha + beta * x + eps. Returns (beta, alpha)."""
    x_const = sm.add_constant(x.values)
    model = sm.OLS(y.values, x_const).fit()
    intercept, beta = model.params
    return float(beta), float(intercept)


def test_cointegration(
    y: pd.Series,
    x: pd.Series,
    significance: float = 0.05,
) -> CointegrationResult:
    """Run the full Engle-Granger test on a pair of aligned price series."""
    eg_stat, eg_pvalue, _ = coint(y, x)

    beta, intercept = estimate_hedge_ratio(y, x)
    resid = y - beta * x - intercept
    adf_stat, adf_pvalue, *_ = adfuller(resid, autolag="AIC")

    is_coint = (eg_pvalue < significance) and (adf_pvalue < significance)

    return CointegrationResult(
        ticker_y=str(y.name),
        ticker_x=str(x.name),
        eg_stat=float(eg_stat),
        eg_pvalue=float(eg_pvalue),
        hedge_ratio=beta,
        intercept=intercept,
        adf_stat_resid=float(adf_stat),
        adf_pvalue_resid=float(adf_pvalue),
        is_cointegrated=is_coint,
    )
