"""
data_loader.py
--------------
Fetches daily FX data and computes base features (log returns, realized vol).

Note: yfinance FX tickers use the format "EURUSD=X", "USDJPY=X".
"""

import numpy as np
import pandas as pd
import yfinance as yf


def load_fx_data(ticker: str, start: str = "2010-01-01", end: str | None = None,
                  vol_window: int = 10) -> pd.DataFrame:
    """
    Download daily FX data and compute log returns + realized volatility.

    Parameters
    ----------
    ticker : str
        Yahoo Finance FX ticker, e.g. "EURUSD=X", "USDJPY=X".
    start, end : str
        Date range (YYYY-MM-DD).
    vol_window : int
        Rolling window (in days) for realized volatility.

    Returns
    -------
    pd.DataFrame with columns: Close, log_ret, realized_vol
    """
    raw = yf.download(ticker, start=start, end=end, interval="1d", progress=False, auto_adjust=True)

    if raw.empty:
        raise ValueError(f"No data returned for {ticker}. Check ticker/date range/connection.")

    # yfinance sometimes returns MultiIndex columns for a single ticker
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = pd.DataFrame(index=raw.index)
    df["close"] = raw["Close"]
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    df["realized_vol"] = df["log_ret"].rolling(vol_window).std() * np.sqrt(252)

    df = df.dropna()
    return df


def load_multiple(tickers: list[str], start: str = "2010-01-01", end: str | None = None,
                   vol_window: int = 10) -> dict[str, pd.DataFrame]:
    """Convenience wrapper to load several pairs at once."""
    return {t: load_fx_data(t, start=start, end=end, vol_window=vol_window) for t in tickers}


if __name__ == "__main__":
    df = load_fx_data("EURUSD=X", start="2015-01-01")
    print(df.tail())
    print(f"\n{len(df)} rows loaded.")
