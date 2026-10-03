#include "pc_p2_cave_seed_binding.h"
#include "pc_p2_cave_campaign_cache.h"
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
    auto cacheImage=[](unsigned char marker) {
        std::string image(P2CaveCacheBanks::imageSize,'\0');
        image[6]=char(0x6c); // big-endian freeSize = native heap size
        image[8]=char(marker);
        for(unsigned i=0;i<5;++i){const unsigned at=8+P2CaveCacheBanks::heapSize+i*37;
            image[at]=char(255);image[at+4]=char(i);}
        return image;
    };
    const auto surface=cacheImage(65),floor=cacheImage(66);
    P2CaveCacheBanks banks;
    assert(banks.valid() && banks.enter(surface) && banks.captureFloor(floor));
    assert(!banks.enter(floor) && banks.surface==surface && banks.floor==floor);
    std::ostringstream cacheWire;banks.write(cacheWire);
    P2CaveCacheBanks restored;std::istringstream cacheInput(cacheWire.str());
    assert(restored.read(cacheInput) && restored.inside && restored.surface==surface && restored.floor==floor);
    auto corrupt=floor;corrupt[0]=1;
    assert(!restored.captureFloor(corrupt) && restored.floor==floor);
    for(const char* text:{"CAVE_CACHE 1 1 - -","CAVE_CACHE 1 2 - -","CAVE_CACHE 2 0 - -",
            "CAVE_CACHE 1 0 ff -","CAVE_CACHE 1 0 - FF"}) {
        std::istringstream bad(text);
        assert(!restored.read(bad) && restored.inside && restored.surface==surface && restored.floor==floor);
    }
    assert(restored.leave(floor) && !restored.inside && restored.surface.empty() && restored.floor==floor);
    assert(!restored.leave(surface));
    assert(restored.enter(surface) && restored.floor==floor);
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
    P2CaveSeedBudget budget;
    assert(p2CaveSeedBudIndex("forest_1:f1:bud:0") == 0);
    assert(p2CaveSeedBudIndex("forest_1:f1:bud:1") == 1);
    assert(p2CaveSeedBudIndex("foreign") == -1);
    assert(budget.consume(0, 1) && budget.consume(0, 2) && budget.consume(1, 1));
    assert(!budget.consume(0, 2) && !budget.consume(0, 1) && !budget.consume(0, 4));
    assert(!budget.consume(2, 1));
    std::ostringstream encoded; budget.write(encoded);
    assert(encoded.str() == " CAVE_BUDS 1 2 1");
    P2CaveSeedBudget decoded;
    std::istringstream validBudget(encoded.str());
    assert(decoded.read(validBudget) && decoded.used == budget.used);
    for (const char* bad : {"CAVE_BUDS 2 2 1", "OTHER 1 2 1", "CAVE_BUDS 1 6 1",
            "CAVE_BUDS 1 -1 1", "CAVE_BUDS 1 02 1", "CAVE_BUDS 1 2", "CAVE_BUDS 1 2 6"}) {
        std::istringstream input(bad);
        assert(!decoded.read(input) && decoded.used == budget.used);
    }
    for (unsigned i = 3; i <= 5; ++i) assert(budget.consume(0, i));
    assert(!budget.consume(0, 6));
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
