#pragma once
#include <vector>
#include <string>
#include <cstdint>

namespace tca {

enum class Side { Buy, Sell };

inline double sideSign(Side s) { return s == Side::Buy ? 1.0 : -1.0; }

inline std::string sideToString(Side s) { return s == Side::Buy ? "BUY" : "SELL"; }

// One bar of simulated intraday market data (e.g. 1-minute bar).
struct MarketBar {
    int timeIndex;      // minute index from market open, 0-based
    double midPrice;    // mid price at this bar
    double bidAskSpread;// quoted spread in price units
    double marketVolume;// total market volume traded during this bar (shares)
    double volatility;  // realized per-bar volatility (sigma), for impact modeling
};

// A single simulated market day.
struct MarketDay {
    std::vector<MarketBar> bars;
    double totalVolume = 0.0;
    int numBars() const { return static_cast<int>(bars.size()); }
};

// Parent order to be executed by an algorithm over the trading horizon.
struct ParentOrder {
    std::string symbol;
    Side side;
    double totalQuantity;   // shares to execute
    int startBar;            // inclusive
    int endBar;               // inclusive
    double arrivalPrice;    // mid price at decision time (t0), set by caller
};

// A single child fill produced by an execution algorithm.
struct Fill {
    int timeIndex;
    double quantity;
    double price;         // effective execution price (incl. spread + impact)
    double marketVolume;  // market volume in that bar, for participation calc
};

// Full execution trajectory (list of fills) produced by an algorithm run.
struct ExecutionResult {
    std::string algoName;
    std::vector<Fill> fills;
    double totalQuantityFilled = 0.0;
    double avgExecutionPrice = 0.0; // quantity-weighted
};

} // namespace tca
