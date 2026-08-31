"""Configuration objects. Immutable dataclasses keep parameters explicit and
prevent accidental mutation mid-backtest."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScreeningConfig:
    """Parameters for scanning a universe and shortlisting tradeable pairs."""

    significance_level: float = 0.05   # Engle-Granger / ADF p-value threshold
    min_half_life_days: float = 1.0    # discard spreads that revert too fast (noise)
    max_half_life_days: float = 60.0   # discard spreads that revert too slowly (not tradeable)
    bonferroni_correction: bool = True  # correct for multiple comparisons across the universe


@dataclass(frozen=True)
class StrategyConfig:
    """Entry / exit / risk thresholds, expressed in z-score units."""

    zscore_window: int = 21            # rolling window for spread mean/std
    entry_zscore: float = 2.0          # open position when |z| exceeds this
    exit_zscore: float = 0.5           # close position when |z| reverts below this
    stop_zscore: float = 4.0           # hard stop: cointegration likely broken


@dataclass(frozen=True)
class BacktestConfig:
    capital: float = 1_000_000.0
    transaction_cost_bps: float = 5.0  # per leg, round-trip charged on position changes
    periods_per_year: int = 252
    hedge_ratio_window: Optional[int] = None  # None => static, full-sample OLS hedge ratio
