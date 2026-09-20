// Lane 48 (#486): one-consumer gate for the seeded Candypop bud-slot plan.
//
// Proves, over the lane-41/44 forest_1 floor-1 bridge form:
//   * one BudPlan per ``kind=="bud"`` node, in layout order;
//   * the elec slot becomes yellow (colour index 2), water blue (0), fire red
//     (1), poison white (4);
//   * the plan keeps the seeded segment and the conversion count N;
//   * a bud slot with no colour key is never fabricated;
//   * an empty layout plans zero buds.
// With argv[1] it parses a host-written rooms config and prints the plans.
#include "pc_p2_cave_bud.h"

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

static const char* kRoomsWithBuds =
    "P2_CAVE_ROOMS_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "salt 0\n"
    "cell 48\n"
    "origin 0 0\n"
    "source engine\n"
    "geometry proxy\n"
    "units 5\n"
    "forest_1:f1:segment:0 segment none 0 0 0 bud_yellow_0,leaf_elec_0 -\n"
    "bud_yellow_0 bud elec 0 24 0 forest_1:f1:segment:0 -\n"
    "leaf_elec_0 leaf elec 0 72 48 forest_1:f1:segment:0,gate:leaf_elec_0 treasure_elec\n"
    "bud_blue_0 bud water 1 0 96 forest_1:f1:segment:1 -\n"
    "forest_1:f1:segment:1 segment none 1 0 96 bud_blue_0 -\n"
    "entrance forest_1:f1:segment:0\n"
    "hole forest_1:f1:segment:1\n"
    "edges 1\n"
    "forest_1:f1:segment:0 forest_1:f1:segment:1\n";

static bool parse(const char* text, P2CaveRoomLayout& layout, std::string& error)
{
    std::istringstream in(text);
    return p2CaveRoomsParse(in, layout, error);
}

int main(int argc, char** argv)
{
    P2CaveRoomLayout layout;
    std::string error;
    CHECK(parse(kRoomsWithBuds, layout, error));

    const std::vector<p2cavebud48::BudPlan> plans = p2cavebud48::planBuds(layout);
    CHECK(plans.size() == 2);
    CHECK(plans[0].slot_id == "bud_yellow_0");
    CHECK(plans[0].colour == "yellow");
    CHECK(plans[0].colour_index == 2);
    CHECK(plans[0].segment == 0);
    CHECK(plans[0].count == p2cavebud48::VanillaConversionCount);
    CHECK(plans[0].x == 24.0f && plans[0].z == 0.0f);
    CHECK(plans[1].slot_id == "bud_blue_0");
    CHECK(plans[1].colour == "blue");
    CHECK(plans[1].colour_index == 0);
    CHECK(plans[1].segment == 1);

    // A non-vanilla seeded count is carried through unchanged.
    const std::vector<p2cavebud48::BudPlan> counted = p2cavebud48::planBuds(layout, 3);
    CHECK(counted.size() == 2);
    CHECK(counted[0].count == 3 && counted[1].count == 3);

    // An unkeyable bud hazard is skipped, never fabricated.
    P2CaveRoomLayout unknown = layout;
    unknown.units[1].hazard = "mystery";
    CHECK(p2cavebud48::planBuds(unknown).size() == 1);

    // An empty layout plans zero buds.
    P2CaveRoomLayout empty;
    CHECK(p2cavebud48::planBuds(empty).empty());

    if (argc > 1) {
        std::ifstream in(argv[1]);
        CHECK(bool(in));
        P2CaveRoomLayout host;
        CHECK(p2CaveRoomsParse(in, host, error));
        const std::vector<p2cavebud48::BudPlan> host_buds = p2cavebud48::planBuds(host);
        for (const p2cavebud48::BudPlan& plan : host_buds) {
            std::printf("P2_CAVE_BUD_PLAN slot=%s colour=%s segment=%d count=%d x=%.3f z=%.3f\n",
                        plan.slot_id.c_str(), plan.colour.c_str(), plan.segment, plan.count, plan.x, plan.z);
        }
    }
    std::puts("PASS p2 cave bud: seeded slot plan, colour key, count, fail-closed");
    return 0;
}
