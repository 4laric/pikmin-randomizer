#include "pc_p2_cave_item_gate_placement.h"

#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

// Lane 37 (#476): focused one-consumer test for the cave item/gate placement
// routine. Frozen forest_1 floor 1 table across two seeds; tagged placement into
// the water/elec leaves plus the electric gate on the elec leaf door. This is a
// unit fixture, not a live generated cave: it proves the routine's decisions,
// not that the engine's generator called it.

static P2CaveFloorTable forestFloor1(int seed, P2CaveHazard chokeHazard)
{
    P2CaveFloorTable table;
    table.seed = seed;
    table.cave = "forest_1";
    table.floor = 1;
    table.chokes.push_back({ "choke_0", chokeHazard, 0 });
    table.leaves.push_back({ "leaf_0", P2CaveHazard::Water, 1 });
    table.leaves.push_back({ "leaf_1", P2CaveHazard::Elec, 1 });
    table.treasures.push_back({ "treasure_water", P2CaveHazard::Water, "leaf_0" });
    table.treasures.push_back({ "treasure_elec", P2CaveHazard::Elec, "leaf_1" });
    return table;
}

static const P2CaveItemRecord* itemById(const P2CavePlacementPlan& plan, const std::string& id)
{
    for (const P2CaveItemRecord& item : plan.items)
        if (item.id == id)
            return &item;
    return nullptr;
}

static const P2CaveGateRecord* gateByDoor(const P2CavePlacementPlan& plan, const std::string& door)
{
    for (const P2CaveGateRecord& gate : plan.gates)
        if (gate.door == door)
            return &gate;
    return nullptr;
}

static bool contains(const std::vector<std::string>& haystack, const std::string& needle)
{
    for (const std::string& entry : haystack)
        if (entry.find(needle) != std::string::npos)
            return true;
    return false;
}

int main()
{
    const P2CaveFloorTable water = forestFloor1(20771, P2CaveHazard::Water);
    const P2CaveFloorTable elec  = forestFloor1(42209, P2CaveHazard::Elec);

    for (const P2CaveFloorTable& table : { water, elec }) {
        assert(p2CaveValidateFloorTable(table).empty());
        P2CavePlacementPlan plan = p2CavePlanPlacement(table, { "gem_a", "gem_b" });
        std::vector<std::string> violations = p2CaveValidatePlacement(plan);
        assert(violations.empty());

        // Tagged treasures land on the matching-hazard leaf; untagged on normal.
        const P2CaveItemRecord* taggedWater = itemById(plan, "treasure_water");
        const P2CaveItemRecord* taggedElec  = itemById(plan, "treasure_elec");
        const P2CaveItemRecord* gem         = itemById(plan, "gem_a");
        assert(taggedWater && taggedWater->leafSlot && taggedWater->leaf == "leaf_0" && taggedWater->hazard == P2CaveHazard::Water);
        assert(taggedElec && taggedElec->leafSlot && taggedElec->leaf == "leaf_1" && taggedElec->hazard == P2CaveHazard::Elec);
        assert(gem && !gem->leafSlot && gem->leaf == "none" && gem->hazard == P2CaveHazard::None);

        // The elec leaf door is electrified; the water leaf is not; the choke
        // carries a gate only when it is an electric gate; no segment gates.
        const P2CaveGateRecord* elecDoor  = gateByDoor(plan, "leaf_1");
        const P2CaveGateRecord* waterDoor = gateByDoor(plan, "leaf_0");
        const P2CaveGateRecord* chokeDoor = gateByDoor(plan, "choke_0");
        assert(elecDoor && elecDoor->doorClass == P2CaveDoorClass::Leaf && elecDoor->gate == P2CaveHazard::Elec);
        assert(waterDoor && waterDoor->doorClass == P2CaveDoorClass::Leaf && waterDoor->gate == P2CaveHazard::None);
        assert(chokeDoor && chokeDoor->doorClass == P2CaveDoorClass::Choke);
        assert(chokeDoor->gate == (table.chokes[0].hazard == P2CaveHazard::Elec ? P2CaveHazard::Elec : P2CaveHazard::None));
        for (const P2CaveGateRecord& gate : plan.gates)
            assert(gate.doorClass != P2CaveDoorClass::Segment);

        for (const P2CaveItemRecord& item : plan.items)
            std::puts(p2CaveFormatItem(item).c_str());
        for (const P2CaveGateRecord& gate : plan.gates)
            std::puts(p2CaveFormatGate(gate).c_str());
    }

    // Seed determinism: the two frozen tables differ.
    P2CavePlacementPlan first  = p2CavePlanPlacement(water);
    P2CavePlacementPlan second = p2CavePlanPlacement(elec);
    assert(first.items[0].seed != second.items[0].seed);
    assert(gateByDoor(first, "choke_0")->gate != gateByDoor(second, "choke_0")->gate);

    // Rejection: a tag/leaf mismatch is refused by the table validator.
    P2CaveFloorTable bad = forestFloor1(20771, P2CaveHazard::Water);
    bad.treasures[0].leaf = "leaf_1";
    assert(contains(p2CaveValidateFloorTable(bad), "treasure_water"));

    // Rejection: a gate on a segment door, an unelectrified elec leaf, and a
    // gate on an unrequired door are all flagged.
    P2CavePlacementPlan invalid;
    invalid.items.push_back({ 1, 20771, "treasure_elec", P2CaveHazard::Elec, true, "leaf_1", P2CaveHazard::Elec });
    invalid.gates.push_back({ 1, 20771, "segment_0", P2CaveDoorClass::Segment, P2CaveHazard::None, true });
    invalid.gates.push_back({ 1, 20771, "leaf_1", P2CaveDoorClass::Leaf, P2CaveHazard::None, true });
    invalid.gates.push_back({ 1, 20771, "leaf_0", P2CaveDoorClass::Leaf, P2CaveHazard::Elec, false });
    std::vector<std::string> rejects = p2CaveValidatePlacement(invalid);
    assert(contains(rejects, "segment_0"));
    assert(contains(rejects, "elec leaf leaf_1"));
    assert(contains(rejects, "unrequired door leaf_0"));

    // Rejection: an untagged treasure must not occupy a leaf.
    P2CavePlacementPlan loose;
    loose.items.push_back({ 1, 20771, "gem_c", P2CaveHazard::None, true, "leaf_0", P2CaveHazard::None });
    assert(contains(p2CaveValidatePlacement(loose), "gem_c"));

    std::puts("PASS cave item/gate placement: tagged water/elec leaves, elec leaf door gate, segment/unrequired rejections across 2 seeds");
    return 0;
}
