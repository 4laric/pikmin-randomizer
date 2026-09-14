// Seam fixture: the Fuefuki binding drives the ActTeki follow-locomotion
// policy through the optional host followerSample/followDrive callbacks
// (#245). Proves claim -> controller registration -> per-tick velocity
// command -> release, and that the locomotion seam stays off unless both
// callbacks are supplied. Engine-free.
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_follow_binding_test.cpp -o ../p2_fuefuki_follow_binding_test.exe
#include "pc_p2_fuefuki_binding.h"

#include <cassert>
#include <cstdio>
#include <map>
#include <tuple>
#include <utility>
#include <vector>

using S = P2FuefukiFsmState;
static constexpr float DT = 1.0f / 30.0f;

struct MockFollow {
    P2FuefukiProbeResult probe;
    std::vector<P2FuefukiSquadEntry> squad;
    std::vector<std::uint32_t> pings;
    std::map<std::uint32_t, std::pair<float, float>> positions;
    bool sampleOk = true;
    int sampleCalls = 0;
    // id, stop, speed, dirX, dirZ
    std::vector<std::tuple<std::uint32_t, bool, float, float, float>> drives;
};

static void probeFn(void* ctx, P2FuefukiProbeResult& out) { out = static_cast<MockFollow*>(ctx)->probe; }

static int enumFn(void* ctx, float, float, float radius, P2FuefukiSquadEntry* out, int cap)
{
    MockFollow* m = static_cast<MockFollow*>(ctx);
    if (radius <= 0.0f) return 0;
    int n = 0;
    for (const P2FuefukiSquadEntry& e : m->squad) {
        if (n >= cap) break;
        out[n++] = e;
    }
    return n;
}

static bool followStart(void*, std::uint32_t) { return true; }
static void followEnd(void*, std::uint32_t, int) { }

static int pingFn(void* ctx, std::uint32_t* out, int cap)
{
    MockFollow* m = static_cast<MockFollow*>(ctx);
    int n = 0;
    for (std::uint32_t id : m->pings) {
        if (n >= cap) break;
        out[n++] = id;
    }
    return n;
}

static void ownershipWrite(void*, std::uint32_t, std::uint32_t) { }
static void killFn(void*, bool) { }

static bool followerSample(void* ctx, std::uint32_t id, float& x, float& z)
{
    MockFollow* m = static_cast<MockFollow*>(ctx);
    m->sampleCalls++;
    if (!m->sampleOk) return false;
    auto it = m->positions.find(id);
    if (it == m->positions.end()) return false;
    x = it->second.first;
    z = it->second.second;
    return true;
}

static void followDrive(void* ctx, std::uint32_t id, const P2FuefukiFollowMove& move)
{
    static_cast<MockFollow*>(ctx)->drives.emplace_back(id, move.stop, move.speed, move.dirX, move.dirZ);
}

static P2FuefukiHost makeHost(MockFollow& m, bool withLocomotion)
{
    P2FuefukiHost h;
    h.context        = &m;
    h.probe          = probeFn;
    h.enumerate      = enumFn;
    h.followStart    = followStart;
    h.followEnd      = followEnd;
    h.pingCollect    = pingFn;
    h.ownershipWrite = ownershipWrite;
    h.kill           = killFn;
    if (withLocomotion) {
        h.followerSample = followerSample;
        h.followDrive    = followDrive;
    }
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
    p.attackRadius = 100.0f;
    p.castDuration = 1.2f;
    return p;
}

static P2FuefukiBindTick baseTick()
{
    P2FuefukiBindTick t;
    t.delta = DT;
    t.health = 100.0f;
    t.animPlaying = true;
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
    // Locomotion parms tuned for the fixture world: record every tick and
    // accept tiny beetle steps so a static probe still builds a trail.
    P2FuefukiFollowParms fp;
    fp.footmarkInterval = 0.0f;
    fp.footmarkSpacing  = 1.0f;
    fp.followDistance   = 100.0f;
    fp.nearSpeedMin     = 0.5f;
    fp.nearSpeedMax     = 1.0f;

    // --- seam active: claim registers a follower, ticks emit velocity ---
    {
        MockFollow m;
        m.probe.valid = true;
        m.probe.x = 0.0f;
        m.probe.z = 0.0f;
        P2FuefukiSquadEntry e;
        e.id = 7;
        e.living = e.callable = true;
        m.squad.push_back(e);
        m.positions[7] = { 60.0f, 0.0f }; // 60 units from the beetle

        P2FuefukiBinding b;
        assert(b.bind(makeHost(m, true), bindParms(), nullptr, fp));
        b.spawn(1);
        driveUntil(b, S::Whisle, 120);

        P2FuefukiBindTick t = baseTick();
        P2FuefukiBindOut out = b.tick(t); // scan + claim + first follow decision
        assert(out.claimed == 1);
        assert(out.followActive);
        assert(b.follow().holds(7));
        assert(out.followStops == 1 && out.followMoves == 0); // parent -> target
        assert(m.drives.size() == 1 && std::get<0>(m.drives[0]) == 7 && std::get<1>(m.drives[0]));

        m.pings = { 7 };
        out = b.tick(baseTick());
        assert(out.followMoves == 1 && out.followStops == 0);
        assert(m.drives.size() == 2);
        const auto& d = m.drives[1];
        assert(std::get<0>(d) == 7 && !std::get<1>(d));
        assert(std::get<2>(d) >= 0.5f && std::get<2>(d) <= 1.0f); // near speed
        assert(std::get<3>(d) < -0.9f);                           // toward x=0

        // Owner death releases the follower and stops locomotion.
        P2FuefukiBindTick dead = baseTick();
        dead.health = 0.0f;
        out = b.tick(dead);
        if (out.fsm.requestFinishMotion) {
            dead.keyEvent = 4;
            out = b.tick(dead);
        }
        assert(out.state == S::Dead);
        assert(!b.follow().holds(7));
        const std::size_t beforeDrives = m.drives.size();
        b.tick(baseTick());
        assert(m.drives.size() == beforeDrives); // no dead-follower command
    }

    // --- sample failure skips the follower without a command ---
    {
        MockFollow m;
        m.probe.valid = true;
        P2FuefukiSquadEntry e;
        e.id = 9;
        e.living = e.callable = true;
        m.squad.push_back(e);
        m.positions[9] = { 30.0f, 0.0f };
        P2FuefukiBinding b;
        assert(b.bind(makeHost(m, true), bindParms(), nullptr, fp));
        b.spawn(1);
        driveUntil(b, S::Whisle, 120);
        b.tick(baseTick()); // claim
        assert(b.follow().holds(9));
        m.sampleOk = false;
        P2FuefukiBindOut out = b.tick(baseTick());
        assert(out.followStops == 0 && out.followMoves == 0);
    }

    // --- locomotion seam stays off when either callback is missing ---
    {
        MockFollow m;
        m.probe.valid = true;
        P2FuefukiSquadEntry e;
        e.id = 11;
        e.living = e.callable = true;
        m.squad.push_back(e);
        P2FuefukiBinding b;
        assert(b.bind(makeHost(m, false), bindParms(), nullptr, fp));
        b.spawn(1);
        driveUntil(b, S::Whisle, 120);
        P2FuefukiBindOut out = b.tick(baseTick());
        assert(out.claimed == 1);
        assert(!out.followActive);
        assert(m.drives.empty());
    }

    std::printf("PASS p2_fuefuki_follow_binding_test\n");
    return 0;
}
