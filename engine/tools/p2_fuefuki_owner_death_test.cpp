// Engine-free owner-death release test (#245 slice 2). Proves that
// P2FuefukiBinding::killVehicle() — the host forget/doKill seam's release path —
// frees every held whistle-stolen follower exactly as a natural health<=0 -> Dead
// transit would: ownerDied commits the Panic release, followEnd(PANIC) fires once
// per follower, the hold clears, and the follower becomes whistle-reclaimable.
// Idempotent after a normal death.

#include "pc_p2_fuefuki_binding.h"
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <vector>

using S = P2FuefukiFsmState;
static constexpr float DT = 1.0f / 30.0f;

struct MockHost {
    P2FuefukiBinding* binding = nullptr;
    P2FuefukiProbeResult probe;
    std::vector<P2FuefukiSquadEntry> squad;
    std::vector<std::uint32_t> pings;
    std::vector<std::uint32_t> started;
    std::vector<std::pair<std::uint32_t, int>> ended;
    std::vector<bool> heldAtEnd;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> writes;
};

static void mockProbe(void* ctx, P2FuefukiProbeResult& out) { out = static_cast<MockHost*>(ctx)->probe; }
static int mockEnumerate(void* ctx, float, float, float radius, P2FuefukiSquadEntry* out, int capacity)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    if (radius <= 0.0f) return 0;
    int n = 0;
    for (const P2FuefukiSquadEntry& e : m->squad) {
        if (n >= capacity) break;
        out[n++] = e;
    }
    return n;
}
static bool mockFollowStart(void* ctx, std::uint32_t id) { static_cast<MockHost*>(ctx)->started.push_back(id); return true; }
static void mockFollowEnd(void* ctx, std::uint32_t id, int reason)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    m->ended.push_back({ id, reason });
    m->heldAtEnd.push_back(m->binding->getFsm().squad().holds(id));
}
static int mockPingCollect(void* ctx, std::uint32_t* out, int capacity)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    int n = 0;
    for (std::uint32_t id : m->pings) { if (n >= capacity) break; out[n++] = id; }
    return n;
}
static void mockOwnershipWrite(void* ctx, std::uint32_t id, std::uint32_t navi)
{
    static_cast<MockHost*>(ctx)->writes.push_back({ id, navi });
}
static void mockKill(void*, bool) {}

static P2FuefukiHost makeHost(MockHost& m)
{
    P2FuefukiHost h;
    h.context = &m; h.probe = mockProbe; h.enumerate = mockEnumerate;
    h.followStart = mockFollowStart; h.followEnd = mockFollowEnd;
    h.pingCollect = mockPingCollect; h.ownershipWrite = mockOwnershipWrite;
    h.kill = mockKill;
    return h;
}

static P2FuefukiFsmParms parms()
{
    P2FuefukiFsmParms p;
    p.maxGroundTime = 2.0f; p.airborneTime = 0.2f; p.minWhistleTime = 0.3f;
    p.maxWhistleTimeNoSquad = 0.4f; p.maxWhistleTimeWithSquad = 1.0f;
    p.struggleTime = 10.0f; p.attackRadius = 100.0f; p.castDuration = 1.2f;
    return p;
}

static P2FuefukiBindTick baseTick()
{
    P2FuefukiBindTick t;
    t.delta = DT; t.health = 100.0f; t.animPlaying = true;
    return t;
}

static void driveUntil(P2FuefukiBinding& b, S target, int maxTicks)
{
    P2FuefukiBindTick t = baseTick();
    for (int i = 0; i < maxTicks && b.getFsm().getState() != target; i++) {
        t.keyEvent = (b.getFsm().getState() == S::Land) ? 2 + (i % 3) : 0;
        if (t.keyEvent > 4) t.keyEvent = 4;
        P2FuefukiBindOut out = b.tick(t);
        assert(out.accepted);
        if (b.getFsm().getState() != S::Land && out.fsm.requestFinishMotion) {
            t.keyEvent = 4;
            b.tick(t);
        }
    }
    assert(b.getFsm().getState() == target);
}

int main()
{
    // Claim one follower, then killVehicle(): PANIC release, followEnd once,
    // hold cleared, follower reclaimable, FSM Dead.
    {
        MockHost m;
        m.probe.valid = true;
        P2FuefukiSquadEntry e;
        e.id = 7; e.living = e.callable = true;
        m.squad.push_back(e);
        P2FuefukiBinding b;
        m.binding = &b;
        assert(b.bind(makeHost(m), parms(), nullptr));
        assert(b.spawn(1).accepted);
        driveUntil(b, S::Whisle, 120);
        P2FuefukiBindOut claimed = b.tick(baseTick());
        assert(claimed.claimed == 1 && m.started.size() == 1 && m.started[0] == 7);
        assert(m.writes.empty());

        P2FuefukiBindOut killed = b.killVehicle();
        assert(killed.accepted && killed.state == S::Dead);
        assert(killed.endedPanic == 1);
        assert(m.ended.size() == 1 && m.ended[0].first == 7
               && m.ended[0].second == P2FUEFUKI_END_PANIC);
        assert(m.heldAtEnd[0] == false);           // release committed before callback
        assert(!b.getFsm().squad().holds(7));      // ownership cleared

        // Source-faithful: death commits the follower to the Panic (reclaimable)
        // set, so a captain whistle reclaims it exactly once via the lane write.
        assert(b.onCaptainWhistle(7, 0));
        assert(m.writes.size() == 1 && m.writes[0].first == 7);
        assert(!b.onCaptainWhistle(7, 0));         // exactly once
        assert(m.writes.size() == 1);

        // Idempotent after a normal death: a second killVehicle releases nothing.
        P2FuefukiBindOut again = b.killVehicle();
        assert(again.accepted && again.endedPanic == 0);
        assert(m.ended.size() == 1);
    }

    // No claims: killVehicle() is still a valid Dead transit with zero releases.
    {
        MockHost m;
        m.probe.valid = true;
        P2FuefukiBinding b;
        m.binding = &b;
        assert(b.bind(makeHost(m), parms(), nullptr));
        assert(b.spawn(1).accepted);
        P2FuefukiBindOut killed = b.killVehicle();
        assert(killed.accepted && killed.state == S::Dead && killed.endedPanic == 0);
        assert(m.ended.empty() && m.writes.empty());
    }
    puts("p2_fuefuki_owner_death_test PASS");
    return 0;
}
