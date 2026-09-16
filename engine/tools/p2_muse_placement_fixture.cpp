// Muse placement slice (#492) engine-free contract fixture.
//
// Verifies the header-inline candidate/slot table without linking the engine:
// every muse candidate resolves to its catalog-accepted generated slot, and
// every other id (including the already-bound 23/59-62 cohort and unknown ids)
// resolves to 0 / non-candidate. The slot literals mirror
// `randomizer/p2_placement_catalog.py` MUSE_GENERATED_SLOTS; the Python sync
// test guards the same table from the catalog side.
//
// Requested shared hook for #491 (NOT applied by this slice): register this
// translation unit in the native CMake/CTest gate, e.g.
//   add_executable(p2_muse_placement_fixture tools/p2_muse_placement_fixture.cpp)
//   add_test(NAME p2_muse_placement_fixture COMMAND p2_muse_placement_fixture)
// Until then it is verified with a direct syntax/single-file compile only.
#include "pc_p2_generated_placement.h"

#include <cstdio>

// Catalog mirror (MUSE_GENERATED_SLOTS): drift fails the build here first.
static_assert(MUSE_GENERATED_SLOT_FUEFUKI41 == 1254096625u, "Fuefuki41 slot drift");
static_assert(MUSE_GENERATED_SLOT_KURAGE57 == 689702860u, "Kurage57 slot drift");
static_assert(MUSE_GENERATED_SLOT_BOMBSARAI58 == 1787125272u, "BombSarai58 slot drift");
static_assert(MUSE_GENERATED_SLOT_MINIHOUDAI78 == 328297937u, "MiniHoudai78 slot drift");

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
    check(pc_p2_generated_placement_is_muse_candidate(41), "candidate-41");
    check(pc_p2_generated_placement_is_muse_candidate(57), "candidate-57");
    check(pc_p2_generated_placement_is_muse_candidate(58), "candidate-58");
    check(pc_p2_generated_placement_is_muse_candidate(78), "candidate-78");
    check(pc_p2_generated_placement_muse_slot(41) == 1254096625u, "slot-41");
    check(pc_p2_generated_placement_muse_slot(57) == 689702860u, "slot-57");
    check(pc_p2_generated_placement_muse_slot(58) == 1787125272u, "slot-58");
    check(pc_p2_generated_placement_muse_slot(78) == 328297937u, "slot-78");
    // Fail closed: ordinary, already-bound and unknown ids are not candidates.
    check(!pc_p2_generated_placement_is_muse_candidate(0), "reject-0");
    check(!pc_p2_generated_placement_is_muse_candidate(23), "reject-23-sarai");
    check(!pc_p2_generated_placement_is_muse_candidate(44), "reject-44-bluekochappy");
    check(!pc_p2_generated_placement_is_muse_candidate(59), "reject-59-otakara");
    check(!pc_p2_generated_placement_is_muse_candidate(99), "reject-99-unknown");
    check(pc_p2_generated_placement_muse_slot(0) == 0, "slot-0-zero");
    check(pc_p2_generated_placement_muse_slot(23) == 0, "slot-23-zero");
    check(pc_p2_generated_placement_muse_slot(99) == 0, "slot-99-zero");
    std::printf(g_failures ? "MUSE_PLACEMENT_FIXTURE FAIL\n" : "MUSE_PLACEMENT_FIXTURE PASS\n");
    std::fflush(stdout);
    return g_failures ? 1 : 0;
}
