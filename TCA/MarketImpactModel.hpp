#pragma once
#include "MarketTypes.hpp"
#include <cmath>
#include <algorithm>

namespace tca {

// Square-root market impact model (Almgren-Chriss style), splitting cost into:
//  - Temporary impact: transient cost paid on THIS trade only, recovers after execution.
//  - Permanent impact: moves the reference price for the rest of the day.
//
// temp_impact(bps)  = eta   * sigma * sqrt(participationRate)
// perm_impact(bps)  = gamma * sigma * participationRate
//
// where participationRate = childOrderQty / barMarketVolume.
class MarketImpactModel {
public:
    MarketImpactModel(double eta = 0.6, double gamma = 0.3)
        : eta_(eta), gamma_(gamma) {}

    // Returns the effective execution price for a child slice, given the
    // pre-trade mid price, the bar's volatility, half-spread, side, and
    // how much of the bar's volume this order consumes.
    double effectivePrice(double midPrice, double barVolatility, double halfSpread,
                           double participationRate, Side side) const {
        double sign = sideSign(side);
        double tempImpactFrac = eta_ * barVolatility * std::sqrt(std::max(0.0, participationRate));
        // Crossing the spread always costs; impact pushes price further adversely.
        double cost = halfSpread + midPrice * tempImpactFrac;
        return midPrice + sign * cost;
    }

    // Permanent impact (bps of price) that should be carried forward to the
    // next bar's reference price after executing at this participation rate.
    double permanentImpactFraction(double barVolatility, double participationRate) const {
        return gamma_ * barVolatility * std::max(0.0, participationRate);
    }

private:
    double eta_;   // temporary impact coefficient
    double gamma_; // permanent impact coefficient
};

} // namespace tca
