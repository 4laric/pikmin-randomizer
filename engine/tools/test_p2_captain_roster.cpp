#include "pc_p2_captain_roster.h"
#include <cassert>
#include <cstdio>

// Lane 12 second-captain roster test (#130). This is the engine-free selection
// logic NaviMgr::getActiveNavi/getAliveOrima/getDeadOrima/informOrimaDead
// delegate to. It is not a live Navi runtime: no engine object is constructed.
int main()
{
    // Single captain is the default: active is slot 0, nothing is down, and
    // every query resolves to slot 0 exactly as the old getNavi() did.
    P2CaptainRoster single;
    single.reset();
    assert(single.activeIndex() == 0);
    assert(single.active(1) == 0);
    assert(single.firstAlive(1) == 0);
    assert(single.firstDead(1) == -1);
    assert(!single.isDead(0));

    // Two live captains: slot 0 is active until reselected.
    P2CaptainRoster two;
    two.reset();
    assert(two.active(2) == 0);
    two.setActiveIndex(1);
    assert(two.active(2) == 1);

    // GET_OTHER_NAVI mapping.
    assert(P2CaptainRoster::otherIndex(0) == 1);
    assert(P2CaptainRoster::otherIndex(1) == 0);
    assert(P2CaptainRoster::otherIndex(2) == -1);
    assert(P2CaptainRoster::otherIndex(-1) == -1);

    // A dead slot is not selectable and control falls to the survivor.
    two.markDead(1);
    assert(two.isDead(1));
    assert(two.active(2) == 0);
    assert(two.firstAlive(2) == 0);
    assert(two.firstDead(2) == 1);

    // Marking the active captain dead hands control to the first alive slot.
    two.markAlive(1);
    two.setActiveIndex(0);
    two.markDead(0);
    assert(two.firstAlive(2) == 1);
    assert(two.active(2) == 1);

    // Both down: no controllable captain (survivor-gated game over).
    two.markDead(1);
    assert(two.firstAlive(2) == -1);
    assert(two.active(2) == -1);

    // Reviving clears the dead flag without forcing an active switch.
    two.markAlive(0);
    assert(!two.isDead(0));
    assert(two.firstDead(2) == 1);
    assert(two.active(2) == 0);

    // Out-of-range indices are inert rather than crashing.
    P2CaptainRoster bounds;
    bounds.reset();
    bounds.markDead(5);
    bounds.markDead(-1);
    assert(!bounds.isDead(5));
    assert(bounds.firstAlive(2) == 0);

    // reset() returns to the single-captain default.
    two.reset();
    assert(!two.isDead(0) && !two.isDead(1));
    assert(two.activeIndex() == 0 && two.active(2) == 0);

    std::puts("PASS P2_CAPTAIN_ROSTER");
    return 0;
}
