#include "pc_p2_captain_policy.h"
#include <cassert>
#include <cstdio>

// Lane 12 policy test: the two-captain / captive / squad ownership contract
// must conserve owned actors across switch, capture, knockout, release and
// reload, and must reject a capture that would leave zero control.
int main() {
    P2CaptainOwnershipTable table;
    P2CaptainPolicy cap;
    assert(cap.bind(&table));
    assert(cap.configure(P2CaptainA, 100.0f, true));
    assert(cap.configure(P2CaptainB, 100.0f, true));
    assert(cap.activeCaptain() == P2CaptainA);

    // Exclusive ownership: an actor has at most one captain.
    assert(cap.claim(P2CaptainA, 11));
    assert(cap.claim(P2CaptainB, 12));
    assert(!cap.claim(P2CaptainB, 11));
    assert(table.ownedBy(P2CaptainA) == 1);
    assert(table.ownedBy(P2CaptainB) == 1);

    // Switch preserves ownership and changes exactly one Active slot.
    assert(cap.switchActive(P2CaptainB));
    assert(cap.activeCaptain() == P2CaptainB);
    assert(cap.phase(P2CaptainA) == P2CaptainPhase::Idle);
    assert(table.ownedBy(P2CaptainA) == 1 && table.ownedBy(P2CaptainB) == 1);
    assert(!cap.switchActive(P2CaptainB)); // already active
    assert(p2_other_captain(P2CaptainA) == P2CaptainB);
    assert(p2_other_captain(P2CaptainB) == P2CaptainA);

    // Capture of the active captain: control falls to the other, and the
    // captive's squad is transferred without loss or duplication.
    assert(cap.capture(P2CaptainB, 7));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Captured);
    assert(cap.activeCaptain() == P2CaptainA);
    assert(table.ownedBy(P2CaptainA) == 2);
    assert(table.ownedBy(P2CaptainB) == 0);
    assert(table.ownedCount() == 2);

    // A stale captor epoch cannot release another captor's capture.
    assert(!cap.releaseCaptured(P2CaptainB, 8));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Captured);
    assert(cap.releaseCaptured(P2CaptainB, 7));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Idle);
    assert(cap.activeCaptain() == P2CaptainA);

    // Knockout frees only the downed captain's actors; the rest stay owned.
    assert(cap.claim(P2CaptainB, 13));
    assert(table.ownedBy(P2CaptainB) == 1);
    assert(cap.damage(P2CaptainB, 100.0f));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Down);
    assert(table.ownedBy(P2CaptainB) == 0);
    assert(table.ownedCount() == 2); // 11 and 12 remain owned by A

    // Scene reload cannot duplicate or lose owned actors.
    cap.reload();
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Down);
    assert(table.ownedBy(P2CaptainA) == 2);
    assert(table.ownedCount() == 2);

    // Revive returns the captain to Idle without stealing control.
    assert(cap.revive(P2CaptainB, 100.0f));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Idle);
    assert(cap.activeCaptain() == P2CaptainA);

    // Transient capture is cleared by reload; ownership stays conserved.
    assert(cap.capture(P2CaptainB, 11));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Captured);
    cap.reload();
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Idle);
    assert(table.ownedCount() == 2);

    // A capture that would leave zero control is refused: with B down, the
    // last controllable captain (A) cannot be ingested.
    assert(cap.damage(P2CaptainB, 100.0f));
    assert(cap.phase(P2CaptainB) == P2CaptainPhase::Down);
    assert(!cap.capture(P2CaptainA, 20));
    assert(cap.phase(P2CaptainA) == P2CaptainPhase::Active);

    // President substitution: a reserved but absent slot is not controllable.
    P2CaptainOwnershipTable table2;
    P2CaptainPolicy cap2;
    assert(cap2.bind(&table2));
    assert(cap2.configure(P2CaptainA, 80.0f, true));
    assert(cap2.configure(P2CaptainB, 80.0f, false));
    assert(cap2.activeCaptain() == P2CaptainA);
    assert(!cap2.present(P2CaptainB));
    assert(!cap2.controllable(P2CaptainB));
    assert(!cap2.switchActive(P2CaptainB));

    // Captor-held actors (families 29/30): an actor is either captain-owned or
    // captor-held, never both; drop frees it, reload restores it, stale
    // captors cannot release it.
    P2CaptainOwnershipTable table3;
    P2CaptainPolicy cap3;
    assert(cap3.bind(&table3));
    assert(cap3.configure(P2CaptainA, 100.0f, true));
    assert(cap3.configure(P2CaptainB, 100.0f, true));
    assert(cap3.claim(P2CaptainA, 21));
    assert(cap3.claim(P2CaptainA, 22));
    assert(cap3.claim(P2CaptainB, 23));

    assert(cap3.captureActor(900, 21));
    assert(cap3.isCaptive(21));
    assert(table3.ownerOf(21) == P2CaptainInvalid);
    assert(table3.ownedBy(P2CaptainA) == 1); // 22 remains with A
    assert(!cap3.captureActor(901, 21));      // never double-claimed
    assert(cap3.releaseActor(900, 21, P2CaptainB));
    assert(!cap3.isCaptive(21));
    assert(table3.ownerOf(21) == P2CaptainB);
    assert(table3.ownedCount() == 3); // 21, 22 and 23 all owned again

    assert(cap3.captureActor(902, 22));
    assert(!cap3.releaseActor(903, 22, P2CaptainA)); // stale captor epoch
    assert(cap3.isCaptive(22));
    std::vector<std::uint32_t> dropped = cap3.dropAllCaptured(902);
    assert(dropped.size() == 1 && dropped[0] == 22);
    assert(table3.ownerOf(22) == P2CaptainInvalid); // freed, not deleted

    // A free actor can be grabbed, and releasing to an invalid target restores
    // the (invalid) previous owner, i.e. leaves it free.
    assert(cap3.captureActor(905, 22));
    assert(cap3.releaseActor(905, 22, P2CaptainInvalid));
    assert(table3.ownerOf(22) == P2CaptainInvalid);

    // Reload restores a captive to its previous captain without duplication.
    assert(cap3.captureActor(904, 23));
    assert(table3.ownerOf(23) == P2CaptainInvalid);
    cap3.reload();
    assert(table3.ownerOf(23) == P2CaptainB);
    assert(cap3.captiveCount() == 0);
    assert(table3.ownedCount() == 2);

    // Cancellation before teardown frees every owned actor.
    cap.cancel();
    assert(table.ownedCount() == 0);

    std::puts("PASS P2_CAPTAIN_POLICY");
    return 0;
}
