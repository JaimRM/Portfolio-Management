# Transaction Cost Analysis (TCA) & Execution Algorithm Simulator

A C++17 simulator that models the core toolkit of an **Execution Quant**: simulate a
realistic trading day, work a large parent order through three execution algorithms
(TWAP, VWAP, Implementation Shortfall / Almgren-Chriss), and produce a full **Transaction
Cost Analysis** report comparing them on the standard industry benchmarks.

## Why this project

Execution desks don't decide *what* to trade — they decide *how* to trade it without
leaking cost to the market. This project builds the two things that role actually requires
day to day:

1. **Market microstructure modeling** — an intraday price/volume simulator with a
   realistic U-shaped volume profile and a square-root market impact model
   (temporary + permanent impact, Almgren-Chriss style).
2. **TCA benchmarking** — Implementation Shortfall (Perold, 1988), VWAP slippage,
   participation-rate tracking, and spread cost attribution, computed the way a real
   execution desk or TCA vendor (e.g. ITG, Virtu Analytics) would report them.

## Architecture

```
include/
  MarketTypes.hpp          Core data structures: Order, Fill, MarketBar, MarketDay
  MarketSimulator.hpp      GBM price path + U-shaped intraday volume profile
  MarketImpactModel.hpp    Square-root temporary/permanent impact model
  ExecutionAlgorithms.hpp  TWAP, VWAP, Implementation Shortfall (Almgren-Chriss)
  TCAEngine.hpp            Cost benchmarking: IS, VWAP slippage, participation, spread cost
  CsvWriter.hpp            Exports fills + summary report to CSV
src/
  main.cpp                 Runs all 3 algos against the same simulated day, prints + exports report
```

## Algorithms implemented

- **TWAP** — splits the order into equal-sized slices across the horizon. Simple,
  ignores real liquidity, used as the naive baseline.
- **VWAP** — slices proportionally to each bar's share of expected volume, keeping
  the order's own participation rate roughly flat and tracking the market benchmark.
- **Implementation Shortfall (Almgren-Chriss)** — solves the closed-form optimal
  trajectory `x(t) = X · sinh(κ(T−t)) / sinh(κT)` that trades off market impact cost
  against timing (volatility) risk via a risk-aversion parameter λ. Higher λ trades
  faster and accepts more impact to reduce exposure to adverse price moves.

## TCA metrics reported

- **Implementation Shortfall (bps & $)** vs. arrival price — the industry-standard
  execution cost measure (Perold 1988).
- **VWAP slippage (bps)** — execution price vs. the realized interval market VWAP.
- **Average / peak participation rate** — % of each bar's volume consumed, a proxy
  for how much market impact and information leakage the order caused.
- **Effective spread cost (bps)** — cost attributable purely to crossing the bid-ask.

## Build & run

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Iinclude src/main.cpp -o tca_sim
./tca_sim
```

Outputs:
- Console comparison table across the three algorithms.
- `output/tca_summary.csv` — one row per algorithm with all TCA metrics.
- `output/fills_<algo>.csv` — full fill-by-fill execution trajectory per algorithm.

## Example result (500k share buy order, 10% of ADV, seed=42)

| Algorithm | Avg Price | IS (bps) | VWAP Slippage (bps) | Avg Participation |
|---|---|---|---|---|
| TWAP | 100.37 | 42.3 | 74.2 | 11.7% |
| VWAP | 100.24 | 30.1 | 61.9 | 10.0% |
| Implementation Shortfall | 100.35 | 40.3 | 72.1 | 11.0% |

VWAP wins on cost here because it tracks the venue's own liquidity profile; IS trades
faster than VWAP early in the session to reduce timing risk, accepting a bit more impact
cost than VWAP but less than naive TWAP.

## Possible extensions

- Replace the synthetic GBM simulator with real tick data (e.g. LOBSTER, Polygon.io).
- Add a POV (Percentage of Volume) algorithm and an adaptive/Almgren-Chriss-with-real-time
  re-optimization variant.
- Model queue position / partial fills against a real limit order book instead of a
  reduced-form impact model.
- Add pre-trade cost estimation (predicting IS before execution) vs. post-trade TCA.
