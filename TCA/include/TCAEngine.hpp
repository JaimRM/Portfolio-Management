#pragma once
#include "MarketTypes.hpp"
#include <string>
#include <numeric>
#include <cmath>

namespace tca {

// Standard Transaction Cost Analysis report for a single execution run.
struct TCAReport {
    std::string algoName;

    double arrivalPrice = 0.0;
    double avgExecutionPrice = 0.0;
    double marketVWAP = 0.0;          // volume-weighted market price over the horizon
    double quantityFilled = 0.0;

    // Costs, expressed in basis points (bps) of arrival price, sign convention:
    // positive = cost (bad for the trader), negative = price improvement.
    double implementationShortfallBps = 0.0; // vs arrival price (Perold 1988)
    double vwapSlippageBps = 0.0;            // vs interval market VWAP
    double avgParticipationRate = 0.0;       // avg % of bar volume consumed
    double maxParticipationRate = 0.0;
    double effectiveSpreadCostBps = 0.0;     // cost attributable to crossing the spread

    double implementationShortfallUSD = 0.0; // in currency terms
};

class TCAEngine {
public:
    // Computes a full TCA report for one execution result against the market day.
    static TCAReport analyze(const ExecutionResult& exec, const MarketDay& day,
                              const ParentOrder& order) {
        TCAReport report;
        report.algoName = exec.algoName;
        report.arrivalPrice = order.arrivalPrice;
        report.avgExecutionPrice = exec.avgExecutionPrice;
        report.quantityFilled = exec.totalQuantityFilled;

        double sign = sideSign(order.side);

        // --- Implementation Shortfall (Perold 1988) ---
        // IS = sign * (avgExecPrice - arrivalPrice) / arrivalPrice, in bps.
        report.implementationShortfallBps =
            sign * (exec.avgExecutionPrice - order.arrivalPrice) / order.arrivalPrice * 10000.0;
        report.implementationShortfallUSD =
            sign * (exec.avgExecutionPrice - order.arrivalPrice) * exec.totalQuantityFilled;

        // --- Interval market VWAP benchmark ---
        double volSum = 0.0, pxVolSum = 0.0;
        for (int i = order.startBar; i <= order.endBar; ++i) {
            const MarketBar& bar = day.bars[i];
            volSum += bar.marketVolume;
            pxVolSum += bar.marketVolume * bar.midPrice;
        }
        report.marketVWAP = volSum > 0.0 ? pxVolSum / volSum : order.arrivalPrice;
        report.vwapSlippageBps =
            sign * (exec.avgExecutionPrice - report.marketVWAP) / report.marketVWAP * 10000.0;

        // --- Participation & spread cost ---
        double partSum = 0.0, spreadCostSum = 0.0;
        double maxPart = 0.0;
        for (const Fill& f : exec.fills) {
            const MarketBar& bar = day.bars[f.timeIndex];
            double participation = f.quantity / std::max(1.0, bar.marketVolume);
            partSum += participation;
            maxPart = std::max(maxPart, participation);

            double halfSpread = bar.bidAskSpread / 2.0;
            spreadCostSum += sign * halfSpread / bar.midPrice * 10000.0 * f.quantity;
        }
        report.avgParticipationRate = exec.fills.empty() ? 0.0 : partSum / exec.fills.size();
        report.maxParticipationRate = maxPart;
        report.effectiveSpreadCostBps =
            exec.totalQuantityFilled > 0.0 ? spreadCostSum / exec.totalQuantityFilled : 0.0;

        return report;
    }
};

} // namespace tca
