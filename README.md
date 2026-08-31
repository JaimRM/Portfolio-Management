A collection of production-grade quantitative trading strategies, financial engineering models, and market microstructure simulators.


Some of my core projects:

### 1. [Transaction Cost Analysis (TCA) & Execution Simulator](./TCA) (C++20)
An institutional-grade intraday simulator to model market microstructure and optimize algorithmic execution.
* **Microstructure Model:** Geometric Brownian Motion (GBM) price paths coupled with a **U-shaped intraday volume profile** and an Almgren-Chriss square-root market impact model (temporary vs. permanent impact decay).
* **Algorithms Implemented:** Naive TWAP, Volume-Tracking VWAP, and **Implementation Shortfall (Almgren-Chriss closed-form optimal trajectory)** trading off timing risk ($\lambda$) against slippage.
* **Metrics:** Implementation Shortfall (Perold 1988) vs. arrival price, VWAP slippage in bps, and peak participation-rate tracking.

### 2. [Regime-Based Momentum Strategy — FX Majors](./HMM_Momentum_FX) (Python)
A systematic FX trading strategy gated by a **3-State Gaussian Hidden Markov Model (HMM)** to decouple structural trends from volatility states.
* **Mathematical Framework:** Baum-Welch (EM) parameter estimation and Forward Algorithm filtering (zero look-ahead bias). Walk-forward expanding windows refitted every 63 trading days.
* **Risk Management:** Dynamic, regime-conditional stop-losses scaled by daily realized volatility. Regime transitions instantly trigger position-sizing adjustments (Trend High Vol vs. Trend Low Vol vs. Mean-Reverting Range).

### 3. [Statistical Arbitrage & Pairs Trading Engine](./Statistical_Arbitrage) (Python)
An end-to-end framework applying cointegration and time-series econometrics to equity pairs.
* **Methodology:** Two-step Engle-Granger cointegration procedure, Augmented Dickey-Fuller (ADF) testing, and **Ornstein-Uhlenbeck (OU) stochastic process** parameter fitting for precise mean-reversion speed modeling.
* **Statistical Rigor:** Implements **Bonferroni corrections** to control family-wise error rates during multi-pair mining, backed by out-of-sample walk-forward testing.

### 4. [Delta-Hedging Options Pricer & Simulator](./DeltaHedging_Options_Pricer) (Python & Streamlit)
A derivatives pricing suite featuring cross-method valuation and dynamic risk replication tracking.
* **Pricing Engines:** Analytical Black-Scholes-Merton, Binomial Trees for American options, and Monte Carlo paths for exotic structures.
* **Dynamic Hedging:** A continuous simulation layer that tracks real-time Greek sensitivities ($\Delta, \Gamma, \ Vega, \Theta$), calculating path-dependent P&L leakage during discrete rebalancing under volatile regimes.

---

## 💻 Tech Stack & Tooling
* **Languages:** C++20 (STL, High-Performance Structs), Python (3.14+), VBA (Excel)
* **Libraries:** NumPy, Pandas, SciPy, Scikit-Learn, Statsmodels, Streamlit
* **Data Pipelines:** SQL (Data Queries/Aggregation), Bloomberg BQL Integration


**(https://www.linkedin.com/in/jaime-ruiz-marín-09a05127b/)**

Contacto/Contact info:
**📫 jaimeruiz018@gmail.com**
