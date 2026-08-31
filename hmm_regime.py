"""
hmm_regime.py
-------------
Gaussian HMM regime detection with WALK-FORWARD re-estimation to avoid
look-ahead bias. At each re-fit date, the model only sees data up to that
point in time; regime probabilities for the following block are produced
using the forward algorithm (filtered probabilities), never Viterbi on the
full sample.

v2: supports n_states=3 by default, separating:
    - trend_high_vol
    - trend_low_vol
    - range
instead of a single "trend" bucket. This matters because a 2-state model
conflates "am I trending" with "how volatile is it", which then gets
double-counted once position sizing ALSO scales by realized vol.

Mathematical core
------------------
Hidden state S_t in {0, ..., K-1} follows a first-order Markov chain:
    P(S_t = j | S_{t-1} = i) = A[i, j]        (transition matrix)
Observations (log return, realized vol) are emitted conditional on state:
    x_t | S_t = i  ~  N(mu_i, Sigma_i)         (Gaussian emission)
Parameters (A, mu, Sigma, pi_0) are estimated via Baum-Welch (EM).
Filtered state probabilities P(S_t | x_1:t) come from the forward pass.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

# hmmlearn logs a "Model is not converging" warning per EM fit; with dozens of
# walk-forward refits this floods stdout. It's informational, not an error
# (EM can plateau within n_iter on noisy FX data) — silenced here on purpose.
logging.getLogger("hmmlearn").setLevel(logging.ERROR)


@dataclass
class RegimeConfig:
    n_states: int = 3
    covariance_type: str = "full"
    n_iter: int = 200
    random_state: int = 42
    refit_every: int = 63          # re-estimate model every N trading days (~1 quarter)
    min_train_size: int = 252      # need at least 1yr of data before first fit
    feature_cols: tuple = ("log_ret", "realized_vol")


def _label_states(model: GaussianHMM, feature_cols: tuple) -> tuple[set, set, dict]:
    """
    Classify each hidden state as 'trend' or 'range', and (for 3+ states)
    split trend states into high-vol / low-vol sub-labels.

    Heuristic:
      1. Rank states by |mean log return| descending.
      2. For n_states == 2: the top state is 'trend', the other is 'range'.
      3. For n_states >= 3: all but the single least-directional state are
         'trend' states; among those, the one with higher mean realized_vol
         is 'trend_high_vol', the other(s) 'trend_low_vol'.

    Returns
    -------
    (trend_states, range_states, labels)
        trend_states / range_states : sets of state indices
        labels : dict[state_idx] -> str label, for readable reporting
    """
    ret_idx = feature_cols.index("log_ret")
    vol_idx = feature_cols.index("realized_vol") if "realized_vol" in feature_cols else None
    means_ret = model.means_[:, ret_idx]
    n_states = model.n_components

    order_by_return = np.argsort(-np.abs(means_ret))  # most directional first

    if n_states == 2:
        trend_states = {int(order_by_return[0])}
        range_states = {int(order_by_return[1])}
        labels = {int(order_by_return[0]): "trend", int(order_by_return[1]): "range"}
        return trend_states, range_states, labels

    n_trend = n_states - 1  # all but the least-directional state
    trend_states = set(int(x) for x in order_by_return[:n_trend])
    range_states = set(int(x) for x in order_by_return[n_trend:])

    labels = {s: "range" for s in range_states}
    if vol_idx is not None and len(trend_states) >= 2:
        trend_ranked_by_vol = sorted(trend_states, key=lambda s: model.means_[s, vol_idx], reverse=True)
        for i, s in enumerate(trend_ranked_by_vol):
            labels[s] = "trend_high_vol" if i == 0 else "trend_low_vol"
    else:
        for s in trend_states:
            labels[s] = "trend"

    return trend_states, range_states, labels


def walk_forward_regimes(df: pd.DataFrame, config: RegimeConfig = RegimeConfig()) -> pd.DataFrame:
    """
    Runs walk-forward HMM fitting and produces filtered P(trend) for every day,
    where P(trend) = sum of posterior probabilities over ALL trend-labeled states.

    On each re-fit date, fits a fresh GaussianHMM on all data up to t (expanding
    window), then scores the NEXT `refit_every` days using the forward algorithm.

    Returns
    -------
    df with added columns:
        p_trend       : P(trend_high_vol) + P(trend_low_vol), filtered
        regime        : 1 if hard-assigned state is a trend state, else 0
        regime_label  : readable label ('trend_high_vol', 'trend_low_vol', 'range')
        hmm_state     : raw hidden state index assigned by the model
    """
    X_full = df[list(config.feature_cols)].values
    n = len(df)

    p_trend = np.full(n, np.nan)
    regime_hard = np.full(n, np.nan)
    regime_label = np.array([""] * n, dtype=object)
    hmm_state = np.full(n, np.nan)

    start = config.min_train_size
    if start >= n:
        raise ValueError("Not enough data for min_train_size; shorten it or fetch more history.")

    i = start
    while i < n:
        train_end = i  # expanding window: train on [0, i)
        block_end = min(i + config.refit_every, n)

        X_train = X_full[:train_end]

        model = GaussianHMM(
            n_components=config.n_states,
            covariance_type=config.covariance_type,
            n_iter=config.n_iter,
            random_state=config.random_state,
        )
        model.fit(X_train)

        trend_states, range_states, labels = _label_states(model, config.feature_cols)

        X_scored = X_full[:block_end]
        probs = model.predict_proba(X_scored)
        hard = model.predict(X_scored)

        block_probs = probs[train_end:block_end]
        block_hard = hard[train_end:block_end]

        p_trend[train_end:block_end] = block_probs[:, list(trend_states)].sum(axis=1)
        regime_hard[train_end:block_end] = np.isin(block_hard, list(trend_states)).astype(int)
        hmm_state[train_end:block_end] = block_hard
        regime_label[train_end:block_end] = [labels[s] for s in block_hard]

        i = block_end

    out = df.copy()
    out["p_trend"] = p_trend
    out["regime"] = regime_hard
    out["regime_label"] = regime_label
    out["hmm_state"] = hmm_state
    out = out.dropna(subset=["p_trend"])
    return out


if __name__ == "__main__":
    from data_loader import load_fx_data

    df = load_fx_data("EURUSD=X", start="2015-01-01")
    regimes = walk_forward_regimes(df)
    print(regimes[["close", "log_ret", "realized_vol", "p_trend", "regime", "regime_label"]].tail(15))
    print("\nRegime label distribution:")
    print(regimes["regime_label"].value_counts(normalize=True))
