#pragma once

#include <cstdint>
#include <istream>
#include <set>
#include <map>
#include <string>

namespace p2purpledirect {

constexpr float AdultHipdropDamage = 50.0f;

struct Config {
    std::set<std::uint32_t> adultGenerators;
    bool campaign = false;
    std::map<std::uint32_t, unsigned> bindings;
    unsigned source(std::uint32_t uid, unsigned seededSource) const {
        const auto it = bindings.find(uid);
        return campaign && it != bindings.end() && it->second == seededSource ? seededSource : 0;
    }
};

inline bool parse(std::istream& in, Config& out)
{
    std::string word;
    float damage = 0.0f;
    int count = 0;
    Config parsed;
    if (!(in >> word)) return false;
    if (word == "P2_PURPLE_DIRECT_2") {
        parsed.campaign = true;
        if (!(in >> word >> count) || word != "bindings" || count < 0 || count > 1024) return false;
        for (int i = 0; i < count; ++i) {
            long long uid = -1; unsigned source = 0;
            if (!(in >> uid >> source) || uid <= 0 || uid > 0xffffffffLL
                || source != 2
                || !parsed.bindings.emplace(static_cast<std::uint32_t>(uid), source).second) return false;
        }
        if (in >> word) return false;
        out = parsed; return true;
    }
    if (word != "P2_PURPLE_DIRECT_1"
        || !(in >> word >> damage) || word != "adult_fp36" || damage != AdultHipdropDamage
        || !(in >> word >> count) || word != "adult_generators" || count < 0 || count > 32) return false;
    for (int i = 0; i < count; ++i) {
        long long id = -1;
        if (!(in >> id) || id < 0 || id > 0xffffffffLL
            || !parsed.adultGenerators.insert(static_cast<std::uint32_t>(id)).second) return false;
    }
    if (in >> word) return false;
    out = parsed;
    return true;
}

} // namespace p2purpledirect
