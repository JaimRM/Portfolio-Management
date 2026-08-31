#include "MarketSimulator.hpp"
#include "ExecutionAlgorithms.hpp"
#include "TCAEngine.hpp"
#include "CsvWriter.hpp"

#include <iostream>
#include <iomanip>
#include <memory>
#include <vector>
#include <filesystem>

using namespace tca;

namespace {

void printReportTable(const std::vector<TCAReport>& reports) {
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "\n================= TCA COMPARISON REPORT =================\n";
    std::cout << std::left << std::setw(32) << "Algorithm"
               << std::right << std::setw(12) << "AvgPx"
               << std::setw(12) << "IS(bps)"
               << std::setw(14) << "VWAPslip(bps)"
               << std::setw(12) << "AvgPart%"
               << std::setw(12) << "MaxPart%"
               << std::setw(14) << "IS($)" << "\n";
    std::cout << std::string(108, '-') << "\n";
    for (const auto& r : reports) {
        std::cout << std::left << std::setw(32) << r.algoName
                   << std::right << std::setw(12) << r.avgExecutionPrice
                   << std::setw(12) << r.implementationShortfallBps
                   << std::setw(14) << r.vwapSlippageBps
                   << std::setw(12) << r.avgParticipationRate * 100.0
                   << std::setw(12) << r.maxParticipationRate * 100.0
                   << std::setw(14) << r.implementationShortfallUSD << "\n";
    }
    std::cout << std::string(108, '-') << "\n";
    std::cout << "IS(bps): Implementation Shortfall vs arrival price (positive = cost).\n";
    std::cout << "VWAPslip(bps): execution price vs interval market VWAP.\n";
    std::cout << "AvgPart%/MaxPart%: average/peak participation rate in bar volume.\n";
}

} // namespace

int main() {
    // --- 1. Simulate today's market ---
    MarketSimConfig mktCfg;
    mktCfg.numBars = 390;               // 1-min bars, full US equity session
    mktCfg.startPrice = 100.0;
    mktCfg.dailyVolatility = 0.02;
    mktCfg.averageDailyVolume = 5'000'000.0;
    mktCfg.baseSpreadBps = 2.0;
    mktCfg.seed = 42;

    MarketSimulator simulator(mktCfg);
    MarketDay day = simulator.simulateDay();

    // --- 2. Define the parent order we need to execute ---
    ParentOrder order;
    order.symbol = "SYN";
    order.side = Side::Buy;
    order.totalQuantity = 500'000.0;   // 10% of ADV: a genuinely costly order to work
    order.startBar = 0;
    order.endBar = day.numBars() - 1;  // execute over the full day
    order.arrivalPrice = day.bars[order.startBar].midPrice;

    std::cout << "Simulated symbol: " << order.symbol
              << " | Side: " << sideToString(order.side)
              << " | Qty: " << order.totalQuantity
              << " | ADV: " << mktCfg.averageDailyVolume
              << " (" << (100.0 * order.totalQuantity / mktCfg.averageDailyVolume) << "% of ADV)\n";
    std::cout << "Arrival price: " << order.arrivalPrice << "\n";

    // --- 3. Run each execution algorithm against the same market realization ---
    std::vector<std::unique_ptr<IExecutionAlgorithm>> algos;
    algos.push_back(std::make_unique<TWAPAlgorithm>());
    algos.push_back(std::make_unique<VWAPAlgorithm>());
    algos.push_back(std::make_unique<ImplementationShortfallAlgorithm>(20.0));

    std::vector<TCAReport> reports;
    std::filesystem::create_directories("output");

    for (const auto& algo : algos) {
        ExecutionResult result = algo->execute(day, order);
        TCAReport report = TCAEngine::analyze(result, day, order);
        reports.push_back(report);

        std::string fname = "output/fills_" + result.algoName + ".csv";
        // Sanitize filename (remove spaces/parentheses)
        for (char& c : fname) if (c == ' ' || c == '(' || c == ')') c = '_';
        CsvWriter::writeFills(fname, result);
    }

    printReportTable(reports);
    CsvWriter::writeReports("output/tca_summary.csv", reports);

    std::cout << "\nDetailed fill-level CSVs and tca_summary.csv written to ./output/\n";
    return 0;
}
