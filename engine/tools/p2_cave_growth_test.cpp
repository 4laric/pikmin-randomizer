#include "pc_p2_cave_growth.h"
#include <cstdio>
#include <initializer_list>

// The Release build defines NDEBUG, so assert() would compile the whole test
// away; CHECK is unconditional and makes this a real gate.
#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                     \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
            return 1;                                                           \
        }                                                                       \
    } while (0)

static P2CavePool make_pool() {
    P2CavePool pool;
    auto add = [&](const char* name, int kind, int doors, std::initializer_list<int> directions, P2CaveHazard hazard) {
        const int index = pool.count++;
        pool.units[index] = P2CaveUnit{name, kind, doors, {}};
        int door = 0;
        for (int direction : directions) pool.units[index].door_direction[door++] = direction;
        pool.hazard[index] = hazard;
    };
    add("way2_tsuchi", 2, 2, {0, 2}, P2CaveHazard::None);
    add("wayl_tsuchi", 2, 2, {2, 3}, P2CaveHazard::Water);
    add("wayx_tsuchi", 2, 2, {0, 2}, P2CaveHazard::Elec);
    add("room_a", 1, 4, {0, 1, 2, 3}, P2CaveHazard::None);
    add("room_b", 1, 2, {0, 2}, P2CaveHazard::None);
    add("cap", 0, 1, {2}, P2CaveHazard::None);
    add("boss", 1, 0, {}, P2CaveHazard::None);
    return pool;
}

static int choke_nodes(const P2CaveLayout& layout) {
    int total = 0;
    for (int node = 0; node < layout.node_count; node++) if (layout.nodes[node].slot == P2CaveSlot::Choke) total++;
    return total;
}

int main() {
    P2CavePool pool = make_pool();
    CHECK(p2_cave_partition_count(pool, P2CaveSlot::Segment) == 3);
    CHECK(p2_cave_partition_count(pool, P2CaveSlot::Choke) == 2);
    CHECK(p2_cave_partition_count(pool, P2CaveSlot::Leaf) == 1);
    CHECK(p2_cave_partition_count(pool, P2CaveSlot::Excluded) == 1);

    const P2CaveHazard water[] = {P2CaveHazard::Water};
    P2CaveLayout first = {};
    CHECK(p2_cave_grow(20260915ULL, 1, 0, pool, water, 1, first));
    CHECK(p2_cave_choke_on_every_path(first, pool, water, 1));
    CHECK(choke_nodes(first) == 1);

    P2CaveLayout repeat = {};
    CHECK(p2_cave_grow(20260915ULL, 1, 0, pool, water, 1, repeat));
    CHECK(p2_cave_layout_same(first, repeat));

    bool rerolled = false;
    for (int salt = 1; salt < 6; salt++) {
        P2CaveLayout other = {};
        CHECK(p2_cave_grow(20260915ULL, 1, salt, pool, water, 1, other));
        if (!p2_cave_layout_same(first, other)) rerolled = true;
    }
    CHECK(rerolled);

    const P2CaveHazard both[] = {P2CaveHazard::Water, P2CaveHazard::Elec};
    P2CaveLayout chained = {};
    CHECK(p2_cave_grow(7ULL, 2, 0, pool, both, 2, chained));
    CHECK(choke_nodes(chained) == 2);
    CHECK(p2_cave_choke_on_every_path(chained, pool, both, 2));

    P2CaveLayout bypass = {};
    bypass.nodes[bypass.node_count++] = P2CaveNode{0, P2CaveSlot::Segment, 0};
    bypass.nodes[bypass.node_count++] = P2CaveNode{1, P2CaveSlot::Choke, 0};
    bypass.nodes[bypass.node_count++] = P2CaveNode{3, P2CaveSlot::Segment, 0};
    bypass.edges[bypass.edge_count++] = P2CaveEdge{0, 0, 1, 0};
    bypass.edges[bypass.edge_count++] = P2CaveEdge{1, 0, 2, 0};
    bypass.edges[bypass.edge_count++] = P2CaveEdge{0, 0, 2, 0};
    bypass.entry = 0;
    bypass.hole_host = 2;
    CHECK(!p2_cave_choke_on_every_path(bypass, pool, water, 1));

    P2CavePool no_rooms;
    no_rooms.count = 2;
    no_rooms.units[0] = P2CaveUnit{"way2_tsuchi", 2, 2, {0, 2}};
    no_rooms.units[1] = P2CaveUnit{"wayl_tsuchi", 2, 2, {2, 3}};
    no_rooms.hazard[1] = P2CaveHazard::Water;
    P2CaveLayout missing = {};
    CHECK(!p2_cave_grow(20260915ULL, 1, 0, no_rooms, water, 1, missing));

    std::puts("PASS p2 cave growth: partition, forced choke on every path, "
              "multi-choke chain, reroll, bypass and no-room failure rejection");
    return 0;
}
