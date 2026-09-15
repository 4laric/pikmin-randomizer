// Standalone engine-free fixture for the Groink shell-strike -> proxy receiver
// bridge (pc_port/pc_p2_groink_strike.h/.cpp). It links only the pure Groink
// classifier and the vendored lane-20 receiver; no engine headers are used.
// Build (MinGW):
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_strike_test.cpp pc_port/pc_p2_groink_strike.cpp pc_port/pc_p2_groink_hit.cpp pc_port/pc_p2_projectile_receiver.cpp -o <private-output>/p2_groink_strike_test.exe

#include "pc_p2_groink_strike.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <limits>

namespace {
constexpr std::uint64_t kNaviToken = 0x1001ULL;
constexpr std::uint64_t kOwnerToken = 0x3003ULL;
constexpr std::uint64_t kRuntimeToken = 0xDEADBEEFCAFEULL;

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

// Source-compatible sweep with the shell damage and no terminal explosion; a
// Captain at the prism center receives a Bomb with the classifier's damage.
P2GroinkHitInput bombSweep(float damage)
{
    P2GroinkHitInput hit;
    hit.start = { 0.0f, 0.0f, 0.0f };
    hit.end = { 0.0f, 0.0f, 10.0f };
    hit.radius = 2.0f;
    hit.terminalRadius = 10.0f;
    hit.damage = damage;
    hit.terminal = false;
    return hit;
}

P2GroinkHitCandidate captain(float x, float z)
{
    return P2GroinkHitCandidate{ { x, 0.0f, z }, P2GroinkCandidateKind::Captain, true, false, 4.0f };
}

// Terminal sweep whose end falloff lies outside the strict prism: the same
// candidate is a Wind at the terminal end instead of a Bomb.
P2GroinkHitInput windSweep(float damage)
{
    P2GroinkHitInput hit = bombSweep(damage);
    hit.terminal = true;
    return hit;
}

void testBombAppliesDamageThenDiesOnce()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 20.0f));

    P2GroinkStrikeInput input;
    input.hit = bombSweep(10.0f);
    input.targetToken = kNaviToken;
    input.attributedToken = kOwnerToken;

    const P2GroinkStrikeResult first =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(first.valid && first.insideSweep && first.kind == P2GroinkHitKind::Bomb);
    assert(near(first.damage, 10.0f)); // exactly the classifier damage
    assert(first.applied && !first.died);
    assert(near(first.health, 10.0f));
    assert(near(registry.find(kNaviToken)->health(), 10.0f));

    const P2GroinkStrikeResult killing =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(killing.applied && killing.died);
    assert(near(killing.health, 0.0f));
    assert(!registry.find(kNaviToken)->alive());

    // The dead receiver applies nothing and never reports a second death.
    const P2GroinkStrikeResult after =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(!after.applied && !after.died);
    assert(near(after.health, 0.0f));
}

void testWindPreservesImpulseWithoutHealthChange()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 20.0f));

    P2GroinkStrikeInput input;
    input.hit = windSweep(10.0f);
    input.targetToken = kNaviToken;
    input.attributedToken = kOwnerToken;

    const P2GroinkStrikeResult result =
        p2_groink_apply_strike(registry, input, captain(2.0f, 10.0f));
    assert(result.valid && !result.insideSweep && result.kind == P2GroinkHitKind::Wind);
    assert(!result.applied && !result.died);
    assert(near(result.impulse.x, 135.0f) && near(result.impulse.y, 0.0f)
           && near(result.impulse.z, 0.0f));
    // Wind must not touch receiver health.
    assert(near(registry.find(kNaviToken)->health(), 20.0f));
    assert(near(result.health, 20.0f));
}

void testNonStrikeCasesAreNoOps()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 20.0f));

    P2GroinkStrikeInput input;
    input.hit = bombSweep(10.0f);
    input.targetToken = kNaviToken;

    // Dead candidate: classifier suppresses before any strike.
    P2GroinkHitCandidate dead = captain(1.0f, 5.0f);
    dead.alive = false;
    const P2GroinkStrikeResult deceased = p2_groink_apply_strike(registry, input, dead);
    assert(deceased.valid && deceased.kind == P2GroinkHitKind::None && !deceased.applied);

    // Degenerate sweep (zero length) is never a strike.
    input.hit.end = input.hit.start;
    input.hit.terminal = true;
    const P2GroinkStrikeResult degenerate =
        p2_groink_apply_strike(registry, input, captain(0.0f, 0.0f));
    assert(degenerate.valid && !degenerate.insideSweep
           && degenerate.kind == P2GroinkHitKind::None && !degenerate.applied);

    // Nonfinite input is invalid with no command.
    input.hit.start.x = std::numeric_limits<float>::quiet_NaN();
    const P2GroinkStrikeResult invalid =
        p2_groink_apply_strike(registry, input, captain(0.0f, 0.0f));
    assert(!invalid.valid && invalid.kind == P2GroinkHitKind::None && !invalid.applied);

    assert(near(registry.find(kNaviToken)->health(), 20.0f));
}

void testRepeatedStrikesClampAtZero()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 20.0f));

    P2GroinkStrikeInput input;
    input.hit = bombSweep(15.0f);
    input.targetToken = kNaviToken;

    const P2GroinkStrikeResult first =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(first.applied && !first.died && near(first.health, 5.0f));

    // The overkill strike clamps the removal to the remaining health and is the
    // only one that reports died.
    const P2GroinkStrikeResult killing =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(killing.applied && killing.died && near(killing.health, 0.0f));
    assert(near(registry.find(kNaviToken)->health(), 0.0f));

    const P2GroinkStrikeResult after =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(!after.applied && !after.died && near(after.health, 0.0f));
}

void testWildcardSinkUnknownRuntimeToken()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.addAny(25.0f));

    P2GroinkStrikeInput input;
    input.hit = bombSweep(10.0f);
    input.targetToken = kRuntimeToken; // not registered exactly
    input.attributedToken = kOwnerToken;

    const P2GroinkStrikeResult result =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(result.valid && result.kind == P2GroinkHitKind::Bomb);
    assert(result.applied && !result.died);
    assert(near(result.health, 15.0f));
}

// Tracker dedups (slot, token): one shell applies once across its flight, a
// second slot can still hit the same token, and reset/clearSlot forget history.
void testTrackerDedupsPerShellSlotButAllowsAnotherSlot()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 30.0f));

    P2GroinkStrikeTracker tracker;
    P2GroinkStrikeInput input;
    input.hit = bombSweep(10.0f);
    input.targetToken = kNaviToken;

    // Slot 0 records the pair on its first contact and the strike applies.
    assert(tracker.firstHit(0, kNaviToken));
    const P2GroinkStrikeResult first =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(first.applied && near(first.health, 20.0f));

    // A later moving step of the same shell must not apply a second hit.
    assert(!tracker.firstHit(0, kNaviToken));
    assert(!p2_groink_strike_first_hit(tracker, 0, kNaviToken));
    assert(near(registry.find(kNaviToken)->health(), 20.0f));

    // A different shell may hit the same token exactly once of its own.
    assert(tracker.firstHit(1, kNaviToken));
    const P2GroinkStrikeResult second =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(second.applied && near(second.health, 10.0f));

    // Reset forgets everything; clearSlot forgets only one shell.
    tracker.clearSlot(0);
    assert(tracker.firstHit(0, kNaviToken));
    assert(!tracker.firstHit(1, kNaviToken));
    tracker.reset();
    assert(tracker.firstHit(0, kNaviToken));
    assert(tracker.firstHit(1, kNaviToken));
}

// A non-terminal moving segment (previous -> current position) still applies.
void testMovingNonTerminalSegmentApplies()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 20.0f));

    P2GroinkStrikeInput input;
    input.hit.start = { 0.0f, 0.0f, 0.0f };
    input.hit.end = { 0.0f, 0.0f, 6.0f }; // mid-flight step, not the terminal end
    input.hit.radius = 2.0f;
    input.hit.terminalRadius = 2.0f;
    input.hit.damage = 10.0f;
    input.hit.terminal = false;
    input.targetToken = kNaviToken;

    const P2GroinkStrikeResult result =
        p2_groink_apply_strike(registry, input, captain(1.0f, 3.0f));
    assert(result.valid && result.insideSweep && result.kind == P2GroinkHitKind::Bomb);
    assert(result.applied && !result.died && near(result.health, 10.0f));
}

// Wind carries impulse with no health change and is deduped like a Bomb. Wind is
// only ever classified at a terminal falloff, so this uses the terminal flag even
// though the host invokes it from a moving-step scan.
void testWindStepCarriesImpulseWithoutHealthAndDedups()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 20.0f));

    P2GroinkStrikeTracker tracker;
    P2GroinkStrikeInput input;
    input.hit = windSweep(10.0f);
    input.targetToken = kNaviToken;

    assert(tracker.firstHit(0, kNaviToken));
    const P2GroinkStrikeResult wind =
        p2_groink_apply_strike(registry, input, captain(2.0f, 10.0f));
    assert(wind.valid && !wind.insideSweep && wind.kind == P2GroinkHitKind::Wind);
    assert(!wind.applied && !wind.died);
    assert(near(wind.impulse.x, 135.0f) && near(wind.impulse.y, 0.0f)
           && near(wind.impulse.z, 0.0f));
    // Wind never touches receiver health.
    assert(near(registry.find(kNaviToken)->health(), 20.0f));
    assert(near(wind.health, 20.0f));

    // The same shell does not re-report the candidate; another shell does.
    assert(!tracker.firstHit(0, kNaviToken));
    assert(tracker.firstHit(1, kNaviToken));
}

void testExactTokenTakesPrecedenceOverWildcard()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.addAny(100.0f));
    assert(registry.add(kNaviToken, 5.0f));

    P2GroinkStrikeInput input;
    input.hit = bombSweep(10.0f);
    input.targetToken = kNaviToken;

    const P2GroinkStrikeResult exact =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(exact.applied && exact.died && near(exact.health, 0.0f));
    assert(near(registry.find(kNaviToken)->health(), 0.0f));

    // The wildcard sink keeps its own untouched health for unknown tokens.
    input.targetToken = kRuntimeToken;
    const P2GroinkStrikeResult wildcard =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(wildcard.applied && !wildcard.died && near(wildcard.health, 90.0f));
}
// Capacity regression (wave-three #437). Filling the tracker must not let an
// untrackable extra pair be reported as a hit on every moving step, which would
// re-apply damage. Overflow is an explicit rejection, and recycling a shell slot
// still admits a genuinely new flight.
void testTrackerRejectsOverflowAndRecycleAdmitsNewFlight()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 30.0f));
    assert(registry.add(kRuntimeToken, 30.0f));

    P2GroinkStrikeTracker tracker;
    P2GroinkStrikeInput input;
    input.hit = bombSweep(10.0f);
    input.targetToken = kNaviToken;

    // Fill the supported bound with kMaxTracked distinct (slot, token) pairs.
    for (std::size_t slot = 0; slot < P2GroinkStrikeTracker::kMaxTracked; ++slot) {
        assert(tracker.firstHit(slot, kNaviToken));
    }
    assert(tracker.tracked() == P2GroinkStrikeTracker::kMaxTracked);
    assert(tracker.full());

    // Already-tracked pairs stay deduped, not misreported as new.
    assert(tracker.decide(0, kNaviToken) == P2GroinkStrikeDecision::AlreadyHit);
    assert(!tracker.firstHit(0, kNaviToken));

    // The 65th unique candidate cannot be recorded. It must be rejected on every
    // call rather than reported as a hit (the pre-fix overflow behavior).
    assert(tracker.decide(0, kRuntimeToken)
           == P2GroinkStrikeDecision::RejectedAtCapacity);
    assert(!tracker.firstHit(0, kRuntimeToken));
    assert(!tracker.firstHit(0, kRuntimeToken));
    assert(!p2_groink_strike_first_hit(tracker, 0, kRuntimeToken));
    assert(near(registry.find(kNaviToken)->health(), 30.0f));

    // Host pattern: apply only when the tracker returns true. The rejected pair
    // never mutates the receiver, so its health is unchanged.
    input.targetToken = kRuntimeToken;
    if (tracker.firstHit(0, kRuntimeToken)) {
        (void)p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    }
    assert(near(registry.find(kRuntimeToken)->health(), 30.0f));

    // Recycling slot 0 frees exactly that shell's pair and admits a new flight.
    tracker.clearSlot(0);
    assert(tracker.tracked() == P2GroinkStrikeTracker::kMaxTracked - 1);
    assert(!tracker.full());
    assert(tracker.firstHit(0, kRuntimeToken));

    // The new flight applies once and is then deduped for that shell.
    const P2GroinkStrikeResult hit =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(hit.applied && near(hit.health, 20.0f));
    assert(!tracker.firstHit(0, kRuntimeToken));
    if (tracker.firstHit(0, kRuntimeToken)) {
        (void)p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    }
    assert(near(registry.find(kRuntimeToken)->health(), 20.0f));

    // Another shell may still strike the same token once of its own once its
    // own slot recycles (the table was full again after slot 0 was re-recorded).
    assert(tracker.full());
    tracker.clearSlot(1);
    assert(tracker.firstHit(1, kRuntimeToken));
    const P2GroinkStrikeResult second =
        p2_groink_apply_strike(registry, input, captain(1.0f, 5.0f));
    assert(second.applied && near(second.health, 10.0f));
}

} // namespace

int main()
{
    testBombAppliesDamageThenDiesOnce();
    testWindPreservesImpulseWithoutHealthChange();
    testNonStrikeCasesAreNoOps();
    testRepeatedStrikesClampAtZero();
    testWildcardSinkUnknownRuntimeToken();
    testExactTokenTakesPrecedenceOverWildcard();
    testTrackerDedupsPerShellSlotButAllowsAnotherSlot();
    testMovingNonTerminalSegmentApplies();
    testWindStepCarriesImpulseWithoutHealthAndDedups();
    testTrackerRejectsOverflowAndRecycleAdmitsNewFlight();
    std::puts("p2_groink_strike_test PASS");
    return 0;
}
