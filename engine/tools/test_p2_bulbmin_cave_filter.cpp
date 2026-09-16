#include "pc_p2_bulbmin_policy.h"
#include <cassert>
#include <cstdio>

// Lane 11 cave save-filter contract (#131): mirror of the source
// PikiMgr::caveSaveAllPikmins / saveAllPikmins predicate
// (src/plugProjectKandoU/pikiMgr.cpp:723,762)
//   (getKind() != Bulbmin || isPikmin()) && isAlive()
// A wild (unwhistled) Bulbmin dependent is never saved; a recruited body and
// every other species are carried. The exit-only drop is deferred (documented).
int main() {
    constexpr int kBulbmin = 5;

    // Non-Bulbmin species are always saved, regardless of phase.
    for (int species = 0; species < kBulbmin; ++species)
        assert(p2_bulbmin_should_save(species, -1)
               && p2_bulbmin_should_save(species, P2BulbminWild)
               && p2_bulbmin_should_save(species, P2BulbminRecruited));

    // Wild dependents are never saved (descent or exit).
    assert(!p2_bulbmin_should_save(kBulbmin, P2BulbminWild));

    // Recruited and untracked (restored/injected -> isPikmin()) Bulbmin save.
    assert(p2_bulbmin_should_save(kBulbmin, P2BulbminRecruited));
    assert(p2_bulbmin_should_save(kBulbmin, -1));

    std::puts("PASS P2_BULBMIN_CAVE_FILTER");
    return 0;
}
