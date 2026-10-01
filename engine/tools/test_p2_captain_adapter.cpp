#include "pc_p2_captain.h"
#include <cassert>
#include <cstdint>
#include <cstdio>

// Lane 12 engine-facing adapter test (#130). This is NOT a live Navi runtime.
// Every engine fact comes from an in-process double supplied through
// P2CaptainHostOps: two fake Pikmin actors and a fake Navi whose health,
// mNavi owner slot and setHealth/setOwner call counts are observable. The
// adapter policy/ownership/health-mirroring semantics under test are the same
// code the live pc_p2_captain.cpp drives; only the engine callbacks differ.

namespace {

struct FakeNavi {
    float health = 0.0f;
};

// ownerSlot: P2CaptainInvalid means free/unowned (the fake's "mNavi == null").
struct FakePiki {
    std::uint32_t id = 0;
    int ownerSlot = P2CaptainInvalid;
};

struct FakeScene {
    FakeNavi navi0;
    FakeNavi navi1;
    bool captain0Present = true;
    bool twoCaptains = false;
    FakePiki pikiA;
    FakePiki pikiB;
    int setHealthCalls = 0;
    int setOwnerCalls = 0;
    int prepareCalls = 0;
    int lastPreparedOwner = P2CaptainInvalid;
    bool refusePrepare = false;
    bool dieOnPrepare = false;
    P2CaptainAdapter* activeAdapter = nullptr;
    std::uint64_t prepareRecaptureEpoch = 0;
    std::uint64_t recaptureReleaseEpoch = 0;
    int notifyActiveCalls = 0;
    int lastActiveSlot = P2CaptainInvalid;
    int notifyKnockoutCalls = 0;
    int lastKnockoutSlot = P2CaptainInvalid;
};

P2CaptainHandle fake_captain_at(void* ctx, int slot)
{
    FakeScene* s = static_cast<FakeScene*>(ctx);
    if (slot == P2CaptainA) return s->captain0Present ? static_cast<void*>(&s->navi0) : nullptr;
    if (slot == P2CaptainB) return s->twoCaptains ? static_cast<void*>(&s->navi1) : nullptr;
    return nullptr;
}

float fake_get_health(void*, P2CaptainHandle captain)
{
    return static_cast<FakeNavi*>(captain)->health;
}

void fake_set_health(void* ctx, P2CaptainHandle captain, float value)
{
    static_cast<FakeScene*>(ctx)->setHealthCalls++;
    static_cast<FakeNavi*>(captain)->health = value;
}

std::uint32_t fake_actor_id(void*, P2PikiHandle actor) { return static_cast<FakePiki*>(actor)->id; }

int fake_owner_slot(void*, P2PikiHandle actor) { return static_cast<FakePiki*>(actor)->ownerSlot; }

void fake_set_owner_slot(void* ctx, P2PikiHandle actor, int slot)
{
    static_cast<FakeScene*>(ctx)->setOwnerCalls++;
    static_cast<FakePiki*>(actor)->ownerSlot = slot;
}

// Squad-action release before ownership is cleared
// (codex/p2-lane12-review 5cbb2f351/b4ac39825, #130): runs while the captain
// pointer is still valid, then the adapter revalidates. The double can
// refuse, kill (predeath revocation), or reentrantly recapture under a newer
// epoch; the stale outer capture must never touch the replacement.
bool fake_prepare_capture(void* ctx, P2PikiHandle actor)
{
    FakeScene* s = static_cast<FakeScene*>(ctx);
    FakePiki* piki = static_cast<FakePiki*>(actor);
    s->prepareCalls++;
    s->lastPreparedOwner = piki->ownerSlot;
    if (s->refusePrepare) return false;
    if (s->dieOnPrepare) {
        // Predeath during cleanup: drop the capture without engine writes.
        if (s->activeAdapter) s->activeAdapter->forgetActor(actor);
        return true;
    }
    if (s->prepareRecaptureEpoch && s->activeAdapter) {
        const std::uint64_t epoch = s->prepareRecaptureEpoch;
        s->prepareRecaptureEpoch = 0;
        // Reentrant interruption then replacement capture under a newer tick.
        assert(s->activeAdapter->releaseActor(s->recaptureReleaseEpoch, actor, P2CaptainInvalid));
        assert(s->activeAdapter->captureActor(epoch, actor));
    }
    return true;
}

int fake_enumerate(void* ctx, P2PikiHandle* out, int capacity)
{
    FakeScene* s = static_cast<FakeScene*>(ctx);
    int count = 0;
    if (count < capacity) out[count++] = static_cast<void*>(&s->pikiA);
    if (count < capacity) out[count++] = static_cast<void*>(&s->pikiB);
    return count;
}

void fake_notify_active(void* ctx, int slot)
{
    FakeScene* s = static_cast<FakeScene*>(ctx);
    s->notifyActiveCalls++;
    s->lastActiveSlot = slot;
}

void fake_notify_knockout(void* ctx, int slot)
{
    FakeScene* s = static_cast<FakeScene*>(ctx);
    s->notifyKnockoutCalls++;
    s->lastKnockoutSlot = slot;
}

P2CaptainHostOps fake_ops(FakeScene& scene)
{
    P2CaptainHostOps ops;
    ops.context      = &scene;
    ops.captainAt    = &fake_captain_at;
    ops.getHealth    = &fake_get_health;
    ops.setHealth    = &fake_set_health;
    ops.actorId      = &fake_actor_id;
    ops.ownerSlot    = &fake_owner_slot;
    ops.prepareCapture = &fake_prepare_capture;
    ops.setOwnerSlot = &fake_set_owner_slot;
    ops.enumerate    = &fake_enumerate;
    ops.notifyActive   = &fake_notify_active;
    ops.notifyKnockout = &fake_notify_knockout;
    return ops;
}

void test_single_captain_slot0(FakeScene& scene)
{
    P2CaptainAdapter adapter;

    // A partial host is refused rather than silently skipping engine writes.
    P2CaptainHostOps partial;
    partial.captainAt = &fake_captain_at;
    assert(!adapter.bind(partial));

    assert(adapter.bind(fake_ops(scene)));
    assert(adapter.setup());
    assert(adapter.policy().activeCaptain() == P2CaptainA);
    assert(adapter.policy().present(P2CaptainA));
    assert(!adapter.policy().present(P2CaptainB));
    assert(!adapter.policy().controllable(P2CaptainB));

    // setup() adopted the live Piki::mNavi ownership into slot 0.
    assert(adapter.ownsActor(101) && adapter.ownsActor(102));
    assert(adapter.ownerOfActor(101) == P2CaptainA);
    assert(adapter.health(P2CaptainA) == 75.0f);

    // Single-captain reality: no switch, and capture of the only captain is
    // refused because it would strand the player with zero control.
    assert(!adapter.switchActive(P2CaptainA));
    assert(!adapter.switchActive(P2CaptainB));
    assert(!adapter.captureCaptain(P2CaptainA, 5));
    assert(adapter.policy().phase(P2CaptainA) == P2CaptainPhase::Active);

    // Health set writes through to the engine and mirrors into the policy.
    assert(adapter.setHealth(P2CaptainA, 42.0f));
    assert(scene.navi0.health == 42.0f);
    assert(adapter.health(P2CaptainA) == 42.0f);
    assert(scene.setHealthCalls == 1);
    assert(!adapter.setHealth(P2CaptainB, 10.0f)); // absent slot
    assert(!adapter.setHealth(P2CaptainA, -1.0f)); // invalid value

    // refresh() pulls the engine value back in without changing phase.
    scene.navi0.health = 90.0f;
    assert(adapter.refresh());
    assert(adapter.health(P2CaptainA) == 90.0f);

    // A captor grabs a Pikmin: the squad action is abandoned while the captain
    // pointer is still valid, then ownership is cleared. Stale captor epochs
    // cannot release it.
    scene.activeAdapter = &adapter;
    assert(adapter.captureActor(900, &scene.pikiA));
    assert(scene.prepareCalls == 1 && scene.lastPreparedOwner == P2CaptainA);
    assert(adapter.isCaptiveFor(900, &scene.pikiA));
    assert(!adapter.isCaptiveFor(901, &scene.pikiA));
    assert(adapter.captiveCount() == 1);
    assert(scene.pikiA.ownerSlot == P2CaptainInvalid);
    assert(!adapter.ownsActor(101));
    assert(adapter.ownsActor(102));
    assert(!adapter.captureActor(901, &scene.pikiA));      // no double capture
    assert(!adapter.releaseActor(902, &scene.pikiA, P2CaptainA)); // stale epoch
    assert(adapter.releaseActor(900, &scene.pikiA, P2CaptainA));
    assert(scene.pikiA.ownerSlot == P2CaptainA);
    assert(adapter.ownsActor(101));

    // Captor death frees held actors to the ground (engine owner cleared).
    assert(adapter.captureActor(910, &scene.pikiB));
    assert(scene.pikiB.ownerSlot == P2CaptainInvalid);
    std::vector<std::uint32_t> dropped = adapter.dropAllCaptured(910);
    assert(dropped.size() == 1 && dropped[0] == 102);
    assert(scene.pikiB.ownerSlot == P2CaptainInvalid);
    assert(adapter.captiveCount() == 0);

    // reload() restores a captive to its previous captain in the engine and
    // conserves the squad.
    assert(adapter.policy().claim(P2CaptainA, 102));
    scene.pikiB.ownerSlot = P2CaptainA;
    assert(adapter.ownsActor(102));
    assert(adapter.captureActor(904, &scene.pikiB));
    assert(scene.pikiB.ownerSlot == P2CaptainInvalid);
    assert(adapter.reload());
    assert(scene.pikiB.ownerSlot == P2CaptainA);
    assert(adapter.captiveCount() == 0);
    assert(adapter.ownsActor(102));

    // teardown drops the binding and all policy bookkeeping; rebinding works.
    adapter.teardown();
    assert(!adapter.bound());
    assert(!adapter.ownsActor(102));
    assert(adapter.bind(fake_ops(scene)));
    assert(adapter.setup());
    scene.activeAdapter = nullptr;
}

// Revocable squad captures bound to captor ticks
// (codex/p2-lane12-review c29ec8398/5cbb2f351/b4ac39825, #130): action release
// before clearing ownership, and a replacement capture made during that
// release is preserved while the stale outer capture is revoked silently.
void test_capture_prepare_revalidate(FakeScene& scene)
{
    P2CaptainAdapter adapter;
    assert(adapter.bind(fake_ops(scene)));
    assert(adapter.setup());
    scene.activeAdapter = &adapter;

    // Refused action release refuses the capture: no owner write, not captive.
    scene.pikiA.ownerSlot = P2CaptainA;
    const int writes = scene.setOwnerCalls;
    scene.refusePrepare = true;
    assert(!adapter.captureActor(920, &scene.pikiA));
    assert(scene.pikiA.ownerSlot == P2CaptainA && scene.setOwnerCalls == writes);
    assert(!adapter.isCaptiveFor(920, &scene.pikiA) && adapter.captiveCount() == 0);
    scene.refusePrepare = false;

    // Predeath during cleanup revokes without engine writes.
    scene.dieOnPrepare = true;
    assert(!adapter.captureActor(921, &scene.pikiA));
    assert(scene.pikiA.ownerSlot == P2CaptainA && scene.setOwnerCalls == writes);
    assert(!adapter.isCaptiveFor(921, &scene.pikiA) && adapter.captiveCount() == 0);
    scene.dieOnPrepare = false;

    // Ordinary capture, then a reentrant interruption + replacement capture
    // under a newer tick during the outer release: the outer capture fails
    // and the replacement is preserved with no further owner writes.
    scene.pikiA.ownerSlot = P2CaptainA; // still attached after the 922 release
    scene.recaptureReleaseEpoch = 0;
    scene.prepareRecaptureEpoch = 0;
    assert(adapter.captureActor(922, &scene.pikiA));
    assert(scene.pikiA.ownerSlot == P2CaptainInvalid);
    assert(adapter.releaseActor(922, &scene.pikiA, P2CaptainA));
    assert(scene.pikiA.ownerSlot == P2CaptainA);

    // True reentrant path: during captureActor(924)'s action release, a
    // callback releases 924 and recaptures under 925. The outer capture is
    // revoked without touching the replacement.
    scene.recaptureReleaseEpoch = 924;
    scene.prepareRecaptureEpoch = 925;
    const int writesBeforeReentrant = scene.setOwnerCalls;
    assert(!adapter.captureActor(924, &scene.pikiA));
    assert(!adapter.isCaptiveFor(924, &scene.pikiA));
    assert(adapter.isCaptiveFor(925, &scene.pikiA));
    assert(adapter.captiveCount() == 1);
    assert(scene.pikiA.ownerSlot == P2CaptainInvalid); // inner capture's write
    assert(scene.setOwnerCalls == writesBeforeReentrant + 2); // inner ops only
    assert(!adapter.releaseActor(924, &scene.pikiA, P2CaptainA)); // stale
    assert(adapter.isCaptiveFor(925, &scene.pikiA));
    assert(adapter.releaseActor(925, &scene.pikiA, P2CaptainA));
    assert(scene.pikiA.ownerSlot == P2CaptainA);

    // Predeath revocation performs no actor writes.
    assert(adapter.captureActor(926, &scene.pikiA));
    const int writesBeforeForget = scene.setOwnerCalls;
    adapter.forgetActor(&scene.pikiA);
    assert(scene.setOwnerCalls == writesBeforeForget);
    assert(!adapter.isCaptiveFor(926, &scene.pikiA) && adapter.captiveCount() == 0);
    assert(!adapter.releaseActor(926, &scene.pikiA, P2CaptainA));
    scene.activeAdapter = nullptr;
}

// Splitting an adopted squad between two captains mirrors Piki::mNavi through
// the engine callbacks. Engine double, not live two-captain runtime.
void test_two_captain_split_double(FakeScene& scene)
{
    P2CaptainAdapter adapter;
    assert(adapter.bind(fake_ops(scene)));
    assert(adapter.setup());
    assert(adapter.activeCaptain() == P2CaptainA);
    assert(adapter.ownerOfActor(101) == P2CaptainA);
    assert(adapter.ownerOfActor(102) == P2CaptainA);

    std::vector<std::uint32_t> moved = adapter.splitSquad(P2CaptainA, P2CaptainB, 1);
    assert(moved.size() == 1 && moved[0] == 101);
    assert(adapter.ownerOfActor(101) == P2CaptainB);
    assert(scene.pikiA.ownerSlot == P2CaptainB); // mirrored into the engine
    assert(adapter.ownerOfActor(102) == P2CaptainA);
    assert(scene.pikiB.ownerSlot == P2CaptainA);

    const std::uint32_t named[1] = { 102 };
    assert(adapter.transferSquad(P2CaptainA, P2CaptainB, named, 1) == 1);
    assert(adapter.ownerOfActor(102) == P2CaptainB);
    assert(scene.pikiB.ownerSlot == P2CaptainB);

    // Splitting an absent slot is refused.
    assert(adapter.splitSquad(P2CaptainA, P2CaptainA, 1).empty());
}

// The adapter is engine-generic: a host that exposes a second captain exercises
// the capture/transfer path that the single-captain port cannot reach. This is
// still an engine double, not live two-captain runtime.
void test_two_captain_transfer_double(FakeScene& scene)
{
    P2CaptainAdapter adapter;
    assert(adapter.bind(fake_ops(scene)));
    assert(adapter.setup());
    assert(adapter.activeCaptain() == P2CaptainA);

    assert(adapter.switchActive(P2CaptainB));
    assert(adapter.activeCaptain() == P2CaptainB);
    assert(adapter.policy().phase(P2CaptainA) == P2CaptainPhase::Idle);
    // The switch is routed into the engine's active-captain helper.
    assert(scene.notifyActiveCalls == 1 && scene.lastActiveSlot == P2CaptainB);

    // B owns 102: capture B hands 102 to A and mirrors it into the engine.
    adapter.policy().abandon(P2CaptainA, 102);
    scene.pikiB.ownerSlot = P2CaptainB;
    assert(adapter.adoptSquad() >= 0);
    assert(adapter.ownerOfActor(102) == P2CaptainB);
    assert(adapter.captureCaptain(P2CaptainB, 77));
    assert(adapter.policy().phase(P2CaptainB) == P2CaptainPhase::Captured);
    assert(adapter.activeCaptain() == P2CaptainA);
    assert(adapter.ownerOfActor(102) == P2CaptainA);
    assert(scene.pikiB.ownerSlot == P2CaptainA);
    assert(adapter.ownsActor(101) && adapter.ownsActor(102));
    // Capture routed control to the survivor.
    assert(scene.notifyActiveCalls == 2 && scene.lastActiveSlot == P2CaptainA);

    // Once B is down, the last controllable captain cannot be captured.
    assert(!adapter.captureCaptain(P2CaptainA, 78));
    assert(adapter.releaseCaptain(P2CaptainB, 77));
    assert(adapter.policy().phase(P2CaptainB) == P2CaptainPhase::Idle);

    // Knockout routes to the engine dead flag and the surviving captain.
    assert(adapter.damageCaptain(P2CaptainB, 100.0f));
    assert(adapter.policy().phase(P2CaptainB) == P2CaptainPhase::Down);
    assert(scene.notifyKnockoutCalls == 1 && scene.lastKnockoutSlot == P2CaptainB);
    assert(scene.notifyActiveCalls == 3 && scene.lastActiveSlot == P2CaptainA);
    // A non-lethal hit does not report a knockout.
    assert(!adapter.damageCaptain(P2CaptainA, 1.0f));
    assert(adapter.policy().phase(P2CaptainA) == P2CaptainPhase::Active);
}

} // namespace

int main()
{
    {
        FakeScene scene;
        scene.navi0.health = 75.0f;
        scene.pikiA = FakePiki{101, P2CaptainA};
        scene.pikiB = FakePiki{102, P2CaptainA};
        test_single_captain_slot0(scene);
    }
    {
        FakeScene scene;
        scene.navi0.health = 100.0f;
        scene.navi1.health = 100.0f;
        scene.twoCaptains = true;
        scene.pikiA = FakePiki{101, P2CaptainA};
        scene.pikiB = FakePiki{102, P2CaptainA};
        test_two_captain_transfer_double(scene);
    }
    {
        FakeScene scene;
        scene.navi0.health = 100.0f;
        scene.navi1.health = 100.0f;
        scene.twoCaptains = true;
        scene.pikiA = FakePiki{101, P2CaptainA};
        scene.pikiB = FakePiki{102, P2CaptainA};
        test_two_captain_split_double(scene);
    }
    {
        FakeScene scene;
        scene.navi0.health = 100.0f;
        scene.pikiA = FakePiki{101, P2CaptainA};
        scene.pikiB = FakePiki{102, P2CaptainA};
        test_capture_prepare_revalidate(scene);
    }

    std::puts("PASS P2_CAPTAIN_ADAPTER");
    return 0;
}
