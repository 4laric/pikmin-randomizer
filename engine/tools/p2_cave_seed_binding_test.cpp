#include "pc_p2_cave_seed_binding.h"
#undef NDEBUG
#include <cassert>
#include <sstream>
#include <iostream>

static std::string wire() {
    return "1 generated-forest-v1 forest_1 1 7989240218121528064 "
        "f4ac3b78b6ff81adbe0aad75398e35af 2 "
        "91 treasure_water forest_1:f1:leaf:0 item:forest_1:f1:leaf:0:0 "
        "92 treasure_elec forest_1:f1:leaf:1 item:forest_1:f1:leaf:1:0 END";
}
static void refused(std::string text) {
    P2CaveSeedBinding retained; retained.seed = 42; retained.token = "retained";
    std::istringstream in(text);
    assert(!p2CaveSeedRead(in, 91, retained));
    assert(retained.seed == 42 && retained.token == "retained");
}
static std::string changed(const std::string& from, const std::string& to) {
    auto s = wire(); const auto at = s.find(from); assert(at != std::string::npos);
    s.replace(at, from.size(), to); return s;
}
int main() {
    int receiver = 1, foreignReceiver = 2;
    assert(p2CaveSeedReceiverMatch(true, true, &receiver, &receiver));
    assert(!p2CaveSeedReceiverMatch(true, true, &receiver, &foreignReceiver));
    assert(!p2CaveSeedReceiverMatch(true, false, &receiver, &receiver));
    assert(!p2CaveSeedReceiverMatch(false, true, &receiver, &receiver));
    assert(!p2CaveSeedReceiverMatch(true, true, nullptr, nullptr));
    int actor = 3, config = 4, foreignConfig = 5;
    assert(p2CaveSeedCargoMatch(&actor, &actor, &config, &config));
    assert(!p2CaveSeedCargoMatch(&actor, &foreignReceiver, &config, &config));
    assert(!p2CaveSeedCargoMatch(&actor, &actor, &config, &foreignConfig));
    assert(!p2CaveSeedCargoMatch(nullptr, &actor, &config, &config));
    assert(!p2CaveSeedCargoMatch(&actor, &actor, nullptr, nullptr));
    P2CaveSeedBinding b; std::istringstream in(wire());
    assert(p2CaveSeedRead(in, 91, b));
    std::string end; assert(in >> end && end == "END");
    assert(b.seed == 7989240218121528064ULL);
    assert(b.checks[0].index == 91 && b.checks[1].index == 92);
    for (auto pair : {std::pair<const char*, const char*>{"1 generated", "2 generated"},
            {"generated-forest-v1", "tutorial-retail"}, {"forest_1 1", "tutorial_1 1"},
            {"forest_1 1", "forest_1 2"}, {"35af 2", "35af 1"},
            {"91 treasure", "90 treasure"}, {"92 treasure", "91 treasure"},
            {"treasure_elec", "treasure_water"}, {"leaf:0 item", "leaf:1 item"},
            {"item:forest_1:f1:leaf:0:0", "item:forest_1:f1:leaf:0:1"},
            {"f4ac3b", "F4ac3b"}, {"7989240218121528064", "18446744073709551616"}})
        refused(changed(pair.first, pair.second));
    refused(wire().substr(0, wire().find("92 treasure")));
    std::uint64_t n = 0;
    assert(p2CaveSeedUint64("18446744073709551615", n) && n == UINT64_MAX);
    assert(p2CaveSeedUint64("0", n) && n == 0);
    for (const char* bad : {"", "00", "01", "+1", "-1", "1x", " 1",
                            "18446744073709551616", "999999999999999999999"})
        assert(!p2CaveSeedUint64(bad, n));
    const auto& row = b.checks[0];
    const auto match = [&](std::uint64_t seed, const char* cave, int floor,
                          const char* item, const char* host, const char* slot,
                          const std::string& token) {
        return p2CaveSeedPhysicalCheck(b, seed, cave, floor, item, host, slot, token);
    };
    assert(match(b.seed, "forest_1", 1, row.item.c_str(), row.host.c_str(), row.slot.c_str(), b.token) == &row);
    assert(!match(b.seed + 1, "forest_1", 1, row.item.c_str(), row.host.c_str(), row.slot.c_str(), b.token));
    assert(!match(b.seed, "tutorial_1", 1, row.item.c_str(), row.host.c_str(), row.slot.c_str(), b.token));
    assert(!match(b.seed, "forest_1", 2, row.item.c_str(), row.host.c_str(), row.slot.c_str(), b.token));
    assert(!match(b.seed, "forest_1", 1, "treasure_elec", row.host.c_str(), row.slot.c_str(), b.token));
    assert(!match(b.seed, "forest_1", 1, row.item.c_str(), "forest_1:f1:leaf:1", row.slot.c_str(), b.token));
    assert(!match(b.seed, "forest_1", 1, row.item.c_str(), row.host.c_str(), row.slot.c_str(), "foreign"));
    std::cout << "PASS generated cave exact bootstrap and physical identities\n";
}
