// Standalone engine-free test for the generic held-object provider (#614).
//
// Compiles with -Ipc_port ONLY (no engine headers: the engine-free policy
// boundary is enforced by the build itself) and runs the provider lifecycle
// with host-callback-free assertions plus synthetic receipt-host-shaped
// confirmation inputs (booleans, never real ledger calls):
//
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port
//       tools/p2_held_object_test.cpp
//       pc_port/pc_p2_held_object.cpp
//       -o p2_held_object_test && ./p2_held_object_test
//
// A printed ATTACH alone cannot pass: every behavior below executes the
// provider lifecycle and asserts outcomes, including exactly-once release,
// single-set reward confirmation, interruption cleanup and stale-handle
// rejection.
#include <cmath>
#include <cstdio>

#include "pc_p2_held_object.h"

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const char* name)
{
    ++checks;
    if (!condition) {
        ++failures;
        std::printf("FAIL %s\n", name);
    }
}

P2HeldObjectVec3 vec(float x, float y, float z)
{
    P2HeldObjectVec3 v;
    v.x = x;
    v.y = y;
    v.z = z;
    return v;
}

} // namespace

int main()
{
    // 1. Attach validation: zero tokens, non-finite joint, duplicate
    //    carrier, exhaustion.
    {
        P2HeldObjectPool pool(1);
        P2HeldObjectHandle bad = pool.attach(0, 5, vec(0, 0, 0));
        check(!p2_held_object_handle_valid(bad), "zero-carrier-refused");
        bad = pool.attach(7, 0, vec(0, 0, 0));
        check(!p2_held_object_handle_valid(bad), "zero-item-refused");
        P2HeldObjectVec3 nan = vec(0, 0, 0);
        nan.y = std::nanf("");
        bad = pool.attach(7, 5, nan);
        check(!p2_held_object_handle_valid(bad), "nonfinite-joint-refused");
        P2HeldObjectHandle h = pool.attach(7, 5, vec(1, 2, 3));
        check(p2_held_object_handle_valid(h), "attach-valid");
        check(pool.isLive(h), "attach-live");
        check(pool.phase(h) == P2HeldObjectPhase::Attached, "attach-phase");
        check(pool.carrierToken(h) == 7, "attach-carrier");
        check(pool.itemToken(h) == 5, "attach-item");
        bad = pool.attach(7, 6, vec(0, 0, 0));
        check(!p2_held_object_handle_valid(bad), "duplicate-carrier-refused");
        bad = pool.attach(8, 6, vec(0, 0, 0));
        check(!p2_held_object_handle_valid(bad), "exhaustion-refused");
        check(pool.activeCount() == 1, "active-count");
    }
    // 2. Follow: attached tracks, dropped holds, non-finite rejected.
    {
        P2HeldObjectPool pool(1);
        P2HeldObjectHandle h = pool.attach(7, 5, vec(1, 2, 3));
        check(pool.followJoint(h, vec(4, 5, 6)), "follow-ok");
        check(pool.position(h).x == 4.0f, "follow-position");
        P2HeldObjectVec3 nan = vec(0, 0, 0);
        nan.z = std::nanf("");
        check(!pool.followJoint(h, nan), "follow-nonfinite-refused");
        check(pool.position(h).x == 4.0f, "follow-unchanged");
        check(pool.detach(h, vec(0, 0, -1), P2HeldObjectDetachReason::Dropped), "detach-ok");
        check(pool.phase(h) == P2HeldObjectPhase::Dropped, "detach-phase");
        check(pool.velocity(h).z == -1.0f, "detach-velocity");
        check(!pool.followJoint(h, vec(9, 9, 9)), "follow-dropped-refused");
        check(pool.position(h).x == 4.0f, "dropped-holds-position");
    }
    // 3. Detach exactly-once: second detach fails and is suppressed.
    {
        P2HeldObjectPool pool(1);
        P2HeldObjectHandle h = pool.attach(7, 5, vec(0, 0, 0));
        check(pool.detach(h, vec(1, 0, 0), P2HeldObjectDetachReason::Thrown), "detach-once");
        check(!pool.detach(h, vec(1, 0, 0), P2HeldObjectDetachReason::Thrown), "detach-twice-fails");
        check(pool.suppressedCount() == 1, "detach-suppressed-counted");
        check(pool.phase(h) == P2HeldObjectPhase::Dropped, "still-dropped");
    }
    // 4. Release exactly-once with reward flag; confirm single-set.
    {
        P2HeldObjectPool pool(1);
        P2HeldObjectHandle h = pool.attach(7, 5, vec(1, 1, 1));
        check(!pool.release(h), "release-attached-refused");
        check(pool.detach(h, vec(0, 0, 0), P2HeldObjectDetachReason::Dropped), "detach-for-release");
        check(pool.release(h), "release-ok");
        check(pool.phase(h) == P2HeldObjectPhase::Released, "release-phase");
        check(!pool.isLive(h), "released-not-live");
        check(pool.releaseCount() == 1, "release-count");
        check(pool.hasRelease(h), "has-release");
        const P2HeldObjectRelease& event = pool.lastRelease(h);
        check(event.carrierToken == 7 && event.itemToken == 5, "release-tokens");
        check(event.needsReward, "release-needs-reward");
        check(event.rewardGranted == -1, "release-unconfirmed");
        check(!pool.release(h), "release-twice-fails");
        check(pool.suppressedCount() == 2, "release-suppressed-counted");
        check(pool.confirmReward(h, true), "confirm-ok");
        check(pool.lastRelease(h).rewardGranted == 1, "confirm-recorded");
        check(!pool.confirmReward(h, false), "confirm-twice-fails");
        check(pool.lastRelease(h).rewardGranted == 1, "confirm-first-wins");
        check(pool.suppressedCount() == 3, "confirm-suppressed-counted");
        pool.clearRelease(h);
        check(!pool.hasRelease(h), "clear-release");
    }
    // 5. Carrier death drops in place; item loss releases without reward.
    {
        P2HeldObjectPool pool(2);
        P2HeldObjectHandle dead = pool.attach(7, 5, vec(1, 2, 3));
        check(pool.onCarrierDeath(dead), "carrier-death-ok");
        check(pool.phase(dead) == P2HeldObjectPhase::Dropped, "death-dropped");
        check(pool.velocity(dead).x == 0.0f, "death-zero-velocity");
        check(pool.release(dead), "death-release-ok");
        check(pool.lastRelease(dead).needsReward, "death-release-needs-reward");
        P2HeldObjectHandle lost = pool.attach(8, 6, vec(0, 0, 0));
        check(pool.onItemLost(lost), "item-lost-ok");
        check(pool.phase(lost) == P2HeldObjectPhase::Released, "lost-released");
        check(!pool.lastRelease(lost).needsReward, "lost-no-reward");
        check(!pool.isLive(lost), "lost-not-live");
        check(pool.releaseCount() == 1, "lost-not-counted-as-release");
    }
    // 6. Reset retires handles; slots are reusable with fresh generations.
    {
        P2HeldObjectPool pool(1);
        P2HeldObjectHandle h = pool.attach(7, 5, vec(0, 0, 0));
        pool.reset();
        check(!pool.isLive(h), "reset-retires-handle");
        check(pool.phase(h) == P2HeldObjectPhase::Free, "reset-frees-phase");
        check(!pool.hasRelease(h), "reset-clears-release");
        check(pool.activeCount() == 0, "reset-active-zero");
        P2HeldObjectHandle h2 = pool.attach(7, 5, vec(0, 0, 0));
        check(p2_held_object_handle_valid(h2), "reuse-valid");
        check(h2.generation != h.generation, "reuse-fresh-generation");
        check(pool.isLive(h2), "reuse-live");
    }
    // 7. Stale/invalid handles fail closed everywhere.
    {
        P2HeldObjectPool pool(1);
        P2HeldObjectHandle stale{};
        stale.slot = 0;
        stale.generation = 999;
        check(!pool.isLive(stale), "stale-not-live");
        check(!pool.followJoint(stale, vec(0, 0, 0)), "stale-follow-fails");
        check(!pool.detach(stale, vec(0, 0, 0), P2HeldObjectDetachReason::Dropped), "stale-detach-fails");
        check(!pool.release(stale), "stale-release-fails");
        check(!pool.confirmReward(stale, true), "stale-confirm-fails");
        check(!pool.hasRelease(stale), "stale-no-release");
        check(pool.phase(stale) == P2HeldObjectPhase::Free, "stale-free-phase");
        check(pool.carrierToken(stale) == 0, "stale-no-carrier");
    }
    std::printf("checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}