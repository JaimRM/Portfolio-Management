#pragma once
#include "MarketTypes.hpp"
#include "MarketImpactModel.hpp"
#include <vector>
#include <numeric>
#include <cmath>
#include <stdexcept>

namespace tca {

// Base interface: every algorithm consumes a MarketDay + ParentOrder and
// produces a sequence of child Fills.
class IExecutionAlgorithm {
public:
    virtual ~IExecutionAlgorithm() = default;
    virtual ExecutionResult execute(const MarketDay& day, const ParentOrder& order) const = 0;
    virtual std::string name() const = 0;

protected:
    // Shared fill-price logic given a schedule of child quantities per bar.
    ExecutionResult runSchedule(const MarketDay& day, const ParentOrder& order,
                                 const std::vector<double>& childQty) const {
        ExecutionResult result;
        result.algoName = name();
        double permanentDrift = 0.0; // accumulated permanent impact carried into ref price

        double qtySum = 0.0;
        double notionalSum = 0.0;

        for (int i = order.startBar; i <= order.endBar; ++i) {
            double qty = childQty[i - order.startBar];
            if (qty <= 0.0) continue;

            const MarketBar& bar = day.bars[i];
            double refPrice = bar.midPrice * (1.0 + sideSign(order.side) * permanentDrift);
            double halfSpread = bar.bidAskSpread / 2.0;
            double participation = qty / std::max(1.0, bar.marketVolume);

            double px = impact_.effectivePrice(refPrice, bar.volatility, halfSpread, participation, order.side);

            result.fills.push_back(Fill{i, qty, px, bar.marketVolume});
            qtySum += qty;
            notionalSum += qty * px;

            permanentDrift += impact_.permanentImpactFraction(bar.volatility, participation);
        }

        result.totalQuantityFilled = qtySum;
        result.avgExecutionPrice = qtySum > 0.0 ? notionalSum / qtySum : 0.0;
        return result;
    }

    MarketImpactModel impact_;
};

// ---------------------------------------------------------------------------
// TWAP: split the parent order into equal-sized slices, one per bar, evenly
// spread over the execution horizon. Simple, predictable, ignores volume.
// ---------------------------------------------------------------------------
class TWAPAlgorithm : public IExecutionAlgorithm {
public:
    std::string name() const override { return "TWAP"; }

    ExecutionResult execute(const MarketDay& day, const ParentOrder& order) const override {
        int horizon = order.endBar - order.startBar + 1;
        if (horizon <= 0) throw std::invalid_argument("Invalid execution horizon");

        std::vector<double> childQty(horizon, order.totalQuantity / horizon);
        return runSchedule(day, order, childQty);
    }
};

// ---------------------------------------------------------------------------
// VWAP: slice the parent order proportionally to each bar's share of the
// forecast/historical volume profile over the horizon, so the algo's own
// participation rate stays roughly constant and tracks the market's VWAP.
// ---------------------------------------------------------------------------
class VWAPAlgorithm : public IExecutionAlgorithm {
public:
    std::string name() const override { return "VWAP"; }

    ExecutionResult execute(const MarketDay& day, const ParentOrder& order) const override {
        int horizon = order.endBar - order.startBar + 1;
        if (horizon <= 0) throw std::invalid_argument("Invalid execution horizon");

        double horizonVolume = 0.0;
        for (int i = order.startBar; i <= order.endBar; ++i) horizonVolume += day.bars[i].marketVolume;

        std::vector<double> childQty(horizon);
        for (int i = 0; i < horizon; ++i) {
            double weight = day.bars[order.startBar + i].marketVolume / horizonVolume;
            childQty[i] = order.totalQuantity * weight;
        }
        return runSchedule(day, order, childQty);
    }
};

// ---------------------------------------------------------------------------
// Implementation Shortfall (Almgren-Chriss): front-loads execution to trade
// off market impact cost against timing (volatility) risk, controlled by a
// risk-aversion parameter lambda. Higher lambda => trade faster/more urgently.
//
// Optimal remaining-inventory trajectory (continuous-time Almgren-Chriss):
//   x(t) = X * sinh(kappa * (T - t)) / sinh(kappa * T)
// where kappa = sqrt(lambda * sigma^2 / eta_temp)
// ---------------------------------------------------------------------------
class ImplementationShortfallAlgorithm : public IExecutionAlgorithm {
public:
    explicit ImplementationShortfallAlgorithm(double riskAversion = 5e-6)
        : lambda_(riskAversion) {}

    std::string name() const override { return "Implementation Shortfall (Almgren-Chriss)"; }

    ExecutionResult execute(const MarketDay& day, const ParentOrder& order) const override {
        int horizon = order.endBar - order.startBar + 1;
        if (horizon <= 0) throw std::invalid_argument("Invalid execution horizon");

        double sigma = day.bars[order.startBar].volatility; // per-bar volatility
        double etaTemp = 0.6; // must match MarketImpactModel's eta for consistency
        double kappa = std::sqrt(std::max(1e-12, lambda_ * sigma * sigma / etaTemp));

        double T = static_cast<double>(horizon);
        std::vector<double> inventory(horizon + 1);
        for (int t = 0; t <= horizon; ++t) {
            double remaining = T - static_cast<double>(t);
            if (kappa * T < 1e-8) {
                // Degenerate case: kappa ~ 0 reduces to linear (TWAP-like) schedule.
                inventory[t] = order.totalQuantity * remaining / T;
            } else {
                inventory[t] = order.totalQuantity * std::sinh(kappa * remaining) / std::sinh(kappa * T);
            }
        }

        std::vector<double> childQty(horizon);
        for (int i = 0; i < horizon; ++i) {
            childQty[i] = inventory[i] - inventory[i + 1];
        }
        return runSchedule(day, order, childQty);
    }

private:
    double lambda_; // risk-aversion coefficient (higher = trade faster)
};

} // namespace tca
