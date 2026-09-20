#pragma once
#include <algorithm>
#include <string>
#include <vector>

// Lane 37 (P2 cave wave, spec #468 / lane issue #476): tagged treasure and gate
// placement over a frozen per-floor structural table.
//
// This is the engine-free core of the native RandItemUnit::setItemSlot and
// RandGateUnit::setGateDoor port. The future MapUnitGenerator port builds a
// P2CaveFloorTable from the seeded slot data (lane 34) and calls
// p2CavePlanItemSlots / p2CavePlanGateDoors; the routine emits the
// P2_CAVE_ITEM / P2_CAVE_GATE markers through p2CaveFormatItem/p2CaveFormatGate.
//
// Rules enforced (mirroring experimental/pikmin2_cave_item_gate_placement.py):
//   * a tagged treasure is placed into the leaf whose hazard equals its tag;
//   * an untagged treasure uses the normal random pool, never a forced leaf;
//   * gates exist only on choke or leaf doors, never segment doors;
//   * an elec leaf door is electrified (the "come back with yellow" loop);
//   * no gate is present on a door the frozen table marks unrequired.

#ifndef P2_CAVE_HAZARD_ENUM_DEFINED
#define P2_CAVE_HAZARD_ENUM_DEFINED
enum class P2CaveHazard { None, Water, Elec, Fire, Poison };
#endif
enum class P2CaveDoorClass { Segment, Choke, Leaf };

struct P2CaveLeaf {
    std::string id;
    P2CaveHazard hazard;
    int segment;
};

struct P2CaveChoke {
    std::string id;
    P2CaveHazard hazard;
    int segment;
};

struct P2CaveTaggedTreasure {
    std::string id;
    P2CaveHazard tag;
    std::string leaf;
};

struct P2CaveFloorTable {
    int seed;
    std::string cave;
    int floor;
    std::vector<P2CaveChoke> chokes;
    std::vector<P2CaveLeaf> leaves;
    std::vector<P2CaveTaggedTreasure> treasures;
};

struct P2CaveItemRecord {
    int floor;
    int seed;
    std::string id;
    P2CaveHazard tag;
    bool leafSlot;
    std::string leaf;
    P2CaveHazard hazard;
};

struct P2CaveGateRecord {
    int floor;
    int seed;
    std::string door;
    P2CaveDoorClass doorClass;
    P2CaveHazard gate;
    bool required;
};

struct P2CavePlacementPlan {
    std::vector<P2CaveItemRecord> items;
    std::vector<P2CaveGateRecord> gates;
};

inline const char* p2CaveHazardName(P2CaveHazard hazard)
{
    switch (hazard) {
    case P2CaveHazard::Water:
        return "water";
    case P2CaveHazard::Elec:
        return "elec";
    case P2CaveHazard::Fire:
        return "fire";
    case P2CaveHazard::Poison:
        return "poison";
    default:
        return "none";
    }
}

inline const char* p2CaveDoorClassName(P2CaveDoorClass doorClass)
{
    switch (doorClass) {
    case P2CaveDoorClass::Choke:
        return "choke";
    case P2CaveDoorClass::Leaf:
        return "leaf";
    default:
        return "segment";
    }
}

// Validate the frozen structural table. Empty result == valid.
inline std::vector<std::string> p2CaveValidateFloorTable(const P2CaveFloorTable& table)
{
    std::vector<std::string> violations;
    if (table.seed == 0)
        violations.push_back("floor table seed must be non-zero");
    if (table.cave.empty())
        violations.push_back("floor table cave must be non-empty");
    if (table.floor <= 0)
        violations.push_back("floor table floor must be positive");
    for (const P2CaveLeaf& leaf : table.leaves) {
        if (leaf.id.empty())
            violations.push_back("leaf with empty id");
        if (leaf.hazard == P2CaveHazard::None)
            violations.push_back("leaf " + leaf.id + " has no hazard");
        for (const P2CaveLeaf& other : table.leaves)
            if (&other != &leaf && other.id == leaf.id)
                violations.push_back("duplicate leaf id " + leaf.id);
    }
    for (const P2CaveChoke& choke : table.chokes) {
        if (choke.id.empty())
            violations.push_back("choke with empty id");
        if (choke.hazard == P2CaveHazard::None)
            violations.push_back("choke " + choke.id + " has no hazard");
    }
    for (const P2CaveTaggedTreasure& treasure : table.treasures) {
        if (treasure.tag == P2CaveHazard::None)
            violations.push_back("treasure " + treasure.id + " has no tag");
        const P2CaveLeaf* bound = nullptr;
        for (const P2CaveLeaf& leaf : table.leaves)
            if (leaf.id == treasure.leaf)
                bound = &leaf;
        if (!bound) {
            violations.push_back("treasure " + treasure.id + " bound to nonexistent leaf " + treasure.leaf);
            continue;
        }
        if (bound->hazard != treasure.tag)
            violations.push_back("treasure " + treasure.id + " tag does not match leaf " + treasure.leaf + " hazard");
    }
    return violations;
}

// RandItemUnit::setItemSlot equivalent: tagged treasure into its matching leaf,
// untagged treasure into the normal random pool.
inline std::vector<P2CaveItemRecord> p2CavePlanItemSlots(const P2CaveFloorTable& table, const std::vector<std::string>& untagged)
{
    std::vector<P2CaveTaggedTreasure> tagged = table.treasures;
    std::sort(tagged.begin(), tagged.end(), [](const P2CaveTaggedTreasure& a, const P2CaveTaggedTreasure& b) { return a.id < b.id; });
    std::vector<std::string> loose = untagged;
    std::sort(loose.begin(), loose.end());

    std::vector<P2CaveItemRecord> items;
    for (const P2CaveTaggedTreasure& treasure : tagged) {
        P2CaveItemRecord record;
        record.floor     = table.floor;
        record.seed      = table.seed;
        record.id        = treasure.id;
        record.tag       = treasure.tag;
        record.leafSlot  = true;
        record.leaf      = treasure.leaf;
        record.hazard    = treasure.tag;
        items.push_back(record);
    }
    for (const std::string& id : loose) {
        P2CaveItemRecord record;
        record.floor    = table.floor;
        record.seed     = table.seed;
        record.id       = id;
        record.tag      = P2CaveHazard::None;
        record.leafSlot = false;
        record.leaf     = "none";
        record.hazard   = P2CaveHazard::None;
        items.push_back(record);
    }
    return items;
}

// RandGateUnit::setGateDoor equivalent restricted to choke/leaf doors: a choke
// door carries a gate only when the choke is itself an electric gate; a leaf
// door carries an electric gate iff the leaf is the elec alcove.
inline std::vector<P2CaveGateRecord> p2CavePlanGateDoors(const P2CaveFloorTable& table)
{
    std::vector<P2CaveGateRecord> gates;
    std::vector<P2CaveChoke> chokes = table.chokes;
    std::sort(chokes.begin(), chokes.end(), [](const P2CaveChoke& a, const P2CaveChoke& b) { return a.id < b.id; });
    for (const P2CaveChoke& choke : chokes) {
        P2CaveGateRecord record;
        record.floor     = table.floor;
        record.seed      = table.seed;
        record.door      = choke.id;
        record.doorClass = P2CaveDoorClass::Choke;
        record.gate      = (choke.hazard == P2CaveHazard::Elec) ? P2CaveHazard::Elec : P2CaveHazard::None;
        record.required  = true;
        gates.push_back(record);
    }
    std::vector<P2CaveLeaf> leaves = table.leaves;
    std::sort(leaves.begin(), leaves.end(), [](const P2CaveLeaf& a, const P2CaveLeaf& b) { return a.id < b.id; });
    for (const P2CaveLeaf& leaf : leaves) {
        bool carries = false;
        for (const P2CaveTaggedTreasure& treasure : table.treasures)
            if (treasure.leaf == leaf.id)
                carries = true;
        P2CaveGateRecord record;
        record.floor     = table.floor;
        record.seed      = table.seed;
        record.door      = leaf.id;
        record.doorClass = P2CaveDoorClass::Leaf;
        record.gate      = (leaf.hazard == P2CaveHazard::Elec) ? P2CaveHazard::Elec : P2CaveHazard::None;
        record.required  = carries;
        gates.push_back(record);
    }
    return gates;
}

inline P2CavePlacementPlan p2CavePlanPlacement(const P2CaveFloorTable& table, const std::vector<std::string>& untagged = {})
{
    P2CavePlacementPlan plan;
    plan.items = p2CavePlanItemSlots(table, untagged);
    plan.gates = p2CavePlanGateDoors(table);
    return plan;
}

// Reconcile a plan against the lane-37 rules. Empty result == valid.
inline std::vector<std::string> p2CaveValidatePlacement(const P2CavePlacementPlan& plan)
{
    std::vector<std::string> violations;
    std::vector<std::pair<std::string, P2CaveHazard>> elecLeaves;
    for (const P2CaveItemRecord& item : plan.items) {
        if (item.tag == P2CaveHazard::None) {
            if (item.leafSlot || item.leaf != "none" || item.hazard != P2CaveHazard::None)
                violations.push_back("untagged item " + item.id + " must use the normal pool, not leaf " + item.leaf);
        } else if (!item.leafSlot || item.leaf.empty() || item.leaf == "none") {
            violations.push_back("tagged item " + item.id + " must be placed in a leaf");
        } else if (item.hazard != item.tag) {
            violations.push_back("tagged item " + item.id + " hazard does not match its tag in leaf " + item.leaf);
        } else if (item.hazard == P2CaveHazard::Elec) {
            elecLeaves.push_back({ item.leaf, item.hazard });
        }
    }
    for (const P2CaveGateRecord& gate : plan.gates) {
        if (gate.doorClass == P2CaveDoorClass::Segment)
            violations.push_back("gate record on segment door " + gate.door + " is not allowed");
        if (!gate.required && gate.gate != P2CaveHazard::None)
            violations.push_back("gate present on unrequired door " + gate.door);
        if (gate.doorClass == P2CaveDoorClass::Leaf) {
            for (const std::pair<std::string, P2CaveHazard>& elec : elecLeaves)
                if (elec.first == gate.door && gate.gate != P2CaveHazard::Elec)
                    violations.push_back("elec leaf " + gate.door + " must have an elec gate");
        }
    }
    return violations;
}

inline std::string p2CaveFormatItem(const P2CaveItemRecord& record)
{
    return "P2_CAVE_ITEM floor=" + std::to_string(record.floor) + " seed=" + std::to_string(record.seed) + " id=" + record.id
           + " tag=" + p2CaveHazardName(record.tag) + " placement=" + (record.leafSlot ? "leaf" : "normal") + " leaf=" + record.leaf
           + " hazard=" + p2CaveHazardName(record.hazard);
}

inline std::string p2CaveFormatGate(const P2CaveGateRecord& record)
{
    return "P2_CAVE_GATE floor=" + std::to_string(record.floor) + " seed=" + std::to_string(record.seed) + " door=" + record.door
           + " door_class=" + p2CaveDoorClassName(record.doorClass) + " gate=" + p2CaveHazardName(record.gate)
           + " required=" + (record.required ? "1" : "0");
}
