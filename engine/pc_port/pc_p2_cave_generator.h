#pragma once
// Lane 41 (#480, cave wave #468): the native cave-generator port.
//
// This is the single engine-side consumer that turns a frozen lane-34 canonical
// per-floor table (``p2-cave-floor-table-v1``) into an observed floor layout.
// It ports the parts of the decomp's MapUnitGenerator / RandMapUnit /
// RandItemUnit / RandGateUnit pipeline that the #468 model needs, over the
// already-landed wave policies:
//
//   * unit-pool partition + seeded RNG          -- pc_p2_cave_growth.h (lane 35)
//   * tagged/untagged item + gate placement     -- pc_p2_cave_item_gate_placement.h (lane 37)
//   * candypop bud slot constraint              -- pc_p2_cave_bud_policy.h (lane 38)
//
// The generator realizes the seeded structural table exactly: segments and the
// chokes between them are grown in table order (phase A -> forced choke ->
// phase B from the choke's far door -> hole in the last segment), so each choke
// is on every path to the hole by construction. Leaves and buds attach to their
// seeded segment as single-door dead ends. Only geometry (unit selection, door
// budget, untagged item host) rerolls with the salt; the table never does.
//
// It adds the retry loop the decomp only has as a 500-iteration fall-through:
// a salt whose door budget cannot host the forced leaves/buds is discarded and
// the next salt is tried; when every salt fails the floor is rejected (a real
// "retry rather than ship a tableless layout", acceptance item 6).
//
// Engine-free header: no engine includes, no globals. The engine consumer and
// the one-consumer test both include it.
#include "pc_p2_cave_growth.h"
#include "pc_p2_cave_item_gate_placement.h"
#include "pc_p2_cave_bud_policy.h"

#include <cstdint>
#include <istream>
#include <ostream>
#include <string>
#include <utility>
#include <vector>

// ---------------------------------------------------------------------------
// Canonical table (lane 34, ``p2-cave-floor-table-v1``)
// ---------------------------------------------------------------------------

struct P2CaveCanonicalSegment {
    std::string slot_id;
    int index = 0;
};

struct P2CaveCanonicalChoke {
    std::string slot_id;
    int index = 0;
    int after_segment = 0;
    int before_segment = 0;
    P2CaveHazard hazard = P2CaveHazard::None;
    std::string kind;
    std::string hardness;
    std::string unit;
};

struct P2CaveCanonicalLeaf {
    std::string slot_id;
    int index = 0;
    int segment = 0;
    P2CaveHazard hazard = P2CaveHazard::None;
    int item_slots = 1;
};

struct P2CaveCanonicalBud {
    std::string slot_id;
    int index = 0;
    int segment = 0;
    std::string species;
    int count = 0;
};

struct P2CaveCanonicalTreasure {
    std::string treasure_id;
    std::string slot_id;
    int segment = 0;
    P2CaveHazard leaf_hazard = P2CaveHazard::None;
};

struct P2CaveCanonicalTable {
    int schema = 1;
    std::uint64_t seed = 0;
    std::string seed_token;
    std::string cave_id;
    int floor = 0;
    std::string unit_pool;
    std::vector<std::string> unit_candidates;
    std::vector<P2CaveCanonicalSegment> segments;
    std::vector<P2CaveCanonicalChoke> chokes;
    std::vector<P2CaveCanonicalLeaf> leaves;
    std::vector<P2CaveCanonicalBud> buds;
    std::vector<P2CaveCanonicalTreasure> treasures;
    std::vector<std::string> loose_treasures;
    int hole_segment = 0;
};

struct P2CaveObservedNode {
    std::string id;
    std::string kind;
    std::string hazard;  // empty for segment/hole nodes
    int segment_index = 0;
    std::string unit;
    std::vector<std::string> items;
};

struct P2CaveObservedLayout {
    std::string source = "engine";
    std::uint64_t seed = 0;
    int seed32 = 0;
    std::string cave;
    int floor = 0;
    std::vector<P2CaveObservedNode> nodes;
    std::vector<std::pair<std::string, std::string>> edges;
    std::string entrance;
    std::string hole;
    int salt = 0;
    int attempts = 1;
};

// ---------------------------------------------------------------------------
// canonical table helpers
// ---------------------------------------------------------------------------

inline const char* p2CaveHazardToken(P2CaveHazard hazard)
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

inline P2CaveHazard p2CaveHazardFromToken(const std::string& token)
{
    if (token == "water") {
        return P2CaveHazard::Water;
    }
    if (token == "elec") {
        return P2CaveHazard::Elec;
    }
    if (token == "fire") {
        return P2CaveHazard::Fire;
    }
    if (token == "poison") {
        return P2CaveHazard::Poison;
    }
    return P2CaveHazard::None;
}

// Candypop species -> the hazard that species is the alternate key for. Purple
// has no hazard (it is a capability bud, lane 11), so it maps to None.
inline P2CaveHazard p2CaveHazardFromSpecies(const std::string& species)
{
    if (species == "blue") {
        return P2CaveHazard::Water;
    }
    if (species == "yellow") {
        return P2CaveHazard::Elec;
    }
    if (species == "red") {
        return P2CaveHazard::Fire;
    }
    if (species == "white") {
        return P2CaveHazard::Poison;
    }
    return P2CaveHazard::None;
}

// The decomp marks room units kind 1 and corridors kind 2; the wave policies use
// the same convention (pc_p2_cave_growth.h). Only used for reporting.
inline int p2CaveCanonicalChokeCount(const P2CaveCanonicalTable& table, int before_segment)
{
    int total = 0;
    for (const P2CaveCanonicalChoke& choke : table.chokes) {
        if (choke.before_segment == before_segment) {
            total++;
        }
    }
    return total;
}

// Lane 34's fail-closed validator, re-checked natively before generation.
inline std::vector<std::string> p2CaveValidateCanonical(const P2CaveCanonicalTable& table)
{
    std::vector<std::string> violations;
    if (table.schema != 1) {
        violations.push_back("unsupported canonical cave schema");
    }
    if (table.cave_id.empty() || table.cave_id.find(':') != std::string::npos) {
        violations.push_back("invalid cave id");
    }
    if (table.floor < 1) {
        violations.push_back("invalid floor");
    }
    if (table.seed_token.empty() && table.seed == 0) {
        violations.push_back("missing seed");
    }
    if (table.segments.size() < 2) {
        violations.push_back("at least two segments are required");
    }
    for (std::size_t index = 0; index < table.segments.size(); index++) {
        if (table.segments[index].index != static_cast<int>(index)) {
            violations.push_back("segment index is not the list position");
        }
        if (table.segments[index].slot_id.empty()) {
            violations.push_back("segment without a slot id");
        }
    }
    const int segment_count = static_cast<int>(table.segments.size());
    for (std::size_t index = 0; index < table.chokes.size(); index++) {
        const P2CaveCanonicalChoke& choke = table.chokes[index];
        if (choke.index != static_cast<int>(index)) {
            violations.push_back("choke index is not the list position");
        }
        if (choke.hazard == P2CaveHazard::None) {
            violations.push_back("choke without a hazard");
        }
        if (choke.before_segment != choke.after_segment + 1) {
            violations.push_back("choke does not join adjacent segments");
        }
        if (choke.before_segment < 1 || choke.before_segment >= segment_count) {
            violations.push_back("choke references an unknown segment");
        }
        if (choke.unit.empty()) {
            violations.push_back("choke without a unit");
        }
    }
    for (std::size_t index = 0; index < table.leaves.size(); index++) {
        const P2CaveCanonicalLeaf& leaf = table.leaves[index];
        if (leaf.index != static_cast<int>(index)) {
            violations.push_back("leaf index is not the list position");
        }
        if (leaf.hazard == P2CaveHazard::None) {
            violations.push_back("leaf without a hazard");
        }
        if (leaf.segment < 0 || leaf.segment >= segment_count) {
            violations.push_back("leaf references an unknown segment");
        }
        if (leaf.item_slots != 1) {
            violations.push_back("a leaf carries exactly one item slot");
        }
    }
    for (const P2CaveCanonicalBud& bud : table.buds) {
        if (bud.segment < 0 || bud.segment >= segment_count) {
            violations.push_back("bud references an unknown segment");
        }
        if (bud.count < 1) {
            violations.push_back("bud conversion count must be positive");
        }
    }
    if (table.hole_segment != segment_count - 1) {
        violations.push_back("hole must be the last segment");
    }
    for (const P2CaveCanonicalTreasure& treasure : table.treasures) {
        if (treasure.leaf_hazard == P2CaveHazard::None) {
            violations.push_back("treasure without a leaf hazard");
        }
    }
    return violations;
}

// Parse the engine->generator text form. The host reconcile tool writes it so
// the native side never links a JSON parser. Grammar (tokens whitespace
// separated, sections fixed order):
//
//   P2_CAVE_FLOOR_V1
//   seed <uint64>
//   cave <id>
//   floor <int>
//   unit_pool <token|->
//   segments <n>          then n lines:   <slot_id> <index>
//   chokes <n>            then n lines:   <slot_id> <index> <after> <before> <hazard> <kind> <hardness> <unit>
//   leaves <n>            then n lines:   <slot_id> <index> <segment> <hazard> <item_slots>
//   buds <n>              then n lines:   <slot_id> <index> <segment> <species> <count>
//   treasures <n>         then n lines:   <treasure_id> <slot_id> <segment> <hazard>
//   loose <n>             then n lines:   <treasure_id>
//   hole <segment>
inline bool p2CaveParseCanonical(std::istream& in, P2CaveCanonicalTable& table, std::string& error)
{
    std::string header;
    if (!(in >> header) || header != "P2_CAVE_FLOOR_V1") {
        error = "missing P2_CAVE_FLOOR_V1 header";
        return false;
    }
    if (!(in >> header) || header != "seed") {
        error = "expected seed";
        return false;
    }
    if (!(in >> table.seed)) {
        error = "malformed seed";
        return false;
    }
    if (!(in >> header >> table.cave_id) || header != "cave") {
        error = "expected cave";
        return false;
    }
    if (!(in >> header >> table.floor) || header != "floor") {
        error = "expected floor";
        return false;
    }
    if (!(in >> header >> table.unit_pool) || header != "unit_pool") {
        error = "expected unit_pool";
        return false;
    }
    table.seed_token = std::to_string(table.seed);

    int count = 0;
    if (!(in >> header >> count) || header != "segments" || count < 0) {
        error = "expected segments";
        return false;
    }
    for (int i = 0; i < count; i++) {
        P2CaveCanonicalSegment segment;
        if (!(in >> segment.slot_id >> segment.index)) {
            error = "malformed segment row";
            return false;
        }
        table.segments.push_back(segment);
    }
    if (!(in >> header >> count) || header != "chokes" || count < 0) {
        error = "expected chokes";
        return false;
    }
    for (int i = 0; i < count; i++) {
        P2CaveCanonicalChoke choke;
        std::string hazard;
        if (!(in >> choke.slot_id >> choke.index >> choke.after_segment >> choke.before_segment >> hazard
              >> choke.kind >> choke.hardness >> choke.unit)) {
            error = "malformed choke row";
            return false;
        }
        choke.hazard = p2CaveHazardFromToken(hazard);
        table.chokes.push_back(choke);
    }
    if (!(in >> header >> count) || header != "leaves" || count < 0) {
        error = "expected leaves";
        return false;
    }
    for (int i = 0; i < count; i++) {
        P2CaveCanonicalLeaf leaf;
        std::string hazard;
        if (!(in >> leaf.slot_id >> leaf.index >> leaf.segment >> hazard >> leaf.item_slots)) {
            error = "malformed leaf row";
            return false;
        }
        leaf.hazard = p2CaveHazardFromToken(hazard);
        table.leaves.push_back(leaf);
    }
    if (!(in >> header >> count) || header != "buds" || count < 0) {
        error = "expected buds";
        return false;
    }
    for (int i = 0; i < count; i++) {
        P2CaveCanonicalBud bud;
        if (!(in >> bud.slot_id >> bud.index >> bud.segment >> bud.species >> bud.count)) {
            error = "malformed bud row";
            return false;
        }
        table.buds.push_back(bud);
    }
    if (!(in >> header >> count) || header != "treasures" || count < 0) {
        error = "expected treasures";
        return false;
    }
    for (int i = 0; i < count; i++) {
        P2CaveCanonicalTreasure treasure;
        std::string hazard;
        if (!(in >> treasure.treasure_id >> treasure.slot_id >> treasure.segment >> hazard)) {
            error = "malformed treasure row";
            return false;
        }
        treasure.leaf_hazard = p2CaveHazardFromToken(hazard);
        table.treasures.push_back(treasure);
    }
    if (!(in >> header >> count) || header != "loose" || count < 0) {
        error = "expected loose";
        return false;
    }
    for (int i = 0; i < count; i++) {
        std::string id;
        if (!(in >> id)) {
            error = "malformed loose row";
            return false;
        }
        table.loose_treasures.push_back(id);
    }
    if (!(in >> header >> table.hole_segment) || header != "hole") {
        error = "expected hole";
        return false;
    }
    return true;
}

inline void p2CaveWriteCanonical(std::ostream& out, const P2CaveCanonicalTable& table)
{
    out << "P2_CAVE_FLOOR_V1\n";
    out << "seed " << table.seed << "\n";
    out << "cave " << table.cave_id << "\n";
    out << "floor " << table.floor << "\n";
    out << "unit_pool " << (table.unit_pool.empty() ? "-" : table.unit_pool) << "\n";
    out << "segments " << table.segments.size() << "\n";
    for (const P2CaveCanonicalSegment& segment : table.segments) {
        out << segment.slot_id << ' ' << segment.index << "\n";
    }
    out << "chokes " << table.chokes.size() << "\n";
    for (const P2CaveCanonicalChoke& choke : table.chokes) {
        out << choke.slot_id << ' ' << choke.index << ' ' << choke.after_segment << ' ' << choke.before_segment << ' '
            << p2CaveHazardToken(choke.hazard) << ' ' << choke.kind << ' ' << choke.hardness << ' ' << choke.unit << "\n";
    }
    out << "leaves " << table.leaves.size() << "\n";
    for (const P2CaveCanonicalLeaf& leaf : table.leaves) {
        out << leaf.slot_id << ' ' << leaf.index << ' ' << leaf.segment << ' ' << p2CaveHazardToken(leaf.hazard) << ' '
            << leaf.item_slots << "\n";
    }
    out << "buds " << table.buds.size() << "\n";
    for (const P2CaveCanonicalBud& bud : table.buds) {
        out << bud.slot_id << ' ' << bud.index << ' ' << bud.segment << ' ' << bud.species << ' ' << bud.count << "\n";
    }
    out << "treasures " << table.treasures.size() << "\n";
    for (const P2CaveCanonicalTreasure& treasure : table.treasures) {
        out << treasure.treasure_id << ' ' << treasure.slot_id << ' ' << treasure.segment << ' '
            << p2CaveHazardToken(treasure.leaf_hazard) << "\n";
    }
    out << "loose " << table.loose_treasures.size() << "\n";
    for (const std::string& id : table.loose_treasures) {
        out << id << "\n";
    }
    out << "hole " << table.hole_segment << "\n";
}

// ---------------------------------------------------------------------------
// generation
// ---------------------------------------------------------------------------

inline std::string p2CaveGateId(const std::string& door_id)
{
    return "gate:" + door_id;
}

// One generation attempt at the given salt. Returns false when this salt's
// geometry cannot host the forced slots (the caller retries a new salt).
inline bool p2CaveGenerateAttempt(const P2CaveCanonicalTable& table, int salt, P2CaveObservedLayout& out,
                                  std::string& error)
{
    const int segment_count = static_cast<int>(table.segments.size());
    if (segment_count < 2) {
        error = "table has no trunk";
        return false;
    }
    P2CaveRng rng(p2_cave_seed(table.seed, table.floor, salt));

    out = P2CaveObservedLayout{};
    out.source = "engine";
    out.seed = table.seed;
    out.seed32 = static_cast<int>(table.seed);
    out.cave = table.cave_id;
    out.floor = table.floor;
    out.salt = salt;

    // Door budget per trunk segment (geometry): the decomp's mDoorCount comes
    // from the chosen units, so it rerolls with the salt.
    std::vector<int> segment_node(segment_count, -1);
    std::vector<int> capacity(segment_count, 0);
    for (int segment = 0; segment < segment_count; segment++) {
        capacity[segment] = 2 + rng.below(3);
    }

    auto push_node = [&](const std::string& id, const std::string& kind, const std::string& hazard, int segment_index,
                         const std::string& unit) -> int {
        P2CaveObservedNode node;
        node.id = id;
        node.kind = kind;
        node.hazard = hazard;
        node.segment_index = segment_index;
        node.unit = unit;
        out.nodes.push_back(node);
        return static_cast<int>(out.nodes.size()) - 1;
    };
    auto connect = [&](int a, int b) { out.edges.push_back({out.nodes[a].id, out.nodes[b].id}); };

    // Phase A: entry segment.
    auto pick_unit = [&](const std::string& fallback) -> std::string {
        if (table.unit_candidates.empty()) {
            return fallback;
        }
        return table.unit_candidates[static_cast<std::size_t>(rng.below(static_cast<int>(table.unit_candidates.size())))];
    };

    segment_node[0] = push_node(table.segments[0].slot_id, "segment", "", 0, pick_unit(table.unit_pool));
    out.entrance = out.nodes[segment_node[0]].id;
    int frontier = segment_node[0];

    std::vector<int> trunk_degree(segment_count, 0);

    for (int segment = 1; segment < segment_count; segment++) {
        // Forced choke(s) between segment-1 and segment, attached to the far
        // door of the previous phase. Order is the frozen table order.
        for (const P2CaveCanonicalChoke& choke : table.chokes) {
            if (choke.before_segment != segment) {
                continue;
            }
            const std::string unit = choke.unit.empty() ? pick_unit(choke.slot_id) : choke.unit;
            const int node = push_node(choke.slot_id, "choke", p2CaveHazardToken(choke.hazard), segment, unit);
            connect(frontier, node);
            frontier = node;
        }
        trunk_degree[segment - 1] += 1;
        segment_node[segment] = push_node(table.segments[segment].slot_id, "segment", "", segment,
                                          pick_unit(table.unit_pool));
        connect(frontier, segment_node[segment]);
        trunk_degree[segment] += 1;
        frontier = segment_node[segment];
    }
    out.hole = out.nodes[segment_node[segment_count - 1]].id;

    // Leaves attach as single-door dead ends to their seeded segment.
    std::vector<int> door_use(segment_count, 0);
    for (int segment = 0; segment < segment_count; segment++) {
        door_use[segment] = trunk_degree[segment];
    }
    std::vector<int> leaf_node;
    leaf_node.reserve(table.leaves.size());
    for (const P2CaveCanonicalLeaf& leaf : table.leaves) {
        const int segment = leaf.segment;
        if (segment < 0 || segment >= segment_count) {
            error = "leaf references an unknown segment";
            return false;
        }
        if (door_use[segment] + 1 > capacity[segment]) {
            error = "no free door for leaf " + leaf.slot_id;
            return false;
        }
        door_use[segment] += 1;
        const int node = push_node(leaf.slot_id, "leaf", p2CaveHazardToken(leaf.hazard), segment,
                                   pick_unit(leaf.slot_id));
        connect(segment_node[segment], node);
        leaf_node.push_back(node);
    }

    // Bud slots attach to their seeded segment (dead end), reusing the lane-38
    // constraint: a bud may never sit behind the colour it provides.
    {
        std::vector<int> gates(segment_count, 0);
        for (int segment = 1; segment < segment_count; segment++) {
            int mask = gates[segment - 1];
            for (const P2CaveCanonicalChoke& choke : table.chokes) {
                if (choke.before_segment != segment) {
                    continue;
                }
                switch (choke.hazard) {
                case P2CaveHazard::Water:
                    mask |= p2cavebud::colourBit(0);
                    break;
                case P2CaveHazard::Elec:
                    mask |= p2cavebud::colourBit(2);
                    break;
                case P2CaveHazard::Fire:
                    mask |= p2cavebud::colourBit(1);
                    break;
                case P2CaveHazard::Poison:
                    mask |= p2cavebud::colourBit(4);
                    break;
                default:
                    break;
                }
            }
            gates[segment] = mask;
        }
        std::vector<p2cavebud::BudSlot> buds;
        for (const P2CaveCanonicalBud& bud : table.buds) {
            p2cavebud::BudSlot slot;
            slot.segment = bud.segment;
            slot.colour = p2cavebud::ColourCount;  // unknown -> validated below
            if (bud.species == "blue") {
                slot.colour = 0;
            } else if (bud.species == "red") {
                slot.colour = 1;
            } else if (bud.species == "yellow") {
                slot.colour = 2;
            } else if (bud.species == "purple") {
                slot.colour = 3;
            } else if (bud.species == "white") {
                slot.colour = 4;
            }
            slot.conversionCount = bud.count;
            buds.push_back(slot);
        }
        if (!buds.empty()) {
            const std::vector<p2cavebud::Violation> violations = p2cavebud::validatePlacement(buds, gates);
            if (!violations.empty()) {
                error = std::string("bud table rejected: ") + p2cavebud::violationName(violations.front());
                return false;
            }
        }
        for (std::size_t index = 0; index < table.buds.size(); index++) {
            const P2CaveCanonicalBud& bud = table.buds[index];
            const int segment = bud.segment;
            if (segment < 0 || segment >= segment_count) {
                error = "bud references an unknown segment";
                return false;
            }
            if (door_use[segment] + 1 > capacity[segment]) {
                error = "no free door for bud " + bud.slot_id;
                return false;
            }
            door_use[segment] += 1;
            const int node = push_node(bud.slot_id, "bud", p2CaveHazardToken(p2CaveHazardFromSpecies(bud.species)),
                                       segment, pick_unit(bud.slot_id));
            connect(segment_node[segment], node);
        }
    }

    // Tagged item placement through the lane-37 routine; untagged items use the
    // normal segment pool. The lane-37 table uses the choke's gated segment.
    P2CaveFloorTable floor_table;
    floor_table.seed = static_cast<int>(table.seed);
    floor_table.cave = table.cave_id;
    floor_table.floor = table.floor;
    for (const P2CaveCanonicalChoke& choke : table.chokes) {
        P2CaveChoke record;
        record.id = choke.slot_id;
        record.hazard = choke.hazard;
        record.segment = choke.before_segment;
        floor_table.chokes.push_back(record);
    }
    for (const P2CaveCanonicalLeaf& leaf : table.leaves) {
        P2CaveLeaf record;
        record.id = leaf.slot_id;
        record.hazard = leaf.hazard;
        record.segment = leaf.segment;
        floor_table.leaves.push_back(record);
    }
    for (const P2CaveCanonicalTreasure& treasure : table.treasures) {
        P2CaveTaggedTreasure record;
        record.id = treasure.treasure_id;
        record.tag = treasure.leaf_hazard;
        record.leaf = treasure.slot_id;
        floor_table.treasures.push_back(record);
    }
    const std::vector<P2CaveItemRecord> items = p2CavePlanItemSlots(floor_table, table.loose_treasures);
    int loose_host = -1;
    for (const P2CaveItemRecord& item : items) {
        const bool tagged = item.tag != P2CaveHazard::None;
        int host = -1;
        if (tagged) {
            for (std::size_t index = 0; index < table.leaves.size(); index++) {
                if (table.leaves[index].slot_id == item.leaf) {
                    host = leaf_node[index];
                    break;
                }
            }
        } else {
            if (loose_host < 0) {
                loose_host = segment_node[rng.below(segment_count)];
            }
            host = loose_host;
        }
        if (host < 0) {
            error = "cannot host item " + item.id;
            return false;
        }
        out.nodes[host].items.push_back(item.id);
    }

    // Gates only on choke/leaf doors, from the lane-37 planner.
    const std::vector<P2CaveGateRecord> gates = p2CavePlanGateDoors(floor_table);
    for (const P2CaveGateRecord& gate : gates) {
        if (gate.gate == P2CaveHazard::None) {
            continue;
        }
        int segment_index = 0;
        int host = -1;
        if (gate.doorClass == P2CaveDoorClass::Choke) {
            for (const P2CaveObservedNode& node : out.nodes) {
                if (node.kind == "choke" && node.id == gate.door) {
                    host = static_cast<int>(&node - &out.nodes[0]);
                    segment_index = node.segment_index;
                    break;
                }
            }
        } else {
            for (std::size_t index = 0; index < table.leaves.size(); index++) {
                if (table.leaves[index].slot_id == gate.door) {
                    host = leaf_node[index];
                    segment_index = table.leaves[index].segment;
                    break;
                }
            }
        }
        if (host < 0) {
            error = "cannot host gate on " + gate.door;
            return false;
        }
        const int node = push_node(p2CaveGateId(gate.door), "gate", p2CaveHazardName(gate.gate), segment_index, "");
        connect(host, node);
        (void)segment_index;
    }

    return true;
}

// Retry loop the decomp lacks: a salt whose geometry cannot host the forced
// slots is discarded; after `max_attempts` salts the floor is rejected.
inline bool p2CaveGenerateWithRetry(const P2CaveCanonicalTable& table, int max_attempts, P2CaveObservedLayout& out,
                                    int& attempts, std::string& error)
{
    if (max_attempts < 1) {
        max_attempts = 1;
    }
    std::string last;
    for (int salt = 0; salt < max_attempts; salt++) {
        if (p2CaveGenerateAttempt(table, salt, out, last)) {
            attempts = salt + 1;
            out.attempts = attempts;
            return true;
        }
    }
    attempts = max_attempts;
    error = "floor rejected after " + std::to_string(max_attempts) + " retries: " + last;
    return false;
}

// ---------------------------------------------------------------------------
// evidence emitters
// ---------------------------------------------------------------------------

inline std::string p2CaveEscape(const std::string& text)
{
    std::string escaped;
    escaped.reserve(text.size());
    for (char ch : text) {
        if (ch == '"' || ch == '\\') {
            escaped.push_back('\\');
        }
        escaped.push_back(ch);
    }
    return escaped;
}

inline std::string p2CaveLayoutJson(const P2CaveObservedLayout& layout)
{
    std::string json;
    json += "{\n";
    json += "  \"schema\": \"p2-cave-observed-layout/1\",\n";
    json += "  \"source\": \"" + p2CaveEscape(layout.source) + "\",\n";
    json += "  \"seed\": " + std::to_string(layout.seed) + ",\n";
    json += "  \"cave\": \"" + p2CaveEscape(layout.cave) + "\",\n";
    json += "  \"floor\": " + std::to_string(layout.floor) + ",\n";
    json += "  \"entrance\": \"" + p2CaveEscape(layout.entrance) + "\",\n";
    json += "  \"hole\": \"" + p2CaveEscape(layout.hole) + "\",\n";
    json += "  \"nodes\": [\n";
    for (std::size_t index = 0; index < layout.nodes.size(); index++) {
        const P2CaveObservedNode& node = layout.nodes[index];
        json += "    {\"id\": \"" + p2CaveEscape(node.id) + "\", \"kind\": \"" + p2CaveEscape(node.kind) + "\"";
        if (!node.hazard.empty()) {
            json += ", \"hazard\": \"" + p2CaveEscape(node.hazard) + "\"";
        }
        json += ", \"segment_index\": " + std::to_string(node.segment_index);
        json += ", \"items\": [";
        for (std::size_t item = 0; item < node.items.size(); item++) {
            if (item) {
                json += ", ";
            }
            json += "\"" + p2CaveEscape(node.items[item]) + "\"";
        }
        json += "]}";
        if (index + 1 != layout.nodes.size()) {
            json += ",";
        }
        json += "\n";
    }
    json += "  ],\n";
    json += "  \"edges\": [\n";
    for (std::size_t index = 0; index < layout.edges.size(); index++) {
        json += "    [\"" + p2CaveEscape(layout.edges[index].first) + "\", \"" + p2CaveEscape(layout.edges[index].second)
                + "\"]";
        if (index + 1 != layout.edges.size()) {
            json += ",";
        }
        json += "\n";
    }
    json += "  ]\n";
    json += "}\n";
    return json;
}

// Engine-facing facade: read the host-written P2_CAVE_FLOOR_V1 table, run the
// retry loop and return the observed-layout JSON plus its one-line marker.
bool pc_p2_cave_generate_file(const std::string& table_path, int max_attempts, std::string& layout_json,
                              std::string& marker, std::string& error);

inline std::string p2CaveLayoutMarker(const P2CaveObservedLayout& layout)
{
    int chokes = 0;
    int leaves = 0;
    int buds = 0;
    int gates = 0;
    for (const P2CaveObservedNode& node : layout.nodes) {
        chokes += node.kind == "choke" ? 1 : 0;
        leaves += node.kind == "leaf" ? 1 : 0;
        buds += node.kind == "bud" ? 1 : 0;
        gates += node.kind == "gate" ? 1 : 0;
    }
    return "P2_CAVE_GEN source=" + layout.source + " cave=" + layout.cave + " floor="
           + std::to_string(layout.floor) + " seed=" + std::to_string(layout.seed)
           + " segments=" + std::to_string(layout.nodes.size()) + " chokes=" + std::to_string(chokes)
           + " leaves=" + std::to_string(leaves) + " buds=" + std::to_string(buds) + " gates="
           + std::to_string(gates) + " entrance=" + layout.entrance + " hole=" + layout.hole + " salt="
           + std::to_string(layout.salt) + " attempts=" + std::to_string(layout.attempts);
}
