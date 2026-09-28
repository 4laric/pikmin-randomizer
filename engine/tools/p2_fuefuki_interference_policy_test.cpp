#include "pc_p2_fuefuki_interference_policy.h"
// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <limits>

int main()
{
    P2FuefukiOwnershipTable table;

    // --- attract -> control -> cast growth -> timer cadence ---
    {
        P2FuefukiInterferencePolicy beetle;
        assert(beetle.bind(&table, 1));
        assert(!beetle.bind(&table, 2)); // no rebinding a live instance
        assert(!beetle.admit(1, 10, true, true, false, false).accepted); // not casting
        assert(beetle.beginCast(1).accepted);
        assert(!beetle.beginCast(1).accepted); // already casting
        // ring growth: 0 -> clamped 1.0 after one second of cast ticks
        auto c = beetle.tickCast(1, 0.4f);
        assert(c.accepted && c.radiusModifier == 0.4f);
        c = beetle.tickCast(1, 0.4f);
        assert(c.radiusModifier == 0.8f);
        c = beetle.tickCast(1, 0.4f);
        assert(c.radiusModifier == 1.0f);
        assert(!beetle.tickCast(1, -1.0f).accepted);
        assert(!beetle.tickCast(1, std::numeric_limits<float>::infinity()).accepted);
        assert(!beetle.tickCast(2, 0.1f).accepted); // stale epoch
        // admission gates: living, callable, not mouth-stuck, not ACT_Teki
        assert(!beetle.admit(1, 10, false, true, false, false).accepted);
        assert(!beetle.admit(1, 10, true, false, false, false).accepted);
        assert(!beetle.admit(1, 10, true, true, true, false).accepted);
        assert(!beetle.admit(1, 10, true, true, false, true).accepted);
        assert(!beetle.admit(2, 10, true, true, false, false).accepted); // stale epoch
        c = beetle.admit(1, 10, true, true, false, false);
        assert(c.accepted && c.claim && c.pikmin == 10);
        assert(beetle.holds(10));
        assert(!beetle.admit(1, 10, true, true, false, false).accepted); // duplicate
        // squad timer: ping refreshes to 5 ticks, tickSquad decrements per tick
        assert(!beetle.squadActive());
        assert(!beetle.ping(1, 99).accepted); // non-follower cannot ping
        c = beetle.ping(1, 10);
        assert(c.accepted && c.squadActive);
        for (int i = 0; i < 4; i++) {
            c = beetle.tickSquad(1);
            assert(c.accepted && c.squadActive);
        }
        c = beetle.tickSquad(1);
        assert(c.accepted && !c.squadActive); // expired after 5 ticks
        c = beetle.ping(1, 10);
        assert(c.squadActive);
        beetle.cancel(1);
        assert(!table.isHeld(10));
    }

    // --- beetle defeat mid-effect: Panic release + captain-whistle reclaim ---
    {
        P2FuefukiInterferencePolicy beetle;
        assert(beetle.bind(&table, 1));
        beetle.beginCast(1);
        beetle.admit(1, 20, true, true, false, false);
        beetle.admit(1, 21, true, true, false, false);
        auto released = beetle.ownerDied(1);
        assert(released.size() == 2);
        assert(!table.isHeld(20) && !table.isHeld(21));
        // captain switch / party combine are no-ops even after release
        assert(!beetle.captainSwitch(20).accepted);
        assert(!beetle.partyCombine(20).accepted);
        // whistle reclaim works only for Panic-released followers, once
        assert(!beetle.reclaimPanic(22).accepted);
        auto c = beetle.reclaimPanic(20);
        assert(c.accepted && c.reclaim && c.pikmin == 20);
        assert(!beetle.reclaimPanic(20).accepted);
        assert(beetle.reclaimPanic(21).accepted);
        // stale epoch commands after death are inert
        assert(!beetle.admit(1, 30, true, true, false, false).accepted);
        assert(!beetle.beginCast(1).accepted); // dead owner cannot cast again
        beetle.cancel(1);
    }

    // --- captain switch and party combine are no-ops while held ---
    {
        P2FuefukiInterferencePolicy beetle;
        assert(beetle.bind(&table, 1));
        beetle.beginCast(1);
        beetle.admit(1, 40, true, true, false, false);
        assert(!beetle.captainSwitch(40).accepted);
        assert(!beetle.partyCombine(40).accepted);
        assert(!beetle.reclaimPanic(40).accepted); // live beetle's follower ignores whistles
        assert(beetle.holds(40));
        beetle.cancel(1);
    }

    // --- owner suspension: flying/bittered exit, no Panic, no reclaim ---
    {
        P2FuefukiInterferencePolicy beetle;
        assert(beetle.bind(&table, 1));
        beetle.beginCast(1);
        beetle.admit(1, 50, true, true, false, false);
        beetle.ping(1, 50);
        auto susp = beetle.suspend(1);
        assert(susp.accepted);
        assert(susp.released.size() == 1 && susp.released[0] == 50);
        assert(susp.fallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        assert(!beetle.squadActive());
        assert(!beetle.reclaimPanic(50).accepted); // suspend is not a Panic release
        // owner returns: can cast and re-claim
        assert(beetle.beginCast(1).accepted);
        assert(beetle.admit(1, 50, true, true, false, false).accepted);
        beetle.cancel(1);
    }

    // --- two-beetle simultaneous claim: first in fixed owner ordering wins ---
    {
        table.invalidateDomain();
        P2FuefukiInterferencePolicy beetleA, beetleB;
        assert(beetleA.bind(&table, 1));
        assert(beetleB.bind(&table, 2));
        beetleA.beginCast(1);
        beetleB.beginCast(2);
        auto cA = beetleA.admit(1, 60, true, true, false, false);
        auto cB = beetleB.admit(2, 60, true, true, false, false);
        assert(cA.accepted && cA.claim);
        assert(!cB.accepted && !cB.claim); // exclusivity across instances
        assert(table.heldBy(60, 1));
        // beetle B keeps its own separate followers
        assert(beetleB.admit(2, 61, true, true, false, false).accepted);
        // B's defeat does not release A's follower
        auto releasedB = beetleB.ownerDied(2);
        assert(releasedB.size() == 1 && releasedB[0] == 61);
        assert(table.heldBy(60, 1));
        // B's death makes A's follower still non-reclaimable for A's policy
        assert(!beetleA.reclaimPanic(60).accepted);
        beetleA.cancel(1);
    }

    // --- stale owner / manager-slot reuse hazard ---
    {
        table.invalidateDomain();
        P2FuefukiInterferencePolicy slot1;
        assert(slot1.bind(&table, 7));
        slot1.beginCast(7);
        slot1.admit(7, 70, true, true, false, false);
        // teardown without death: cancel guarantees no phantom claims
        slot1.cancel(7);
        assert(!table.isHeld(70));
        assert(!slot1.reclaimPanic(70).accepted); // cancel clears Panic records too
        // domain invalidation before slot reuse, then a new owner epoch
        table.invalidateDomain();
        P2FuefukiInterferencePolicy slot2;
        assert(slot2.bind(&table, 8)); // strictly increasing epoch
        slot2.beginCast(8);
        assert(slot2.admit(8, 70, true, true, false, false).accepted);
        assert(!slot1.admit(7, 70, true, true, false, false).accepted); // stale owner rejected
        assert(!slot1.ping(7, 70).accepted);
        slot2.cancel(8);
    }

    // --- epoch zero / malformed input rejection ---
    {
        table.invalidateDomain();
        P2FuefukiInterferencePolicy beetle;
        assert(!beetle.bind(nullptr, 1));
        assert(!beetle.bind(&table, 0));
        assert(beetle.bind(&table, 1));
        assert(!beetle.tickCast(0, 0.5f).accepted);
        assert(!beetle.ping(0, 1).accepted);
        assert(beetle.beginCast(1).accepted);
        assert(!beetle.admit(1, 0, true, true, false, false).accepted); // pikmin id 0 invalid
        beetle.cancel(1);
    }

    puts("p2_fuefuki_interference_policy_test PASS");
}
