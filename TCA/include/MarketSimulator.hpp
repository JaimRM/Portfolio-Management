#pragma once
#include "MarketTypes.hpp"
#include <random>
#include <cmath>

namespace tca {

// Parameters governing the synthetic market used for the simulation.
struct MarketSimConfig {
    int numBars = 390;              // 1-minute bars over a 6.5h trading session
    double startPrice = 100.0;      // opening mid price
    double dailyVolatility = 0.02;  // daily sigma (2%)
    double averageDailyVolume = 5'000'000.0; // ADV in shares
    double baseSpreadBps = 2.0;     // quoted spread in basis points of price
    unsigned int seed = 42;
};

// Generates a synthetic trading day: a GBM price path plus a realistic
// U-shaped ("smile") intraday volume profile, heavier at the open and close.
class MarketSimulator {
public:
    explicit MarketSimulator(MarketSimConfig cfg) : cfg_(cfg), rng_(cfg.seed) {}

    MarketDay simulateDay() {
        MarketDay day;
        day.bars.reserve(cfg_.numBars);

        const double perBarVol = cfg_.dailyVolatility / std::sqrt(static_cast<double>(cfg_.numBars));
        std::normal_distribution<double> priceShock(0.0, perBarVol);

        double price = cfg_.startPrice;
        double totalVolWeight = uShapeIntegral();

        for (int i = 0; i < cfg_.numBars; ++i) {
            // Price evolves as a discretized GBM (no drift assumption: T-cost analysis
            // should be agnostic to alpha; drift is set to 0 by default).
            double shock = priceShock(rng_);
            price *= std::exp(shock - 0.5 * perBarVol * perBarVol);

            double volWeight = uShapeWeight(i) / totalVolWeight;
            double barVolume = cfg_.averageDailyVolume * volWeight;

            double spread = price * (cfg_.baseSpreadBps / 10000.0);

            MarketBar bar{i, price, spread, barVolume, perBarVol};
            day.bars.push_back(bar);
            day.totalVolume += barVolume;
        }
        return day;
    }

private:
    // Classic U-shape: high volume near open/close, quieter midday.
    double uShapeWeight(int barIndex) const {
        double x = static_cast<double>(barIndex) / static_cast<double>(cfg_.numBars - 1); // 0..1
        // Parabola with minimum at midday, normalized to stay positive.
        double u = 1.0 + 2.5 * std::pow(2.0 * x - 1.0, 2);
        return u;
    }

    double uShapeIntegral() const {
        double total = 0.0;
        for (int i = 0; i < cfg_.numBars; ++i) total += uShapeWeight(i);
        return total;
    }

    MarketSimConfig cfg_;
    std::mt19937 rng_;
};

} // namespace tca
