#pragma once

// Production bootstrap contract. This module observes identities only; the
// physical Pod delivery callback remains the producer of native checks.
#include <array>
#include <cstdint>
#include <istream>
#include <limits>
#include <string>

struct P2CaveSeedCheck {
    unsigned index = 0;
    std::string item, host, slot;
};

struct P2CaveSeedBinding {
    std::uint64_t seed = 0;
    std::string token;
    std::array<P2CaveSeedCheck, 2> checks;
};

inline bool p2CaveSeedReceiverMatch(bool enabled, bool ready,
    const void* ownedReceiver, const void* actualTarget) {
    return enabled && ready && ownedReceiver && actualTarget == ownedReceiver;
}

inline bool p2CaveSeedCargoMatch(const void* ownedActor, const void* actualActor,
    const void* ownedConfig, const void* actualConfig) {
    return ownedActor && ownedConfig && actualActor == ownedActor
        && actualConfig == ownedConfig;
}

inline const char* p2CaveSeedCheckName(unsigned ordinal) {
    static const char* names[] = {
        "Pikmin 2: Generated Forest Cave F1 Water Treasure",
        "Pikmin 2: Generated Forest Cave F1 Electric Treasure"
    };
    return ordinal < 2 ? names[ordinal] : nullptr;
}

inline bool p2CaveSeedUint64(const std::string& text, std::uint64_t& value) {
    if (text.empty() || text.size() > 20 || (text.size() > 1 && text[0] == '0')) return false;
    value = 0;
    for (char c : text) {
        if (c < '0' || c > '9') return false;
        const unsigned digit = unsigned(c - '0');
        if (value > (std::numeric_limits<std::uint64_t>::max() - digit) / 10) return false;
        value = value * 10 + digit;
    }
    return true;
}

// Called after CAVE_CHECKS was consumed. The two new checks must append to the
// already validated complete base catalog, never renumber its existing checks.
inline bool p2CaveSeedRead(std::istream& in, unsigned baseCount, P2CaveSeedBinding& result) {
    std::string version, identity, cave, floor, seed, token, count;
    if (!(in >> version >> identity >> cave >> floor >> seed >> token >> count)
        || version != "1" || identity != "generated-forest-v1" || cave != "forest_1"
        || floor != "1" || count != "2" || token.size() != 32
        || token.find_first_not_of("0123456789abcdef") != std::string::npos
        || baseCount > std::numeric_limits<unsigned>::max() - 2) return false;
    P2CaveSeedBinding candidate;
    if (!p2CaveSeedUint64(seed, candidate.seed)) return false;
    candidate.token = token;
    for (unsigned i = 0; i < 2; ++i) {
        std::string index;
        auto& check = candidate.checks[i];
        std::uint64_t parsed = 0;
        const std::string host = "forest_1:f1:leaf:" + std::to_string(i);
        if (!(in >> index >> check.item >> check.host >> check.slot)
            || !p2CaveSeedUint64(index, parsed) || parsed != baseCount + i
            || check.item != (i == 0 ? "treasure_water" : "treasure_elec")
            || check.host != host || check.slot != "item:" + host + ":0") return false;
        check.index = unsigned(parsed);
    }
    result = candidate;
    return true;
}

inline const P2CaveSeedCheck* p2CaveSeedPhysicalCheck(
    const P2CaveSeedBinding& binding, std::uint64_t seed, const std::string& cave,
    int floor, const std::string& item, const std::string& host, const std::string& slot,
    const std::string& boundaryToken) {
    if (seed != binding.seed || cave != "forest_1" || floor != 1
        || boundaryToken != binding.token) return nullptr;
    for (const auto& check : binding.checks)
        if (check.item == item && check.host == host && check.slot == slot) return &check;
    return nullptr;
}
