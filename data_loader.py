"""Price data loader. Wraps yfinance; swap this module out for a Bloomberg
BQL or internal data warehouse call in production without touching the
rest of the pipeline."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_close_prices(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """Download adjusted close prices for `tickers` and return a clean,
    aligned wide DataFrame (columns = tickers, forward-filled, no gaps)."""
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    prices = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(
        columns={"Close": tickers[0]}
    )
    prices = prices.dropna(how="all").ffill().dropna()
    return prices
