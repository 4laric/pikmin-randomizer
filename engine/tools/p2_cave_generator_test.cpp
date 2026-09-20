// Lane 41 (#480): one-consumer gate for the native cave-generator port.
//
// Proves, over the frozen forest_1 floor-1 spike table (seed 468001):
//   * the forced water choke, water/elec leaves and elec gate are realized;
//   * the choke is on every path to the hole (graph dominance, by construction);
//   * a tagged treasure lands only in its matching-hazard leaf and an untagged
//     treasure only in a hazard-free segment;
//   * the same seed+salt reproduces the layout and different salts keep the
//     logical projection while rerolling geometry;
//   * a table whose forced units cannot be hosted is rejected after retrying.
// With argv[1]/argv[2] it also reads a host-written P2_CAVE_FLOOR_V1 table and
// writes the observed-layout JSON, which is how the engine run feeds lane 40.
#include "pc_p2_cave_generator.h"

#include <cstdio>
#include <deque>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#define CHECK(condition)                                                                  \
    do {                                                                                  \
        if (!(condition)) {                                                               \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition);     \
            return 1;                                                                     \
        }                                                                                 \
    } while (0)

static P2CaveCanonicalTable spike_table()
{
    P2CaveCanonicalTable table;
    table.schema = 1;
    table.seed = 468001;
    table.seed_token = "468001";
    table.cave_id = "forest_1";
    table.floor = 1;
    table.unit_pool = "1_units_cent3_tsuchi.txt";
    table.unit_candidates = {"way2_tsuchi", "way3_tsuchi", "wayl_tsuchi", "room_cent3_4_tsuchi"};
    table.segments.push_back({"forest_1:f1:segment:0", 0});
    table.segments.push_back({"forest_1:f1:segment:1", 1});
    P2CaveCanonicalChoke choke;
    choke.slot_id = "forest_1:f1:choke:0";
    choke.index = 0;
    choke.after_segment = 0;
    choke.before_segment = 1;
    choke.hazard = P2CaveHazard::Water;
    choke.kind = "hard";
    choke.hardness = "hard";
    choke.unit = "wayl_tsuchi";
    table.chokes.push_back(choke);
    table.leaves.push_back({"forest_1:f1:leaf:0", 0, 0, P2CaveHazard::Elec, 1});
    table.leaves.push_back({"forest_1:f1:leaf:1", 1, 1, P2CaveHazard::Water, 1});
    table.treasures.push_back({"treasure_elec", "forest_1:f1:leaf:0", 0, P2CaveHazard::Elec});
    table.treasures.push_back({"treasure_water", "forest_1:f1:leaf:1", 1, P2CaveHazard::Water});
    table.loose_treasures.push_back("juji_key_fc");
    table.hole_segment = 1;
    return table;
}

static const P2CaveObservedNode* find_node(const P2CaveObservedLayout& layout, const std::string& kind,
                                           const std::string& hazard, int segment_index)
{
    for (const P2CaveObservedNode& node : layout.nodes) {
        if (node.kind == kind && node.hazard == hazard && node.segment_index == segment_index) {
            return &node;
        }
    }
    return nullptr;
}

static bool connected_without(const P2CaveObservedLayout& layout, const std::string& removed)
{
    if (layout.entrance == removed || layout.hole == removed) {
        return false;
    }
    std::set<std::string> seen{layout.entrance};
    std::deque<std::string> queue{layout.entrance};
    while (!queue.empty()) {
        const std::string current = queue.front();
        queue.pop_front();
        if (current == layout.hole) {
            return true;
        }
        for (const std::pair<std::string, std::string>& edge : layout.edges) {
            std::string next;
            if (edge.first == current) {
                next = edge.second;
            } else if (edge.second == current) {
                next = edge.first;
            } else {
                continue;
            }
            if (next == removed || seen.count(next)) {
                continue;
            }
            seen.insert(next);
            queue.push_back(next);
        }
    }
    return false;
}

// The re-roll-stable logical projection: slot kinds, hazards and seeded segment
// indices, plus where each *tagged* treasure sits. The untagged item uses the
// normal pool and is allowed to move with the salt (it is geometry, not logic).
static std::string projection(const P2CaveObservedLayout& layout)
{
    std::ostringstream out;
    for (const P2CaveObservedNode& node : layout.nodes) {
        out << node.kind << '|' << node.hazard << '|' << node.segment_index << ';';
    }
    out << layout.entrance << '>' << layout.hole;
    for (const P2CaveObservedNode& node : layout.nodes) {
        for (const std::string& item : node.items) {
            if (item == "treasure_elec" || item == "treasure_water") {
                out << item << '@' << node.kind << node.segment_index << ';';
            }
        }
    }
    return out.str();
}

int main(int argc, char** argv)
{
    const P2CaveCanonicalTable table = spike_table();
    CHECK(p2CaveValidateCanonical(table).empty());

    P2CaveObservedLayout layout;
    int attempts = 0;
    std::string error;
    CHECK(p2CaveGenerateWithRetry(table, 8, layout, attempts, error));
    CHECK(attempts == 1);
    CHECK(layout.source == "engine");
    CHECK(layout.seed == 468001);

    // Forced slots exist.
    const P2CaveObservedNode* choke = find_node(layout, "choke", "water", 1);
    const P2CaveObservedNode* elec_leaf = find_node(layout, "leaf", "elec", 0);
    const P2CaveObservedNode* water_leaf = find_node(layout, "leaf", "water", 1);
    CHECK(choke != nullptr);
    CHECK(elec_leaf != nullptr);
    CHECK(water_leaf != nullptr);
    const P2CaveObservedNode* gate = find_node(layout, "gate", "elec", 0);
    CHECK(gate != nullptr);

    // The gate is on the elec leaf door; the water choke is not a gate.
    bool gate_on_elec_leaf = false;
    for (const std::pair<std::string, std::string>& edge : layout.edges) {
        if ((edge.first == gate->id && edge.second == elec_leaf->id)
            || (edge.second == gate->id && edge.first == elec_leaf->id)) {
            gate_on_elec_leaf = true;
        }
    }
    CHECK(gate_on_elec_leaf);

    // Tagged items in their leaves; the untagged item only in a segment.
    bool elec_tagged = false;
    bool water_tagged = false;
    bool loose_tagged = false;
    for (const P2CaveObservedNode& node : layout.nodes) {
        for (const std::string& item : node.items) {
            if (item == "treasure_elec") {
                elec_tagged = node.id == elec_leaf->id;
            }
            if (item == "treasure_water") {
                water_tagged = node.id == water_leaf->id;
            }
            if (item == "juji_key_fc") {
                loose_tagged = node.kind == "segment" && node.hazard.empty();
            }
        }
    }
    CHECK(elec_tagged);
    CHECK(water_tagged);
    CHECK(loose_tagged);

    // Choke dominance: removing it disconnects the hole, and it is present.
    CHECK(!connected_without(layout, choke->id));

    // Determinism: the same seed and salt reproduce the layout byte for byte.
    P2CaveObservedLayout repeat;
    int repeat_attempts = 0;
    CHECK(p2CaveGenerateWithRetry(table, 8, repeat, repeat_attempts, error));
    CHECK(p2CaveLayoutJson(layout) == p2CaveLayoutJson(repeat));

    // Re-roll invariance: salts change geometry but never the logical projection.
    for (int salt = 0; salt < 4; salt++) {
        P2CaveObservedLayout other;
        std::string attempt_error;
        CHECK(p2CaveGenerateAttempt(table, salt, other, attempt_error));
        CHECK(projection(other) == projection(layout));
        CHECK(!connected_without(other, find_node(other, "choke", "water", 1)->id));
    }

    // Failure handling: more forced leaves than any salt's door budget -> reject.
    P2CaveCanonicalTable impossible = table;
    impossible.leaves.clear();
    impossible.treasures.clear();
    for (int i = 0; i < 12; i++) {
        impossible.leaves.push_back({"forest_1:f1:leaf:" + std::to_string(i), i, 0, P2CaveHazard::Water, 1});
    }
    P2CaveObservedLayout rejected;
    int rejected_attempts = 0;
    std::string rejected_error;
    CHECK(!p2CaveGenerateWithRetry(impossible, 8, rejected, rejected_attempts, rejected_error));
    CHECK(rejected_attempts == 8);
    CHECK(!rejected_error.empty());

    // Bud slot class: a seeded elec bud in the entry segment becomes a bud node
    // with the species->hazard mapping the layout vocabulary needs.
    P2CaveCanonicalTable budded = table;
    P2CaveCanonicalBud bud;
    bud.slot_id = "forest_1:f1:bud:0";
    bud.index = 0;
    bud.segment = 0;
    bud.species = "yellow";
    bud.count = 5;
    budded.buds.push_back(bud);
    P2CaveObservedLayout with_bud;
    std::string bud_error;
    CHECK(p2CaveGenerateAttempt(budded, 0, with_bud, bud_error));
    CHECK(find_node(with_bud, "bud", "elec", 0) != nullptr);

    // A bud in the segment gated by its own colour is rejected (lane 38 rule).
    P2CaveCanonicalTable behind = table;
    P2CaveCanonicalBud gated;
    gated.slot_id = "forest_1:f1:bud:0";
    gated.index = 0;
    gated.segment = 1;
    gated.species = "blue";
    gated.count = 5;
    behind.buds.push_back(gated);
    P2CaveObservedLayout rejected_bud;
    std::string behind_error;
    CHECK(!p2CaveGenerateAttempt(behind, 0, rejected_bud, behind_error));

    // Canonical text round trip through the engine-facing grammar.
    std::ostringstream text;
    p2CaveWriteCanonical(text, table);
    std::istringstream back(text.str());
    P2CaveCanonicalTable parsed;
    std::string parse_error;
    CHECK(p2CaveParseCanonical(back, parsed, parse_error));
    CHECK(p2CaveValidateCanonical(parsed).empty());
    P2CaveObservedLayout parsed_layout;
    int parsed_attempts = 0;
    CHECK(p2CaveGenerateWithRetry(parsed, 8, parsed_layout, parsed_attempts, error));
    CHECK(p2CaveLayoutJson(parsed_layout) == p2CaveLayoutJson(layout));

    if (argc >= 3) {
        std::string json;
        std::string marker;
        std::string load_error;
        CHECK(pc_p2_cave_generate_file(argv[1], 8, json, marker, load_error));
        std::ofstream out(argv[2], std::ios::binary | std::ios::trunc);
        CHECK(out.good());
        out.write(json.data(), static_cast<std::streamsize>(json.size()));
        out.close();
        std::puts(marker.c_str());
    }

    std::puts("PASS p2 cave generator: forced choke/leaves/gate, choke dominance, "
              "tagged vs untagged placement, bud slot mapping and own-gate rejection, "
              "seed determinism, reroll invariance, retry rejection");
    return 0;
}
