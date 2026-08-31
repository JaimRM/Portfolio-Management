#pragma once
#include "MarketTypes.hpp"
#include "TCAEngine.hpp"
#include <fstream>
#include <vector>
#include <string>
#include <stdexcept>

namespace tca {

class CsvWriter {
public:
    static void writeFills(const std::string& path, const ExecutionResult& exec) {
        std::ofstream out(path);
        if (!out) throw std::runtime_error("Cannot open " + path);
        out << "algo,time_index,quantity,price,market_volume,participation_rate\n";
        for (const Fill& f : exec.fills) {
            double part = f.quantity / std::max(1.0, f.marketVolume);
            out << exec.algoName << "," << f.timeIndex << "," << f.quantity << ","
                << f.price << "," << f.marketVolume << "," << part << "\n";
        }
    }

    static void writeReports(const std::string& path, const std::vector<TCAReport>& reports) {
        std::ofstream out(path);
        if (!out) throw std::runtime_error("Cannot open " + path);
        out << "algo,arrival_price,avg_exec_price,market_vwap,qty_filled,"
               "is_bps,vwap_slippage_bps,avg_participation,max_participation,"
               "spread_cost_bps,is_usd\n";
        for (const TCAReport& r : reports) {
            out << r.algoName << "," << r.arrivalPrice << "," << r.avgExecutionPrice << ","
                << r.marketVWAP << "," << r.quantityFilled << "," << r.implementationShortfallBps << ","
                << r.vwapSlippageBps << "," << r.avgParticipationRate << "," << r.maxParticipationRate << ","
                << r.effectiveSpreadCostBps << "," << r.implementationShortfallUSD << "\n";
        }
    }
};

} // namespace tca
