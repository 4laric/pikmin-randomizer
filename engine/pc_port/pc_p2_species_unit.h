// Per-species placement unit for P2-in-P1 slots: when a seed-bound species replaces a
// generator, the generator births at least `unit` actors (Anode Beetle 28 = 2, a
// linked pair). The table is DATA staged by the randomizer into the run directory
// (randomizer/p2_units.py writes p2-species-units.txt from the pool's "unit" field):
//
//     P2_SPECIES_UNITS_1
//     28 2
//
// No file, or a species not listed, means unit 1 (the generator's own count).
#pragma once
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <sstream>
#include <string>

#include "pc_randomizer.h"

namespace p2unit {

inline bool parse(const std::string& text, std::map<unsigned, int>& out) {
    std::istringstream in(text);
    std::string header;
    if (!(in >> header) || header != "P2_SPECIES_UNITS_1") return false;
    unsigned source = 0;
    int unit = 0;
    while (in >> source) {
        if (!(in >> unit) || source == 0 || unit < 1 || unit > 8) return false;
        out[source] = unit;
    }
    return in.eof();
}

// Generator count after the unit rule: never below the generator's own count.
inline int effectiveCount(int generatorCount, int unit) { return unit > generatorCount ? unit : generatorCount; }

// Offset of the i-th actor (i >= 1) of a unit from the generator spot: a ring, 40 apart
// so a pair is far inside the 300-unit Anode Beetle link range.
constexpr float kSpacing = 40.0f;

inline const std::map<unsigned, int>& table() {
    static std::map<unsigned, int> units;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        std::ifstream file("p2-species-units.txt");
        if (file) {
            std::stringstream buffer;
            buffer << file.rdbuf();
            if (!parse(buffer.str(), units)) {
                units.clear();
                std::printf("P2_SPECIES_UNITS_ERROR file unreadable\n");
            } else {
                for (const auto& row : units) std::printf("P2_SPECIES_UNIT source_id=%u unit=%d\n", row.first, row.second);
            }
            std::fflush(stdout);
        }
    }
    return units;
}

// Unit for the species bound to `generator`; 1 when unbound or not listed.
inline int unitForGenerator(const void* generator) {
    if (!pc_randomizer_p2_bridge() || !generator) return 1;
    const unsigned source = pc_randomizer_p2_source_for_id(pc_randomizer_generator_id(generator));
    if (!source) return 1;
    const auto& units = table();
    const auto it = units.find(source);
    return it == units.end() ? 1 : it->second;
}

} // namespace p2unit
