// Titan Dweevil weapon visuals and weapon selection (engine-free).
// pc_p2_bigtreasure_fx.h reads the element runtime and places P1-effect points;
// this test drives the real runtime for each weapon, so a change in node
// motion, ranges or chain links shows up here. It also records the laser
// (elec) selection finding from the owner playtest 2026-09-30: the weapon pick
// is health weighted with elec as band 0, so absence over a few attacks is
// chance, and the elec attack forms its chains inside the 5 s attack window.
#include "pc_p2_bigtreasure.h"
#include "pc_p2_bigtreasure_fx.h"

#include <cmath>
#include <cstdio>

using namespace p2titanfx;

namespace {
int gFail = 0;
#define CHECK(cond, name)                                                         \
    do {                                                                          \
        if (!(cond)) {                                                            \
            ++gFail;                                                              \
            std::printf("FAIL %s (%s:%d)\n", name, __FILE__, __LINE__);           \
        } else {                                                                  \
            std::printf("ok   %s\n", name);                                       \
        }                                                                         \
    } while (0)

constexpr float kDt = 1.0f / 30.0f;

bool mockTrace(void*, const P2BigTreasureVec3& position, const P2BigTreasureVec3& velocity, float, float, float,
               P2BigTreasureTraceResult& result) {
    result.position = P2BigTreasureVec3{position.x, 20.0f, position.z}; // floor at y=0 (sphere raised by 20)
    result.velocity = P2BigTreasureVec3{velocity.x, 0.0f, velocity.z};
    result.floor = true;
    result.wall = false;
    result.groundY = 0.0f;
    result.hasGroundY = true;
    return true;
}
bool mockGround(void*, float, float, float* outY) { *outY = 0.0f; return true; }

P2BigTreasureElementHost host() {
    P2BigTreasureElementHost h;
    h.trace = mockTrace;
    h.ground = mockGround;
    return h;
}

bool finite(const p2attackfx::Point& p) {
    return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z) && std::isfinite(p.scale);
}

struct Run {
    int maxPoints = 0, totalPoints = 0, firstPointTick = -1, arcPoints = 0, nodePoints = 0, tipPoints = 0, muzzle = 0;
    float maxReach = 0.0f;
    bool allFinite = true;
    int chained = 0;
};

// Runs `ticks` source ticks of `weapon` and lays out the visuals each tick.
Run run(int weapon, float hp, float pickA, float pickB, int ticks, bool useAim, P2BigTreasureElementRuntime& rt,
        State& st, const Legs& legs) {
    Run r;
    P2BigTreasureElementHost h = host();
    P2BigTreasureElementAim aim;
    if (useAim) {
        aim.set = true;
        aim.emit = {100.0f, 150.0f, 200.0f};
        aim.direction = {0.0f, 0.0f, 1.0f};
        aim.haveWaterTarget = true;
        aim.waterTarget = {100.0f, 0.0f, 500.0f};
        rt.setAim(aim);
    }
    rt.start(weapon, P2BigTreasureVec3{100.0f, 30.0f, 200.0f}, 0.0f, hp, pickA, pickB);
    const P2BigTreasureVec3 origin = useAim ? aim.emit : P2BigTreasureVec3{100.0f, 60.0f, 200.0f};
    for (int t = 0; t < ticks; ++t) {
        P2BigTreasureElementStats stats;
        rt.tick(kDt, h, stats);
        p2attackfx::Element e;
        p2attackfx::Point pts[MAX_POINTS];
        const int n = layout(rt, stats, legs, st, e, pts);
        if (n > r.maxPoints) r.maxPoints = n;
        r.totalPoints += n;
        if (n > 0 && r.firstPointTick < 0) r.firstPointTick = t;
        for (int i = 0; i < n; ++i) {
            r.allFinite &= finite(pts[i]);
            if (pts[i].kind == p2attackfx::Kind::Arc) ++r.arcPoints;
            if (pts[i].kind == p2attackfx::Kind::Node) ++r.nodePoints;
            if (pts[i].kind == p2attackfx::Kind::Tip) ++r.tipPoints;
            if (pts[i].kind == p2attackfx::Kind::Muzzle) ++r.muzzle;
            const float dx = pts[i].x - origin.x, dz = pts[i].z - origin.z;
            const float reach = std::sqrt(dx * dx + dz * dz);
            if (reach > r.maxReach) r.maxReach = reach;
        }
        r.chained = rt.elecPolicy().chainedCount();
    }
    return r;
}
} // namespace

int main() {
    const Legs noLegs;
    // Fire: a muzzle jet from the first tick, reach bounded by the source extent x scale.
    {
        P2BigTreasureElementRuntime rt;
        State st;
        const Run r = run(P2BTWEAPON_Fire, 6000.0f, 0.25f, 0.25f, 40, true, rt, st, noLegs);
        CHECK(r.firstPointTick == 0 && r.maxPoints >= 1 && r.allFinite, "fire shows from the first tick");
        CHECK(r.maxReach <= 200.0f * 1.0f + 1.0f, "fire reach never passes the source extent (200)");
        rt.finish();
        p2attackfx::Element e;
        p2attackfx::Point pts[MAX_POINTS];
        P2BigTreasureElementStats stats;
        CHECK(layout(rt, stats, noLegs, st, e, pts) == 0, "no fire points once the attack finished");
    }
    // Damaged fire uses the 1.25 scale on the point (parm ff10).
    {
        P2BigTreasureElementRuntime rt;
        State st;
        P2BigTreasureElementHost h = host();
        P2BigTreasureElementAim aim;
        aim.set = true; aim.emit = {0, 100, 0}; aim.direction = {0, 0, 1};
        rt.setAim(aim);
        rt.start(P2BTWEAPON_Fire, {0, 0, 0}, 0.0f, 2000.0f, 0.25f, 0.25f);
        P2BigTreasureElementStats stats;
        rt.tick(kDt, h, stats);
        p2attackfx::Element e;
        p2attackfx::Point pts[MAX_POINTS];
        const int n = layout(rt, stats, noLegs, st, e, pts);
        CHECK(n >= 1 && std::fabs(pts[0].scale - 1.25f) < 1e-5f, "damaged fire (hp <= 3000) draws at scale 1.25");
    }
    // Gas: 3 arms normal / 4 damaged; puffs inside 480 of the emit position.
    {
        P2BigTreasureElementRuntime rt;
        State st;
        const Run r = run(P2BTWEAPON_Gas, 6000.0f, 0.25f, 0.25f, 120, true, rt, st, noLegs);
        CHECK(r.totalPoints > 0 && r.allFinite, "gas emits puffs");
        CHECK(r.maxReach <= 480.0f + 1.0f, "gas puffs stay inside the arm extent (480)");
        CHECK(rt.gasArms() == 3, "normal gas has 3 arms");
        P2BigTreasureElementRuntime rt4;
        State st4;
        run(P2BTWEAPON_Gas, 1000.0f, 0.25f, 0.25f, 30, true, rt4, st4, noLegs);
        CHECK(rt4.gasArms() == 4, "damaged gas has 4 arms");
    }
    // Water: muzzle per shot, one body point per live bubble, a splash where each lands.
    {
        P2BigTreasureElementRuntime rt;
        State st;
        const Run r = run(P2BTWEAPON_Water, 6000.0f, 0.25f, 0.25f, 100, true, rt, st, noLegs);
        CHECK(r.muzzle > 0, "water emits a muzzle burst per shot");
        CHECK(r.totalPoints > r.muzzle && r.allFinite, "water draws the bubbles in flight");
        CHECK(r.tipPoints > 0, "water splashes where a bubble lands");
    }
    // Elec: arcs appear once chains link, and they link inside the 5 s attack window for every parameter set.
    {
        // pick01 < 0.5 -> set 1 (scatter 2.7 s) / set 3 (0.5 s); >= 0.5 -> set 2 (4.5 s) / set 4 (0.2 s).
        struct Case { float hp, pick; const char* name; };
        const Case cases[4] = {{6000.0f, 0.25f, "normal set 1 (scatter 2.7 s)"}, {6000.0f, 0.75f, "normal set 2 (scatter 4.5 s)"},
                               {2000.0f, 0.25f, "damaged set 3 (scatter 0.5 s)"}, {2000.0f, 0.75f, "damaged set 4 (scatter 0.2 s)"}};
        for (const Case& c : cases) {
            P2BigTreasureElementRuntime rt;
            State st;
            Legs legs;
            legs.set = true;
            for (int l = 0; l < 4; ++l) { legs.hip[l][1] = 100; legs.foot[l][0] = 50.0f * float(l); legs.foot[l][1] = 10; }
            const Run r = run(P2BTWEAPON_Elec, c.hp, 0.3f, c.pick, 150, true, rt, st, legs); // 5 s of source ticks
            char label[160];
            std::snprintf(label, sizeof(label), "elec %s: nodes drawn", c.name);
            CHECK(r.nodePoints > 0 && r.allFinite, label);
            std::snprintf(label, sizeof(label), "elec %s: chains link inside the 5 s attack window", c.name);
            CHECK(r.chained > 0, label);
            std::snprintf(label, sizeof(label), "elec %s: arcs are drawn", c.name);
            CHECK(r.arcPoints > 0, label);
        }
    }
    // Elec anchor glow only before the first chain (ElecAttack1 fades when chains start).
    {
        P2BigTreasureElementRuntime rt;
        State st;
        const Run early = run(P2BTWEAPON_Elec, 6000.0f, 0.3f, 0.25f, 10, true, rt, st, noLegs);
        CHECK(early.muzzle > 0, "elec anchor glow shows while the nodes scatter");
    }
    // Emission cadence keeps the generator pool bounded.
    {
        using p2attackfx::Element;
        CHECK(emitsOn(Element::Fire, 0) && emitsOn(Element::Fire, 1), "fire emits every tick");
        CHECK(emitsOn(Element::Water, 1), "water emits every tick");
        CHECK(emitsOn(Element::Gas, 0) && !emitsOn(Element::Gas, 1), "gas emits every other tick");
        CHECK(emitsOn(Element::Elec, 2) && !emitsOn(Element::Elec, 3), "elec emits every other tick");
    }
    // Elec scatter is seeded from the host inputs: distinct per attack, reproducible per input.
    {
        P2BigTreasureElementRuntime a, b, c;
        P2BigTreasureElementHost h = host();
        P2BigTreasureElementStats stats;
        a.start(P2BTWEAPON_Elec, {0, 0, 0}, 0.0f, 6000.0f, 0.31f, 0.25f);
        b.start(P2BTWEAPON_Elec, {0, 0, 0}, 0.0f, 6000.0f, 0.31f, 0.25f);
        c.start(P2BTWEAPON_Elec, {0, 0, 0}, 0.0f, 6000.0f, 0.77f, 0.25f);
        for (int i = 0; i < 20; ++i) { a.tick(kDt, h, stats); b.tick(kDt, h, stats); c.tick(kDt, h, stats); }
        bool same = true, differs = false;
        for (int i = 1; i < P2BigTreasureElecPolicy::kCapacity; ++i) {
            same &= a.elecPolicy().node(i).velocity.x == b.elecPolicy().node(i).velocity.x
                 && a.elecPolicy().node(i).velocity.z == b.elecPolicy().node(i).velocity.z;
            differs |= a.elecPolicy().node(i).velocity.x != c.elecPolicy().node(i).velocity.x;
        }
        CHECK(same, "same host inputs reproduce the same elec scatter");
        CHECK(differs, "different host inputs scatter the nodes differently (source rand jitter)");
    }
    // Laser selection finding. setTreasureAttack (BigTreasure.cpp:984-1035): weight
    // 12000 - hp per live weapon, bands in elec/fire/gas/water order.
    {
        P2BigTreasureOwnership own;
        for (int w = 0; w < 4; ++w) own.attachWeapon(w);
        const float total = 4.0f * (P2BigTreasureOwnership::kPickWeightBase - P2BigTreasureOwnership::kWeaponMaxHealth);
        int counts[4] = {};
        const int steps = 40000;
        for (int i = 0; i < steps; ++i) {
            const int w = own.pickWeapon(total * (float(i) + 0.5f) / float(steps));
            if (w >= 0) ++counts[w];
        }
        const float elecShare = float(counts[P2BTWEAPON_Elec]) / float(steps);
        CHECK(std::fabs(elecShare - 0.25f) < 0.001f, "at full health elec is exactly 1 of 4 attacks");
        const float noElecIn6 = std::pow(1.0f - elecShare, 6.0f);
        std::printf("info P(no elec in 6 picks) = %.3f\n", noElecIn6);
        CHECK(noElecIn6 > 0.15f && noElecIn6 < 0.20f, "6 picks without elec happens about 18% of the time (chance)");
        // Lower weapon health raises its band (more likely), and a dropped weapon is never picked.
        P2BigTreasureDropEvent drops[4];
        P2BigTreasureOwnership own2;
        for (int w = 0; w < 4; ++w) own2.attachWeapon(w);
        own2.addWeaponDamage(P2BTWEAPON_Elec, 4000.0f, false);
        own2.update(drops, 4);
        int c2[4] = {};
        float total2 = 0.0f;
        for (int w = 0; w < 4; ++w)
            if (own2.isWeaponAttached(w)) total2 += P2BigTreasureOwnership::kPickWeightBase - own2.weaponHealth(w);
        for (int i = 0; i < steps; ++i) {
            const int w = own2.pickWeapon(total2 * (float(i) + 0.5f) / float(steps));
            if (w >= 0) ++c2[w];
        }
        CHECK(c2[P2BTWEAPON_Elec] > counts[P2BTWEAPON_Elec], "a damaged weapon is picked more often");
    }
    if (gFail) { std::printf("%d failure(s)\n", gFail); return 1; }
    std::puts("p2_bigtreasure_fx_test: ok");
    return 0;
}
