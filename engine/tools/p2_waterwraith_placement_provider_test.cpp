// Provider slice (#575) engine-free contract test for Waterwraith BlackMan99
// generated-placement support (consumer #572).
//
// Compiles with -Ipc_port ONLY (no engine headers), proving the header-inline
// contract without linking the engine:
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port
//       tools/p2_waterwraith_placement_provider_test.cpp
//       -o p2_waterwraith_placement_provider_test
//
// The #492 muse table is asserted UNCHANGED here (99 stays non-muse), so the
// existing p2_muse_placement_fixture reject-99 expectation is preserved. Slot
// literals mirror `randomizer/p2_placement_catalog.py` WATERWRAITH_GENERATED_SLOTS
// and are asserted by the Python root/native sync test.
#include "pc_p2_generated_placement.h"

#include <cstdio>

static_assert(WATERWRAITH_GENERATED_SLOT_BLACKMAN99 == 568677317u,
              "Waterwraith99 slot drift");

// The muse #492 table must not move.
static_assert(MUSE_GENERATED_SLOT_FUEFUKI41 == 1254096625u, "muse 41 drift");
static_assert(MUSE_GENERATED_SLOT_KURAGE57 == 689702860u, "muse 57 drift");
static_assert(MUSE_GENERATED_SLOT_BOMBSARAI58 == 1787125272u, "muse 58 drift");
static_assert(MUSE_GENERATED_SLOT_MINIHOUDAI78 == 328297937u, "muse 78 drift");

namespace {
int g_failures = 0;

void check(bool condition, const char* name)
{
    std::printf("%s %s\n", condition ? "PASS" : "FAIL", name);
    std::fflush(stdout);
    if (!condition) ++g_failures;
}
} // namespace

int main()
{
    // 1. Muse #492 contract preserved exactly.
    check(pc_p2_generated_placement_is_muse_candidate(41), "muse-41");
    check(pc_p2_generated_placement_is_muse_candidate(57), "muse-57");
    check(pc_p2_generated_placement_is_muse_candidate(58), "muse-58");
    check(pc_p2_generated_placement_is_muse_candidate(78), "muse-78");
    check(!pc_p2_generated_placement_is_muse_candidate(99), "muse-reject-99-unchanged");
    check(!pc_p2_generated_placement_is_muse_candidate(0), "muse-reject-0");
    check(!pc_p2_generated_placement_is_muse_candidate(98), "muse-reject-98-tyre");
    check(pc_p2_generated_placement_muse_slot(41) == 1254096625u, "muse-slot-41");
    check(pc_p2_generated_placement_muse_slot(57) == 689702860u, "muse-slot-57");
    check(pc_p2_generated_placement_muse_slot(58) == 1787125272u, "muse-slot-58");
    check(pc_p2_generated_placement_muse_slot(78) == 328297937u, "muse-slot-78");
    check(pc_p2_generated_placement_muse_slot(99) == 0u, "muse-slot-99-zero");

    // 2. Waterwraith candidate predicate and slot: 99 only.
    check(pc_p2_generated_placement_is_waterwraith_candidate(99), "ww-99");
    check(!pc_p2_generated_placement_is_waterwraith_candidate(0), "ww-reject-0");
    check(!pc_p2_generated_placement_is_waterwraith_candidate(41), "ww-reject-41");
    check(!pc_p2_generated_placement_is_waterwraith_candidate(57), "ww-reject-57");
    check(!pc_p2_generated_placement_is_waterwraith_candidate(58), "ww-reject-58");
    check(!pc_p2_generated_placement_is_waterwraith_candidate(78), "ww-reject-78");
    check(!pc_p2_generated_placement_is_waterwraith_candidate(98), "ww-reject-98-tyre");
    check(pc_p2_generated_placement_waterwraith_slot(99) == 568677317u, "ww-slot-99");
    check(pc_p2_generated_placement_waterwraith_slot(98) == 0u, "ww-slot-98-zero");
    check(pc_p2_generated_placement_waterwraith_slot(41) == 0u, "ww-slot-41-zero");

    // 3. The two tables are disjoint: no id is both muse and waterwraith.
    const unsigned ids[] = {0u, 23u, 41u, 44u, 57u, 58u, 59u, 78u, 98u, 99u};
    for (unsigned id : ids) {
        check(!(pc_p2_generated_placement_is_muse_candidate(id)
                && pc_p2_generated_placement_is_waterwraith_candidate(id)),
              "tables-disjoint");
    }

    std::printf(g_failures ? "WATERWRAITH_PLACEMENT_PROVIDER FAIL\n"
                           : "WATERWRAITH_PLACEMENT_PROVIDER PASS\n");
    std::fflush(stdout);
    return g_failures ? 1 : 0;
}
