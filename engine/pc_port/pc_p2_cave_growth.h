#pragma once
// Lane 35 engine-free unit-pool partition + phased trunk growth (#474).
// Mirrors experimental/pikmin2_cave_growth.py; consumed by the eventual
// cave generator port. Header-only, no engine dependencies.
#include <cstdint>

enum class P2CaveSlot { Segment, Choke, Leaf, Excluded };
#ifndef P2_CAVE_HAZARD_ENUM_DEFINED
#define P2_CAVE_HAZARD_ENUM_DEFINED
enum class P2CaveHazard { None, Water, Elec, Fire, Poison };
#endif

struct P2CaveUnit {
    const char* name;
    int kind;
    int door_count;
    int door_direction[6];
};

struct P2CavePool {
    int count = 0;
    P2CaveUnit units[16] = {};
    P2CaveHazard hazard[16] = {};
};

inline P2CaveSlot p2_cave_slot(const P2CaveUnit& unit, P2CaveHazard hazard) {
    if (unit.door_count == 0) return P2CaveSlot::Excluded;
    if (unit.door_count == 1) return P2CaveSlot::Leaf;
    if (hazard != P2CaveHazard::None) return P2CaveSlot::Choke;
    return P2CaveSlot::Segment;
}

inline int p2_cave_partition_count(const P2CavePool& pool, P2CaveSlot slot) {
    int total = 0;
    for (int i = 0; i < pool.count; i++)
        if (p2_cave_slot(pool.units[i], pool.hazard[i]) == slot) total++;
    return total;
}

struct P2CaveNode { int unit; P2CaveSlot slot; int rotation; };
struct P2CaveEdge { int a; int a_door; int b; int b_door; };

struct P2CaveLayout {
    static constexpr int MAX_NODES = 24;
    int node_count = 0;
    int edge_count = 0;
    P2CaveNode nodes[MAX_NODES] = {};
    P2CaveEdge edges[MAX_NODES] = {};
    int entry = 0;
    int hole_host = 0;
};

class P2CaveRng {
public:
    explicit P2CaveRng(std::uint64_t seed) : state_(seed) {}
    std::uint64_t next_u64() {
        state_ += 0x9E3779B97F4A7C15ULL;
        std::uint64_t value = state_;
        value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9ULL;
        value = (value ^ (value >> 27)) * 0x94D049BB133111EBULL;
        return value ^ (value >> 31);
    }
    int below(int count) { return static_cast<int>(next_u64() % static_cast<std::uint64_t>(count)); }
private:
    std::uint64_t state_;
};

inline std::uint64_t p2_cave_seed(std::uint64_t base, int floor, int salt) {
    std::uint64_t mixed = base ^ (static_cast<std::uint64_t>(floor) << 32) ^ static_cast<std::uint64_t>(salt);
    return mixed * 0x100000001B3ULL;
}

inline bool p2_cave_grow(std::uint64_t ap_seed, int floor, int salt, const P2CavePool& pool,
                         const P2CaveHazard* chokes, int choke_count, P2CaveLayout& out) {
    P2CaveRng rng(p2_cave_seed(ap_seed, floor, salt));
    int segments[16] = {}; int segment_count = 0;
    int rooms[16] = {}; int room_count = 0;
    for (int i = 0; i < pool.count; i++) {
        if (p2_cave_slot(pool.units[i], pool.hazard[i]) != P2CaveSlot::Segment) continue;
        segments[segment_count++] = i;
        if (pool.units[i].kind == 1) rooms[room_count++] = i;
    }
    if (segment_count == 0 || room_count == 0) return false;
    out = P2CaveLayout{};
    int entry_unit = rooms[rng.below(room_count)];
    out.nodes[out.node_count++] = P2CaveNode{entry_unit, P2CaveSlot::Segment, 0};
    out.entry = 0;
    int frontier_node = 0;
    int frontier_door = rng.below(pool.units[entry_unit].door_count);
    int frontier_dir = (pool.units[entry_unit].door_direction[frontier_door]) % 4;
    auto attach = [&](int unit_index, P2CaveSlot slot) -> bool {
        const P2CaveUnit& unit = pool.units[unit_index];
        if (unit.door_count < 2) return false;
        int connect = rng.below(unit.door_count);
        int rotation = ((frontier_dir + 2) % 4 - unit.door_direction[connect]) % 4;
        if (rotation < 0) rotation += 4;
        int far = -1;
        for (int door = 0; door < unit.door_count; door++) if (door != connect) { far = door; break; }
        if (far < 0) return false;
        out.edges[out.edge_count++] = P2CaveEdge{frontier_node, frontier_door, out.node_count, far};
        out.nodes[out.node_count] = P2CaveNode{unit_index, slot, rotation};
        frontier_node = out.node_count++;
        frontier_door = far;
        frontier_dir = (unit.door_direction[far] + rotation) % 4;
        return true;
    };
    for (int i = 0, length = 1 + rng.below(3); i < length; i++)
        if (!attach(segments[rng.below(segment_count)], P2CaveSlot::Segment)) return false;
    for (int i = 0; i < choke_count; i++) {
        int candidates[16] = {}; int candidate_count = 0;
        for (int unit = 0; unit < pool.count; unit++)
            if (pool.hazard[unit] == chokes[i] &&
                p2_cave_slot(pool.units[unit], pool.hazard[unit]) == P2CaveSlot::Choke)
                candidates[candidate_count++] = unit;
        if (candidate_count == 0) return false;
        if (!attach(candidates[rng.below(candidate_count)], P2CaveSlot::Choke)) return false;
    }
    for (int i = 0, length = 1 + rng.below(3); i < length; i++) {
        int pick = (i == 0) ? rooms[rng.below(room_count)] : segments[rng.below(segment_count)];
        if (!attach(pick, P2CaveSlot::Segment)) return false;
    }
    int chosen = -1;
    for (int node = 1; node < out.node_count; node++)
        if (out.nodes[node].slot == P2CaveSlot::Segment && pool.units[out.nodes[node].unit].kind == 1) chosen = node;
    if (chosen < 0) return false;
    out.hole_host = chosen;
    return true;
}

inline bool p2_cave_choke_on_every_path(const P2CaveLayout& layout, const P2CavePool& pool,
                                        const P2CaveHazard* chokes, int choke_count) {
    bool adjacent[P2CaveLayout::MAX_NODES][P2CaveLayout::MAX_NODES] = {};
    for (int edge = 0; edge < layout.edge_count; edge++)
        adjacent[layout.edges[edge].a][layout.edges[edge].b] = adjacent[layout.edges[edge].b][layout.edges[edge].a] = true;
    auto hole_reachable = [&](int forbidden) {
        bool seen[P2CaveLayout::MAX_NODES] = {};
        int stack[P2CaveLayout::MAX_NODES] = {}; int top = 0;
        seen[layout.entry] = true; stack[top++] = layout.entry;
        while (top) {
            int current = stack[--top];
            for (int node = 0; node < layout.node_count; node++)
                if (node != forbidden && adjacent[current][node] && !seen[node]) { seen[node] = true; stack[top++] = node; }
        }
        return seen[layout.hole_host];
    };
    if (!hole_reachable(-1)) return false;
    int required = 0;
    for (int index = 0; index < choke_count; index++) {
        bool present = false;
        for (int node = 0; node < layout.node_count; node++)
            if (layout.nodes[node].slot == P2CaveSlot::Choke &&
                pool.hazard[layout.nodes[node].unit] == chokes[index]) present = true;
        if (!present) return false;
        required++;
    }
    for (int node = 0; node < layout.node_count; node++) {
        if (layout.nodes[node].slot != P2CaveSlot::Choke) continue;
        if (hole_reachable(node)) return false;
    }
    return choke_count > 0 && required == choke_count;
}

inline bool p2_cave_layout_same(const P2CaveLayout& a, const P2CaveLayout& b) {
    if (a.node_count != b.node_count || a.edge_count != b.edge_count) return false;
    for (int node = 0; node < a.node_count; node++)
        if (a.nodes[node].unit != b.nodes[node].unit || a.nodes[node].rotation != b.nodes[node].rotation) return false;
    return true;
}
