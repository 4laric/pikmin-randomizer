// Lane 48 (#486, cave wave #468): engine-free bud-slot instantiation plan.
//
// The frozen cave model's fourth slot class is a *seeded* Candypop bud slot.
// Lane 41 already emits the bud node into the observed layout; lane 44 projects
// it into the playable P2CaveRoomLayout. This header is the missing consumer:
// it turns every ``kind=="bud"`` unit into one BudPlan, tying the real actor to
// the seeded bud node's segment (never a hand-placed position) and to the
// ordinary conversion count N.
//
// The conversion *behavior* is lane 23's (pc_p2_pom_policy.h); lane 48 only
// instantiates the actor and drives the ordinary acquisition path. This header
// stays engine-free so it has a one-consumer test (tools/p2_cave_bud_test.cpp).

#pragma once

#include "pc_p2_cave_rooms.h"

#include <string>
#include <vector>

namespace p2cavebud48 {

// Vanilla colour-bud lifetime budget, ip01 = 5 (p2pom::IpTtlBudget, lane 23).
inline constexpr int VanillaConversionCount = 5;

struct BudPlan {
    std::string slot_id;
    std::string colour;    // "yellow" / "blue" / "red" / "white"
    int colour_index = 2;  // P1 mColor: blue 0 / red 1 / yellow 2 / white 4
    int segment = 0;
    int count = VanillaConversionCount;
    float x = 0.0f;
    float z = 0.0f;
};

// Hazard key -> P1 Pikmin colour index. -1 for a slot with no colour key.
inline int p2CaveBudColourIndex(const std::string& colour)
{
    if (colour == "blue") return 0;
    if (colour == "red") return 1;
    if (colour == "yellow") return 2;
    if (colour == "white") return 4;
    return -1;
}

// One plan per bud unit, in layout order. A bud whose hazard has no colour key
// is skipped, so an unkeyable slot is never fabricated. ``count`` is the
// conversion count N exposed to logic (vanilla 5 until the seeded count is
// propagated through the lane-44 bridge).
inline std::vector<BudPlan> planBuds(const P2CaveRoomLayout& layout, int count = VanillaConversionCount)
{
    std::vector<BudPlan> out;
    if (count < 1) return out;
    for (const P2CaveRoomUnit& unit : layout.units) {
        if (unit.kind != "bud") continue;
        const std::string colour = p2CaveRoomsHazardKey(unit.hazard);
        const int colour_index = p2CaveBudColourIndex(colour);
        if (colour_index < 0) continue;
        BudPlan plan;
        plan.slot_id = unit.id;
        plan.colour = colour;
        plan.colour_index = colour_index;
        plan.segment = unit.segment_index;
        plan.count = count;
        plan.x = p2CaveRoomsWorldX(layout, unit);
        plan.z = p2CaveRoomsWorldZ(layout, unit);
        out.push_back(plan);
    }
    return out;
}

}  // namespace p2cavebud48
