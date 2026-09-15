#pragma once

#include <cstdint>
#include <istream>
#include <set>
#include <string>

namespace p2purpledirect {

constexpr float AdultHipdropDamage = 50.0f;

struct Config {
    std::set<std::uint32_t> adultGenerators;
};

inline bool parse(std::istream& in, Config& out)
{
    std::string word;
    float damage = 0.0f;
    int count = 0;
    Config parsed;
    if (!(in >> word) || word != "P2_PURPLE_DIRECT_1"
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
