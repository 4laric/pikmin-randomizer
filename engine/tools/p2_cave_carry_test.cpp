// Lane 50 (#488): one-consumer gate for carry blocking.
//
// Proves, over the forest_1 floor-1 forest_1 carry plan (seed 468001):
//   * the plan parses to the same cave/floor/seed/geometry, door order and ids;
//   * every door's carry_block/key is derived from its hazard (none/water/elec);
//   * the verdict gates only non-immune CARRIERS (immune passes, non-carrier is
//     ignored, a non-blocking door always passes);
//   * malformed/truncated/duplicate/mismatched text is rejected.
// With argv[1] it also parses a host-written gates config and prints the marker.
#include "pc_p2_cave_carry.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#define CHECK(condition)                                                              \
    do {                                                                              \
        if (!(condition)) {                                                           \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
            return 1;                                                                 \
        }                                                                             \
    } while (0)

static const char* kPlan =
    "P2_CAVE_GATES_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "geometry proxy\n"
    "doors 6\n"
    "forest_1:f1:segment:0 segment none none -\n"
    "choke_water_0 choke water water blue\n"
    "leaf_elec_0 leaf elec elec yellow\n"
    "forest_1:f1:segment:1 segment none none -\n"
    "gate:leaf_elec_0 gate elec elec yellow\n"
    "leaf_water_0 leaf water water blue\n"
    "entrance forest_1:f1:segment:0\n"
    "hole forest_1:f1:segment:1\n";

static bool parse(const char* text, P2CaveCarryPlan& plan)
{
    std::istringstream in(text);
    std::string error;
    return p2CaveCarryParse(in, plan, error);
}

int main(int argc, char** argv)
{
    P2CaveCarryPlan plan;
    CHECK(parse(kPlan, plan));
    CHECK(plan.cave == "forest_1");
    CHECK(plan.floor == 1);
    CHECK(plan.seed == 468001);
    CHECK(plan.geometry == "proxy");
    CHECK(plan.doors.size() == 6);
    CHECK(plan.entrance == "forest_1:f1:segment:0");
    CHECK(plan.hole == "forest_1:f1:segment:1");
    CHECK(plan.doors[1].id == "choke_water_0");
    CHECK(plan.doors[1].kind == "choke");
    CHECK(plan.doors[1].hazard == "water");
    CHECK(plan.doors[1].carry_block == "water");
    CHECK(plan.doors[1].key == "blue");
    CHECK(plan.doors[2].carry_block == "elec");
    CHECK(plan.doors[2].key == "yellow");
    CHECK(plan.doors[0].carry_block.empty());
    CHECK(plan.doors[0].key.empty());
    CHECK(p2CaveCarryBlockingCount(plan) == 4);
    CHECK(!p2CaveCarryBlocks(plan.doors[0]));
    CHECK(p2CaveCarryBlocks(plan.doors[1]));
    CHECK(p2CaveCarryBlocks(plan.doors[2]));
    CHECK(std::string(p2CaveCarryKeyFor(plan.doors[1].carry_block)) == "blue");
    CHECK(std::string(p2CaveCarryHazardFor(plan.doors[2].carry_block)) == "elec");

    // Verdict: only a non-immune carrier is blocked; immune and non-blocking pass.
    CHECK(p2CaveCarryDecide(plan.doors[0], false, true) == P2CaveCarryPass);
    CHECK(p2CaveCarryDecide(plan.doors[1], false, true) == P2CaveCarryBlock);
    CHECK(p2CaveCarryDecide(plan.doors[1], true, true) == P2CaveCarryPass);
    CHECK(p2CaveCarryDecide(plan.doors[1], false, false) == P2CaveCarryIgnore);
    CHECK(p2CaveCarryDecide(plan.doors[2], false, true) == P2CaveCarryBlock);
    CHECK(p2CaveCarryDecide(plan.doors[2], true, true) == P2CaveCarryPass);

    const std::string marker = p2CaveCarryMarker(plan);
    CHECK(marker == "P2_CAVE_CARRY_PLAN doors=6 blocking=4 elec=2 water=2 geometry=proxy "
                    "cave=forest_1 floor=1 seed=468001");
    const std::string doorMarker = p2CaveCarryDoorMarker(plan.doors[2]);
    CHECK(doorMarker == "P2_CAVE_CARRY_DOOR id=leaf_elec_0 kind=leaf hazard=elec "
                        "carry_block=elec key=yellow");
    CHECK(p2CaveCarryFindDoor(plan, "leaf_water_0") != nullptr);
    CHECK(p2CaveCarryFindDoor(plan, "nope") == nullptr);

    P2CaveCarryPlan bad;
    CHECK(!parse("P2_CAVE_GATES_1\ncave forest_1\nfloor 1\nseed 1\ngeometry proxy\n"
                 "doors 1\nid segment none none -\nentrance id\n",
                 bad));
    CHECK(!parse("NOPE\ncave x\n", bad));

    std::string duplicate = std::string(kPlan);
    const std::string waterRow = "leaf_water_0 leaf water water blue\n";
    duplicate.replace(duplicate.find(waterRow), waterRow.size(),
                      "leaf_elec_0 leaf elec elec yellow\n");
    CHECK(!parse(duplicate.c_str(), bad));

    std::string mismatch = std::string(kPlan);
    const std::string waterTail = "water water blue";
    mismatch.replace(mismatch.find(waterTail), waterTail.size(), "water water yellow");
    CHECK(!parse(mismatch.c_str(), bad));

    std::string unknownBlock = std::string(kPlan);
    unknownBlock.replace(unknownBlock.find(waterTail), waterTail.size(), "water fire blue");
    CHECK(!parse(unknownBlock.c_str(), bad));

    std::string badClass = std::string(kPlan);
    badClass.replace(badClass.find("geometry proxy"), 14, "geometry bananas");
    CHECK(!parse(badClass.c_str(), bad));

    CHECK(!parse("P2_CAVE_GATES_1\ncave forest_1\nfloor 1\nseed 1\ngeometry proxy\n"
                 "doors 1\nchoke_water_0 choke water water blue\n",
                 bad));

    if (argc > 1) {
        std::ifstream in(argv[1]);
        P2CaveCarryPlan host;
        std::string error;
        CHECK(p2CaveCarryParse(in, host, error));
        std::printf("%s\n", p2CaveCarryMarker(host).c_str());
    }
    std::puts("PASS p2 cave carry: plan parse, block verdict, immune/key mapping");
    std::fflush(stdout);
    return 0;
}
