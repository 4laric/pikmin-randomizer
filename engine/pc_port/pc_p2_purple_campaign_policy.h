#pragma once
#include <cstdint>
#include <istream>
#include <map>
#include <string>

namespace p2purplecampaign {
// Stage identity is part of the binding: IDs are not globally unique in P1.
struct Config {
    std::map<int, std::uint32_t> violet;
    bool matches(int stage, std::uint32_t generator) const {
        const auto row = violet.find(stage);
        return generator && row != violet.end() && row->second == generator;
    }
};
inline bool parse(std::istream& in, Config& result) {
    Config parsed;
    std::string token;
    int count;
    if (!(in >> token >> count) || token != "P2_PURPLE_CAMPAIGN_1" || count < 1 || count > 5) return false;
    for (int i = 0; i < count; ++i) {
        int stage; unsigned long long generator;
        if (!(in >> stage >> generator) || stage < 0 || stage > 4 || !generator || generator > UINT32_MAX
            || !parsed.violet.emplace(stage, static_cast<std::uint32_t>(generator)).second) return false;
    }
    if (in >> token) return false;
    result = parsed;
    return true;
}
}
