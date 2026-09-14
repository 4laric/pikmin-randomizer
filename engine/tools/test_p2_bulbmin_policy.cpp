#include "pc_p2_bulbmin_policy.h"
#include <cassert>
#include <cstdio>

// Lane 11 policy test: Bulbmin dependents are born only through a mother,
// recruitment converts a body in place without duplication, the mother's
// death releases only wild dependents, and cave transitions keep exactly the
// source-permitted survivors.
int main() {
    P2BulbminFlock flock;
    P2BulbminLeader mother;
    assert(mother.bind(&flock, 100));

    for (int i = 0; i < P2BULBMIN_MAX_DEPENDENTS; ++i) {
        P2BulbminCommand c = mother.birth(100, 1000 + i);
        assert(c.accepted);
        assert(c.phase == P2BulbminWild);
        assert(!c.countsAsPikmin);
    }
    assert(mother.dependentCount() == P2BULBMIN_MAX_DEPENDENTS);
    assert(flock.size() == 10 && flock.wildCount() == 10 && flock.recruitedCount() == 0);

    // The eleven dependents / duplicate id / stale mother epoch are refused.
    assert(!mother.birth(100, 2000).accepted);
    assert(!mother.birth(100, 1000).accepted);
    assert(!mother.birth(999, 3000).accepted);
    assert(flock.size() == 10);

    // Whistle converts in place, counts as a Pikmin and detaches from the
    // mother. A second whistle is a no-op and a stale epoch is refused.
    P2BulbminCommand w = mother.whistle(100, 1000);
    assert(w.accepted && w.phase == P2BulbminRecruited);
    assert(w.countsAsPikmin && w.detachFromLeader);
    assert(flock.phaseOf(1000) == P2BulbminRecruited);
    assert(flock.size() == 10 && flock.wildCount() == 9 && flock.recruitedCount() == 1);
    assert(!mother.whistle(100, 1000).accepted);
    assert(!mother.whistle(999, 1001).accepted);

    // Mother death releases only the nine wild dependents; the recruited
    // team member survives with its captain ownership intact.
    std::vector<std::uint32_t> released = mother.leaderDied(100);
    assert(released.size() == 9);
    assert(flock.size() == 1 && flock.recruitedCount() == 1);
    assert(flock.contains(1000));
    assert(!mother.birth(100, 4000).accepted);
    assert(!mother.whistle(100, 1001).accepted);

    // Floor descent keeps only whistled Bulbmin; cave exit removes them all.
    P2BulbminFlock flock2;
    P2BulbminLeader mother2;
    assert(mother2.bind(&flock2, 200));
    for (int i = 0; i < P2BULBMIN_MAX_DEPENDENTS; ++i) {
        assert(mother2.birth(200, 5000 + i).accepted);
    }
    assert(mother2.whistle(200, 5000).accepted);
    P2BulbminTransitionOut down = flock2.applyTransition(P2BulbminDescendFloor);
    assert(down.kept.size() == 1 && down.removed.size() == 9 && down.recruitedKept == 1);
    assert(flock2.size() == 1 && flock2.phaseOf(5000) == P2BulbminRecruited);
    P2BulbminTransitionOut exitOut = flock2.applyTransition(P2BulbminExitCave);
    assert(exitOut.removed.size() == 1 && exitOut.kept.empty());
    assert(flock2.size() == 0);

    // Bulbmin carry every elemental immunity in both phases.
    assert(p2_bulbmin_hazard_immune());

    // Teardown clears the shared ledger so a recycled id cannot inherit it.
    flock.invalidateDomain();
    assert(flock.size() == 0);

    std::puts("PASS P2_BULBMIN_POLICY");
    return 0;
}
