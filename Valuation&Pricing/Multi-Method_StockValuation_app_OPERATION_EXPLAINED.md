# Weighted stock valuation app

Blends **six independent valuation methods** into a **single target price**,
**weighted however you want**.

## Methods included
- **DCF** — 5-year FCF projection + terminal value (Gordon terminal growth), discounted at CAPM cost of equity
- **Multiples** — P/E, EV/EBITDA, P/S implied prices, averaged
- **Gordon Growth** — dividend discount model (only runs for dividend payers)
- **Asset-Based** — book value per share (floor valuation)
- **Monte Carlo** — Geometric Brownian Motion (GBM) simulation of the price distribution N days out, with median as point estimate
- **ARIMA + GARCH** — ARIMA(1,0,1) forecasts the conditional mean of daily log returns over the horizon; GARCH(1,1) forecasts the conditional variance combined into a point estimate + ~80% confidence band


ARX and VAR were deliberately left out. The prior BTC/Gold walk-forward backtest found neither added meaningful accuracy over plain ARIMA/GARCH. VAR, in particular, is built for capturing co-dependency between multiple series, and doesn't map cleanly onto a single-stock target price. If you later want to test ARX with a specific exogenous regressor (e.g. sector ETF, rates), it is in the "Predictive_Models" folder.


## Structure
```
data_fetcher.py       # pulls raw inputs from yfinance into one dictionary
valuation_methods.py  # 6 independent methods, MethodResult interface
blending_engine.py    # normalizes weights across applicable methods, computes blended price
app.py                # Streamlit UI: ticker input, weight sliders, chart, output
```

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py
```

NEXT:

Type a ticker, hit "Run valuation," and you get sliders per method, a bar chart comparing each method's implied price against your blended target and the current market price, plus the Monte Carlo and GARCH confidence bands.


## A few design choices worth flagging:

If a method is inapplicable (e.g. Gordon Growth on a non-dividend payer), it's automatically excluded, and weights are re-normalized across the rest — so you never accidentally zero out your target price.

DCF and Gordon Growth default to CAPM for the discount rate (using the ticker's beta), but you can override growth assumptions from the sidebar.

The spread stat (min/max/std across active methods) is shown alongside the target. That dispersion is more informative than the point estimate itself when methods disagree a lot.
