#include "pc_p2_fuefuki_binding.h"
// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <cstring>
#include <limits>
#include <vector>

using S = P2FuefukiFsmState;
static constexpr float DT = 1.0f / 30.0f;

// ---------------------------------------------------------------- mock host
struct MockHost {
    P2FuefukiBinding* binding = nullptr;
    P2FuefukiProbeResult probe;
    std::vector<P2FuefukiSquadEntry> squad;   // world Pikmin the scan may list
    std::vector<std::uint32_t> pings;         // follow-action pings this tick
    bool enumerateFails = false;
    bool pingFails = false;
    bool rejectFollowStart = false;
    // records
    std::vector<std::uint32_t> started;
    std::vector<std::pair<std::uint32_t, int>> ended;
    std::vector<bool> heldAtEnd;              // ownership state when followEnd ran
    std::vector<std::pair<std::uint32_t, std::uint32_t>> writes;
    int killCalls = 0;
    bool killCarcass = false;
};

static void mockProbe(void* ctx, P2FuefukiProbeResult& out)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    out         = m->probe;
}

static int mockEnumerate(void* ctx, float, float, float radius, P2FuefukiSquadEntry* out, int capacity)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    if (m->enumerateFails) return -1;
    int n = 0;
    if (radius <= 0.0f) return 0; // mock world: nothing inside a zero ring
    for (const P2FuefukiSquadEntry& e : m->squad) {
        if (n >= capacity) break;
        out[n++] = e;
    }
    return n;
}

static bool mockFollowStart(void* ctx, std::uint32_t pikmin)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    if (m->rejectFollowStart) return false;
    m->started.push_back(pikmin);
    return true;
}

static void mockFollowEnd(void* ctx, std::uint32_t pikmin, int reason)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    m->ended.push_back({ pikmin, reason });
    // Contract-critical: for panic releases the table release is committed
    // before this callback runs.
    m->heldAtEnd.push_back(m->binding->getFsm().squad().holds(pikmin));
}

static int mockPingCollect(void* ctx, std::uint32_t* out, int capacity)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    if (m->pingFails) return -1;
    int n = 0;
    for (std::uint32_t id : m->pings) {
        if (n >= capacity) break;
        out[n++] = id;
    }
    return n;
}

static void mockOwnershipWrite(void* ctx, std::uint32_t pikmin, std::uint32_t naviId)
{
    static_cast<MockHost*>(ctx)->writes.push_back({ pikmin, naviId });
}

static void mockKill(void* ctx, bool carcassCarryAnim)
{
    MockHost* m = static_cast<MockHost*>(ctx);
    m->killCalls++;
    m->killCarcass = carcassCarryAnim;
}

static P2FuefukiHost makeHost(MockHost& m)
{
    P2FuefukiHost h;
    h.context        = &m;
    h.probe          = mockProbe;
    h.enumerate      = mockEnumerate;
    h.followStart    = mockFollowStart;
    h.followEnd      = mockFollowEnd;
    h.pingCollect    = mockPingCollect;
    h.ownershipWrite = mockOwnershipWrite;
    h.kill           = mockKill;
    return h;
}

static P2FuefukiFsmParms bindParms()
{
    P2FuefukiFsmParms p;
    p.maxGroundTime = 2.0f;
    p.airborneTime = 0.2f;
    p.minWhistleTime = 0.3f;
    p.maxWhistleTimeNoSquad = 0.4f;
    p.maxWhistleTimeWithSquad = 1.0f;
    p.struggleTime = 10.0f;
    p.jumpTime = 0.0f;
    p.attackRadius = 100.0f;
    p.castDuration = 1.2f;
    return p;
}

static P2FuefukiBindTick baseTick()
{
    P2FuefukiBindTick t;
    t.delta       = DT;
    t.health      = 100.0f;
    t.animPlaying = true;
    return t;
}

static void driveUntil(P2FuefukiBinding& b, MockHost& m, S target, int maxTicks)
{
    P2FuefukiBindTick t = baseTick();
    for (int i = 0; i < maxTicks && b.getFsm().getState() != target; i++) {
        // Land needs its KEYEVENT_2/3/END motion sequence to progress.
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
    (void)m;
}

int main()
{
    // --- bind validation: every seam callback is required ---
    {
        MockHost m;
        P2FuefukiBinding b;
        P2FuefukiHost h = makeHost(m);
        h.kill          = nullptr;
        assert(!b.bind(h, bindParms(), nullptr));
        h           = makeHost(m);
        h.ownershipWrite = nullptr;
        assert(!b.bind(h, bindParms(), nullptr));
        assert(b.bind(makeHost(m), bindParms(), nullptr));
        assert(!b.bind(makeHost(m), bindParms(), nullptr)); // no rebind
    }

    // --- full seam cycle: scan -> claim -> follow start -> ping -> cast
    //     end -> suspend end -> re-claim; no ownership write anywhere ---
    {
        MockHost m;
        m.probe.valid = true;
        m.probe.x = 10.0f; m.probe.z = 20.0f;
        P2FuefukiSquadEntry e;
        e.id = 7; e.living = e.callable = true;
        m.squad.push_back(e);
        P2FuefukiBinding b;
        m.binding = &b;
        assert(b.bind(makeHost(m), bindParms(), nullptr));
        P2FuefukiBindOut out = b.spawn(1);
        assert(out.accepted && out.state == S::Land && out.fsm.teleportToTarget);

        driveUntil(b, m, S::Whisle, 120);
        // scan+claim happen on cast ticks; mock follow starts
        P2FuefukiBindTick t = baseTick();
        out                 = b.tick(t);
        assert(out.claimed == 1 && m.started.size() == 1 && m.started[0] == 7);
        assert(m.writes.empty()); // claim is NOT an ownership write
        m.pings = { 7 };          // follow action pings back each tick
        // ride out the cast; claims persist past the fixed cast duration
        driveUntil(b, m, S::Turn, 120);
        assert(b.getFsm().squad().holds(7));
        assert(m.ended.empty());
        // jump-away via the fp01 probe-free path (appear timer) -> Stay suspends
        driveUntil(b, m, S::Stay, 200);
        assert(m.ended.size() == 1 && m.ended[0].first == 7
               && m.ended[0].second == P2FUEFUKI_END_SUSPEND);
        assert(m.heldAtEnd[0] == false);
        assert(!b.onCaptainWhistle(7, 1)); // suspend is not reclaimable
        // re-land and re-claim the same Pikmin
        driveUntil(b, m, S::Whisle, 300);
        out = b.tick(t);
        assert(out.claimed == 1 && m.started.size() == 2);
        assert(m.writes.empty());
    }

    // --- death: panic release ordering, reclaim interception, non-routes,
    //     kill + Carry carcass ---
    {
        MockHost m;
        m.probe.valid = true;
        P2FuefukiSquadEntry e;
        e.id = 8; e.living = e.callable = true;
        m.squad.push_back(e);
        P2FuefukiBinding b;
        m.binding = &b;
        assert(b.bind(makeHost(m), bindParms(), nullptr));
        b.spawn(1);
        driveUntil(b, m, S::Whisle, 120);
        b.tick(baseTick());
        assert(m.started.size() == 1);

        P2FuefukiBindTick t = baseTick();
        t.health            = 0.0f;
        P2FuefukiBindOut out = b.tick(t); // -> requestFinish Dead
        if (out.fsm.requestFinishMotion) {
            t.keyEvent = 4;
            out        = b.tick(t);
        }
        assert(out.state == S::Dead);
        assert(m.ended.size() == 1 && m.ended[0].second == P2FUEFUKI_END_PANIC);
        assert(m.heldAtEnd[0] == false); // release committed before callback
        // a live beetle's other followers are never reclaimable; this one is
        assert(b.onCaptainWhistle(8, 1));
        assert(m.writes.size() == 1 && m.writes[0].first == 8 && m.writes[0].second == 1);
        assert(!b.onCaptainWhistle(8, 1)); // exactly once
        assert(m.writes.size() == 1);
        // captain switch / party combine are explicit non-routes
        assert(!b.onCaptainSwitch(8));
        assert(!b.onPartyCombine(8));
        assert(m.writes.size() == 1);
        // dead-anim END delivers kill with the Carry carcass flag
        P2FuefukiBindTick dk = baseTick();
        dk.health            = 0.0f;
        dk.keyEvent          = 4;
        out                  = b.tick(dk);
        assert(out.kill && out.carcassCarryAnim);
        assert(m.killCalls == 1 && m.killCarcass);
    }

    // --- probe / enumeration / ping failures reject the tick ---
    {
        MockHost m;
        m.probe.valid = true;
        P2FuefukiBinding b;
        m.binding = &b;
        assert(b.bind(makeHost(m), bindParms(), nullptr));
        b.spawn(1);
        m.probe.valid = false;
        assert(!b.tick(baseTick()).accepted);
        m.probe.valid = true;
        m.probe.x     = std::numeric_limits<float>::quiet_NaN();
        assert(!b.tick(baseTick()).accepted);
        m.probe.x = 0.0f;
        assert(b.tick(baseTick()).accepted);
        m.enumerateFails = true;
        driveUntil(b, m, S::Whisle, 120);
        assert(!b.tick(baseTick()).accepted);
        m.enumerateFails = false;
        assert(b.tick(baseTick()).accepted);
        m.pingFails = true;
        assert(!b.tick(baseTick()).accepted);
        m.pingFails = false;
        P2FuefukiBindTick bad = baseTick();
        bad.delta             = -DT;
        assert(!b.tick(bad).accepted);
        assert(b.tick(baseTick()).accepted);
    }

    // --- shared table: two beetles, one Pikmin, single controller ---
    {
        P2FuefukiOwnershipTable shared;
        shared.invalidateDomain();
        MockHost ma, mb;
        ma.probe.valid = mb.probe.valid = true;
        P2FuefukiSquadEntry e;
        e.id = 9; e.living = e.callable = true;
        ma.squad.push_back(e);
        mb.squad.push_back(e);
        P2FuefukiBinding a, b;
        ma.binding = &a;
        mb.binding = &b;
        assert(a.bind(makeHost(ma), bindParms(), &shared));
        assert(b.bind(makeHost(mb), bindParms(), &shared));
        a.spawn(1);
        b.spawn(2);
        driveUntil(a, ma, S::Whisle, 120);
        driveUntil(b, mb, S::Whisle, 120);
        P2FuefukiBindOut outA = a.tick(baseTick()); // first in fixed ordering
        P2FuefukiBindOut outB = b.tick(baseTick());
        assert(outA.claimed == 1 && ma.started.size() == 1);
        assert(outB.claimed == 0 && mb.started.empty()); // exclusivity across binders
        assert(shared.heldBy(9, 1));
        assert(!b.getFsm().squad().holds(9));
    }

    puts("p2_fuefuki_binding_test PASS");
}
