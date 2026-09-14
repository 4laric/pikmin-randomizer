#include "pc_p2_fuefuki_binding.h"
#include <cassert>
#include <cstdio>
#include <algorithm>
#include <vector>

using S = P2FuefukiFsmState;
static constexpr float DT = 1.0f / 30.0f;

// Source trace ground-truth (issue #245, open item "suspend brain-fallback
// (Formation vs Free)" -- resolved): ActTeki::getNextAIType() returns
// ACT_Free (include/PikiAI.h:1254); Brain::exec routes the Success exit to
// start(ACT_Free, nullptr) (src/plugProjectKandoU/aiAction.cpp:108-110) so
// the ACT_Formation/searchOrima() branch is never reached for a Fuefuki
// follower. The stored piki->mNavi is not consulted and ActFree::init
// clears it (src/plugProjectKandoU/aiFree.cpp:33): a suspended follower
// detaches and re-attaches only through a future captain touch or whistle
// path. The source force-invokes its situation scan BEFORE the fallback
// (Brain::exec, aiAction.cpp:92-95) -- a released Pikmin may be re-tasked
// there (notably ACT_Attack on a grounded, bittered beetle within
// mEnemySearchRange) before Free applies; that re-task is a world-side
// gate the lane cannot see engine-free.
//
// Both aiTeki.cpp triggers -- isFlying (lines 84-87) and isBittered
// (lines 90-94) -- set mToEmote and return ACTEXEC_Success through the
// same exit; the policy exposes one suspend() call.

static P2FuefukiFsmParms testParms()
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

static P2FuefukiFsmInput baseIn()
{
    P2FuefukiFsmInput in;
    in.delta       = DT;
    in.health      = 100.0f;
    in.animPlaying = true;
    return in;
}

static void finishLanding(P2FuefukiFsm& fsm)
{
    P2FuefukiFsmInput in = baseIn();
    in.keyEvent          = 2;
    fsm.tick(in);
    in.keyEvent = 3;
    fsm.tick(in);
    in.keyEvent = 4;
    P2FuefukiFsmOut out = fsm.tick(in);
    assert(out.transited && out.state == S::Wait);
}

static P2FuefukiFsmOut runUntilTransition(P2FuefukiFsm& fsm, P2FuefukiFsmInput in, int maxTicks)
{
    P2FuefukiFsmOut out;
    for (int i = 0; i < maxTicks; i++) {
        in.keyEvent = 0;
        out         = fsm.tick(in);
        if (out.transited) return out;
        if (out.requestFinishMotion) {
            in.keyEvent = 4;
            out         = fsm.tick(in);
            if (out.transited) return out;
        }
    }
    return out;
}

// Keep ticking (finishing requested motions) until a target state is reached.
static void driveToState(P2FuefukiFsm& fsm, P2FuefukiFsmInput in, S target, int maxTicks)
{
    in.keyEvent = 0;
    for (int i = 0; i < maxTicks && fsm.getState() != target; i++) {
        P2FuefukiFsmOut out = fsm.tick(in);
        if (out.requestFinishMotion && !out.transited) {
            in.keyEvent = 4;
            fsm.tick(in);
            in.keyEvent = 0;
        }
    }
    assert(fsm.getState() == target);
}

static void driveToWhisle(P2FuefukiFsm& fsm, P2FuefukiFsmInput in)
{
    for (int g = 0; g < 12 && fsm.getState() != S::Whisle; g++)
        runUntilTransition(fsm, in, 60);
    assert(fsm.getState() == S::Whisle);
}

static void claimOne(P2FuefukiFsm& fsm, std::uint32_t id, std::vector<std::uint32_t>& pings)
{
    P2FuefukiFsmInput in = baseIn();
    P2FuefukiCandidate c;
    c.id = id; c.living = c.callable = true;
    in.candidates.push_back(c);
    in.followerPings = { id };
    P2FuefukiFsmOut out;
    for (int i = 0; i < 10; i++) {
        out = fsm.tick(in);
        if (!out.claimed.empty()) break;
        in.candidates.clear();
    }
    assert(fsm.squad().holds(id));
    if (pings.empty() || pings.back() != id) pings.push_back(id);
}

// Unordered set-equality check (releaseAll iterates an unordered_map).
static bool releasedSetEq(const std::vector<std::uint32_t>& a,
                          const std::vector<std::uint32_t>& b)
{
    if (a.size() != b.size()) return false;
    std::vector<std::uint32_t> sa = a, sb = b;
    std::sort(sa.begin(), sa.end());
    std::sort(sb.begin(), sb.end());
    return sa == sb;
}

int main()
{
    // --- (1) Trace-grounded decision: suspend returns FREE, never Formation ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        fsm.spawn(table, 1);
        finishLanding(fsm);
        P2FuefukiFsmInput in = baseIn();
        driveToWhisle(fsm, in);
        std::vector<std::uint32_t> pings;
        claimOne(fsm, 10, pings);

        auto susp = fsm.squad().suspend(1);
        assert(susp.accepted);
        assert(susp.released.size() == 1 && susp.released[0] == 10);
        assert(susp.fallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        assert(!fsm.squad().holds(10));
        assert(!fsm.squad().reclaimPanic(10).accepted);
    }

    // --- (2) Suspend via FSM Stay entry (Jump -> Stay, flying case) ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        fsm.spawn(table, 1);
        finishLanding(fsm);
        P2FuefukiFsmInput in = baseIn();
        driveToWhisle(fsm, in);
        std::vector<std::uint32_t> pings;
        claimOne(fsm, 20, pings);
        // Jump away via the appear timer (may pass the cast-end Turn first)
        in.followerPings = { 20 };
        driveToState(fsm, in, S::Jump, 200);
        // escape burst, then END -> Stay releases through suspend
        P2FuefukiFsmInput jin = baseIn();
        jin.keyEvent          = 3;
        P2FuefukiFsmOut out   = fsm.tick(jin);
        assert(out.escapeVelocity);
        jin.keyEvent = 4;
        out          = fsm.tick(jin);
        assert(out.transited && out.state == S::Stay);
        assert(out.releasedSuspend.size() == 1 && out.releasedSuspend[0] == 20);
        assert(out.suspendFallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        assert(!fsm.squad().holds(20));
        assert(!fsm.squad().reclaimPanic(20).accepted); // not Panic: no whistle reclaim
    }

    // --- (3) Multiple claims: all released, set-equal, no reclaim ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiFsm fsm(testParms());
        fsm.spawn(table, 1);
        finishLanding(fsm);
        P2FuefukiFsmInput in = baseIn();
        driveToWhisle(fsm, in);
        P2FuefukiCandidate c30, c31, c32;
        c30.id = 30; c30.living = c30.callable = true;
        c31.id = 31; c31.living = c31.callable = true;
        c32.id = 32; c32.living = c32.callable = true;
        in.candidates.push_back(c30);
        in.candidates.push_back(c31);
        in.candidates.push_back(c32);
        P2FuefukiFsmOut out;
        for (int i = 0; i < 10; i++) {
            out = fsm.tick(in);
            if (out.claimed.size() == 3) break;
            in.candidates.clear();
        }
        assert(fsm.squad().holds(30) && fsm.squad().holds(31) && fsm.squad().holds(32));
        auto susp = fsm.squad().suspend(1);
        assert(susp.accepted);
        std::vector<std::uint32_t> expected = { 30, 31, 32 };
        assert(releasedSetEq(susp.released, expected));
        assert(susp.fallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        assert(!fsm.squad().holds(30) && !fsm.squad().holds(31) && !fsm.squad().holds(32));
        assert(!fsm.squad().reclaimPanic(30).accepted);
        assert(!fsm.squad().reclaimPanic(31).accepted);
        assert(!fsm.squad().reclaimPanic(32).accepted);
    }

    // --- (4) Wrong epoch is inert; no-claims suspend is an empty accept ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiInterferencePolicy beetle;
        assert(beetle.bind(&table, 1));
        auto wrong = beetle.suspend(2);
        assert(!wrong.accepted);
        assert(beetle.beginCast(1).accepted);
        auto empty = beetle.suspend(1);
        assert(empty.accepted && empty.released.empty());
        assert(empty.fallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        beetle.cancel(1);
    }

    // --- (5) Suspend then re-claim (owner returns) at the policy level ---
    {
        P2FuefukiOwnershipTable table;
        table.invalidateDomain();
        P2FuefukiInterferencePolicy beetle;
        assert(beetle.bind(&table, 1));
        beetle.beginCast(1);
        assert(beetle.admit(1, 50, true, true, false, false).accepted);
        beetle.ping(1, 50);
        auto susp = beetle.suspend(1);
        assert(susp.accepted && susp.released.size() == 1 && susp.released[0] == 50);
        assert(susp.fallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        // owner returns: cast and re-admit the same Pikmin
        assert(beetle.beginCast(1).accepted);
        assert(beetle.admit(1, 50, true, true, false, false).accepted);
        assert(beetle.holds(50));
        beetle.cancel(1);
    }

    // --- (6) Binding seam: suspend fallback propagated; followEnd SUSPEND ---
    {
        struct MockHost {
            std::vector<std::uint32_t> started;
            std::vector<std::pair<std::uint32_t, int>> ended;
        };
        MockHost mh;
        P2FuefukiBinding bind;

        P2FuefukiHost h = {};
        h.context        = &mh;
        h.probe = [](void*, P2FuefukiProbeResult& out) {
            out.valid = true; out.x = 0.0f; out.z = 0.0f;
            out.intruder = false; out.arriveTarget = false; out.water = false;
        };
        h.enumerate = [](void*, float, float, float radius,
                         P2FuefukiSquadEntry* out, int cap) -> int {
            if (radius <= 0.0f || cap < 1) return 0;
            P2FuefukiSquadEntry e = {};
            e.id = 60; e.living = e.callable = true;
            out[0] = e;
            return 1;
        };
        h.followStart = [](void* ctx, std::uint32_t id) -> bool {
            static_cast<MockHost*>(ctx)->started.push_back(id);
            return true;
        };
        h.followEnd = [](void* ctx, std::uint32_t id, int reason) {
            static_cast<MockHost*>(ctx)->ended.push_back({ id, reason });
        };
        h.pingCollect = [](void*, std::uint32_t*, int) -> int { return 0; };
        h.ownershipWrite = [](void*, std::uint32_t, std::uint32_t) {};
        h.kill = [](void*, bool) {};
        assert(bind.bind(h, testParms(), nullptr));
        bind.spawn(1);

        P2FuefukiBindTick t;
        t.delta = DT; t.health = 100.0f; t.animPlaying = true;
        // Land: feed KEYEVENT_2/3/END
        for (int i = 0; i < 4 && bind.getFsm().getState() == S::Land && i < 3; i++) {
            t.keyEvent = 2 + i;
            (void)bind.tick(t);
        }
        // Drive to Whisle
        for (int i = 0; i < 200 && bind.getFsm().getState() != S::Whisle; i++) {
            t.keyEvent = 0;
            P2FuefukiBindOut bo = bind.tick(t);
            if (bo.fsm.requestFinishMotion && !bo.transited) {
                t.keyEvent = 4;
                bind.tick(t);
                t.keyEvent = 0;
            }
        }
        assert(bind.getFsm().getState() == S::Whisle);
        // Claim Pikmin 60
        P2FuefukiBindOut bo = bind.tick(t);
        assert(bo.claimed == 1 && mh.started.size() == 1 && mh.started[0] == 60);
        // Drive to Jump; then Stay (suspend) through the binding seam
        for (int i = 0; i < 300 && bind.getFsm().getState() != S::Jump; i++) {
            t.keyEvent = 0;
            bo = bind.tick(t);
            if (bo.fsm.requestFinishMotion && !bo.transited) {
                t.keyEvent = 4;
                bind.tick(t);
                t.keyEvent = 0;
            }
        }
        assert(bind.getFsm().getState() == S::Jump);
        t.keyEvent = 3;
        bo         = bind.tick(t); // escape burst
        assert(bo.fsm.escapeVelocity);
        t.keyEvent = 4;
        bo         = bind.tick(t); // END -> Stay: suspend
        assert(bind.getFsm().getState() == S::Stay);
        assert(bo.endedSuspend == 1);
        assert(mh.ended.size() == 1 && mh.ended[0].first == 60
               && mh.ended[0].second == P2FUEFUKI_END_SUSPEND);
        assert(bo.suspendFallback == P2FUEFUKI_SUSPEND_FALLBACK_FREE);
        assert(!bind.onCaptainWhistle(60, 1)); // no reclaim after suspend
    }

    puts("p2_fuefuki_suspend_fallback_test PASS");
}