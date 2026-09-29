// #892 engine-free regressions for the Groink shell visuals
// (pc_port/pc_p2_groink_fx.h): source effect timing from
// MiniHoudaiShotGun.cpp startShotGun/update/emitShotGun, driven through the
// real P2GroinkVolley and, end to end, the real source FSM.
#include "pc_p2_groink_fsm.h"
#include "pc_p2_groink_fx.h"
#include <cmath>
#include <cstdio>
#include <vector>

using namespace p2groinkfsm;

namespace {
int failures = 0;
void check(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); ++failures; }
}
bool near(float a, float b, float eps = 1e-3f) { return std::fabs(a - b) <= eps; }

float groundY = 0.0f;
// Flat floor at groundY: integrate, report a floor hit when the sphere touches it.
bool floorTrace(void*, const P2GroinkVec3& c, const P2GroinkVec3& v, float dt, float r, P2GroinkTraceResult& out) {
    out = {};
    out.position = {c.x + v.x * dt, c.y + v.y * dt, c.z + v.z * dt};
    out.velocity = v;
    if (out.position.y - r <= groundY) {
        out.position.y = groundY + r;
        out.floor = true;
        out.hasGroundY = true;
        out.groundY = groundY;
    }
    return true;
}
bool noWater(void*, const P2GroinkVec3&) { return false; }
bool allWater(void*, const P2GroinkVec3&) { return true; }

P2GroinkMuzzle muzzle(P2GroinkVec3 at, P2GroinkVec3 axis) {
    P2GroinkMuzzle m;
    m.column0 = axis;
    m.column1 = {0.0f, 1.0f, 0.0f};
    m.column2 = {0.0f, 0.0f, 1.0f};
    m.column3 = at;
    return m;
}

int count(const std::vector<P2GroinkFxCommand>& v, P2GroinkFxKind k) {
    int n = 0;
    for (const auto& c : v) n += c.kind == k;
    return n;
}

struct Run {
    int shoots = 0, trails = 0, hits = 0, water = 0, ticks = 0;
    std::vector<P2GroinkVec3> hitPos;
};

// Emits one volley, then updates until every shell ended, feeding each tick
// to the effect policy the way the host does.
Run fly(P2GroinkShellFx& fx, P2GroinkVolley& vol, const P2GroinkMuzzle& m, float speed, P2GroinkWaterFn water) {
    Run r;
    const std::array<P2GroinkVec3, P2GroinkVolley::kVolleySize> samples{
        P2GroinkVec3{0.5f, 0.5f, 0.5f}, P2GroinkVec3{0.2f, 0.5f, 0.8f}, P2GroinkVec3{0.8f, 0.5f, 0.2f}};
    for (int i = 0; i < 400; ++i) {
        P2GroinkFxTick t;
        if (i == 0) {
            const auto e = vol.emit(m, speed, samples);
            check(e.valid && e.count == 3, "volley emits three shells");
            t.volley = true;
            t.volleyMuzzle = m;
        }
        const bool any = vol.activeCount() > 0;
        if (any) vol.update({0.0f, 0.0f, 0.0f}, P2GroinkPolicy::kSourceDelta, floorTrace, nullptr);
        t.terminals = any ? int(vol.terminalCount()) : 0;
        t.shells = &vol;
        const auto cmds = fx.onTick(t, water, nullptr);
        r.shoots += count(cmds, P2GroinkFxKind::Shoot);
        r.trails += count(cmds, P2GroinkFxKind::Trail);
        r.hits += count(cmds, P2GroinkFxKind::Hit);
        r.water += count(cmds, P2GroinkFxKind::WaterHit);
        for (const auto& c : cmds)
            if (c.kind == P2GroinkFxKind::Hit || c.kind == P2GroinkFxKind::WaterHit) r.hitPos.push_back(c.pos);
        ++r.ticks;
        if (!any && i > 0) break;
    }
    return r;
}
} // namespace

int main() {
    // ---- TChibiShoot: once per emitShotGun, at the muzzle, along column 0.
    {
        P2GroinkShellFx fx;
        P2GroinkVolley vol;
        P2GroinkFxTick t;
        t.volley = true;
        t.volleyMuzzle = muzzle({1.0f, 50.0f, 2.0f}, {0.0f, 0.0f, 4.0f});
        const auto cmds = fx.onTick(t, noWater, nullptr);
        check(cmds.size() == 1 && cmds[0].kind == P2GroinkFxKind::Shoot, "a volley tick without shells is one Shoot");
        if (cmds.empty()) return 1;
        check(near(cmds[0].pos.x, 1.0f) && near(cmds[0].pos.y, 50.0f) && near(cmds[0].pos.z, 2.0f), "Shoot at kuti column 3");
        check(near(cmds[0].dir.z, 1.0f) && near(cmds[0].dir.x, 0.0f), "Shoot along the normalised column 0");
        P2GroinkFxTick d;
        d.deadBomb = true;
        d.deadMuzzle = muzzle({5.0f, 6.0f, 7.0f}, {1.0f, 0.0f, 0.0f});
        const auto dc = fx.onTick(d, noWater, nullptr);
        check(dc.size() == 1 && dc[0].kind == P2GroinkFxKind::Shoot && near(dc[0].pos.x, 5.0f),
              "Dead KEYEVENT_2 emits TChibiShoot on kuti (createDeadBombEmitEffect)");
        check(fx.onTick(P2GroinkFxTick{}, noWater, nullptr).empty(), "an idle tick emits nothing");
    }

    // ---- A volley that lands: shell trail while live, one hit per landing
    // shell at the source effectPos (raised to ground+10, then -10 y).
    {
        groundY = 0.0f;
        P2GroinkShellFx fx;
        P2GroinkVolley vol;
        const Run r = fly(fx, vol, muzzle({0.0f, 60.0f, 0.0f}, {0.0f, 0.0f, 1.0f}), 200.0f, noWater);
        check(r.shoots == 1, "one TChibiShoot per volley");
        check(r.hits == 3 && r.water == 0, "every floor landing shows exactly one hit effect");
        bool atGround = r.hitPos.size() == 3;
        for (const auto& p : r.hitPos) atGround = atGround && near(p.y, 0.0f);
        check(atGround, "hit effect at ground+10-10 (the source effectPos)");
        // Live for (ticks - 1) updates; first sight puffs, then every kTrailInterval.
        const int live = r.ticks - 1;
        check(r.trails >= 3 && r.trails <= 3 * (1 + live / P2GroinkShellFx::kTrailInterval),
              "trail puffs at creation, then every kTrailInterval ticks");
        check(r.trails > 3, "a shell in flight keeps showing (more than the creation puff)");
        for (std::size_t s = 0; s < P2GroinkVolley::kCapacity; ++s) check(!fx.live(s), "landed shells stop trailing");
    }

    // ---- Water landing -> THdamaHit3 stand-in, never also the ground blast.
    {
        groundY = 0.0f;
        P2GroinkShellFx fx;
        P2GroinkVolley vol;
        const Run r = fly(fx, vol, muzzle({0.0f, 60.0f, 0.0f}, {0.0f, 0.0f, 1.0f}), 200.0f, allWater);
        check(r.water == 3 && r.hits == 0, "a water landing is a splash, not a blast");
    }

    // ---- Out of range (>1000 from the owner): the shell fades, no hit effect.
    {
        groundY = -100000.0f;
        P2GroinkShellFx fx;
        P2GroinkVolley vol;
        const Run r = fly(fx, vol, muzzle({0.0f, 60.0f, 0.0f}, {0.0f, 0.0f, 1.0f}), 3000.0f, noWater);
        check(r.hits == 0 && r.water == 0, "an out-of-range shell ends with no hit effect");
        check(r.trails >= 3, "it still trails while live");
        for (std::size_t s = 0; s < P2GroinkVolley::kCapacity; ++s) check(!fx.live(s), "faded shells stop trailing");
        groundY = 0.0f;
    }

    // ---- Stale terminals: the volley keeps last update's receipts until its
    // next update, so a tick without an update must not replay the hits.
    {
        groundY = 0.0f;
        P2GroinkShellFx fx;
        P2GroinkVolley vol;
        fly(fx, vol, muzzle({0.0f, 60.0f, 0.0f}, {0.0f, 0.0f, 1.0f}), 200.0f, noWater);
        check(vol.terminalCount() > 0, "precondition: receipts still stored");
        P2GroinkFxTick t;
        t.terminals = 0;
        t.shells = &vol;
        check(fx.onTick(t, noWater, nullptr).empty(), "stored receipts are not replayed as new hits");
    }

    // ---- End to end: the real FSM against a Pikmin lane. Every volley tick
    // yields one Shoot at the reported muzzle, every floor terminal one hit.
    {
        const Bank bank = defaultBank();
        const Params params;
        Fsm f;
        P2GroinkVec3 pos{};
        f.init(params, bank, false, pos, 0.0f, 11u, nullptr);
        std::vector<Candidate> c;
        auto piki = [](std::uint64_t id, P2GroinkVec3 p) { Candidate k; k.id = id; k.pos = p; k.pikmin = true; return k; };
        c.push_back(piki(9, {0.0f, 0.0f, 190.0f}));
        for (int k = 0; k < 8; ++k) c.push_back(piki(100 + k, {0.0f, 0.0f, 60.0f + 15.0f * k}));
        P2GroinkShellFx fx;
        int volleys = 0, shoots = 0, floorEnds = 0, hits = 0, trails = 0;
        for (int i = 0; i < 600; ++i) {
            TickInput in;
            in.position = pos;
            in.health = 100.0f;
            in.candidates = c.data();
            in.count = c.size();
            in.trace = floorTrace;
            const TickOutput o = f.tick(in);
            pos.x += o.velocity.x * kSourceDelta;
            pos.z += o.velocity.z * kSourceDelta;
            P2GroinkFxTick t;
            t.volley = o.shotFired;
            t.volleyMuzzle = o.volleyMuzzle;
            t.deadBomb = o.deadBomb;
            t.deadMuzzle = o.deadMuzzle;
            t.terminals = o.terminals;
            t.shells = &f.shells();
            const auto cmds = fx.onTick(t, noWater, nullptr);
            volleys += o.volley ? 1 : 0;
            shoots += count(cmds, P2GroinkFxKind::Shoot);
            hits += count(cmds, P2GroinkFxKind::Hit);
            trails += count(cmds, P2GroinkFxKind::Trail);
            for (int k = 0; k < o.terminals; ++k) {
                const auto& term = f.shells().terminals()[std::size_t(k)];
                floorEnds += term.step.valid && (term.step.reason == P2GroinkTerminalReason::Floor
                                                 || term.step.reason == P2GroinkTerminalReason::Wall);
            }
        }
        check(volleys >= 2, "precondition: the FSM fires volleys");
        check(shoots == volleys, "one muzzle flash per FSM volley");
        check(floorEnds >= 3 && hits == floorEnds, "one hit effect per floor/wall shell landing");
        check(trails >= 3 * volleys, "every FSM shell shows in flight");
    }

    if (failures) {
        std::fprintf(stderr, "p2_groink_fx_test: %d failure(s)\n", failures);
        return 1;
    }
    std::puts("p2_groink_fx_test: ok");
    return 0;
}
