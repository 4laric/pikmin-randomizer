// Shared P2 attack-effect layouts and lifecycle (engine-free): pc_p2_attack_fx.h.
// Each scenario names the defect it guards (the mutant it kills).
#include "pc_p2_attack_fx.h"

#include <cmath>
#include <cstdio>

using namespace p2attackfx;

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

float dist2(const Point& p, float ox, float oz) { return std::sqrt((p.x - ox) * (p.x - ox) + (p.z - oz) * (p.z - oz)); }
} // namespace

int main() {
    Point a[MAX_STREAM_POINTS], b[MAX_STREAM_POINTS];

    // Water preset == the Watery Blowhog stream of PR #51 (mutant: generalising
    // changed the tank look). Muzzle + 6 drops + tip, sag below the origin.
    {
        const int n = layoutStream(Element::Water, 10, 6, 20, 1, 0, 100.0f, 0, 1.0f, a);
        CHECK(n == 8, "water layout is muzzle + 6 drops + tip");
        CHECK(a[0].kind == Kind::Muzzle && a[n - 1].kind == Kind::Tip, "water muzzle first, tip last");
        CHECK(std::fabs(a[n - 1].x - 110.0f) < 1e-3f, "water tip lands at the range");
        bool reach = true, sag = true;
        for (int i = 1; i < n; ++i) { reach &= a[i].x - 10 <= 100.0f + 1e-3f; sag &= a[i].y <= 6.0f + 1e-4f; }
        CHECK(reach && sag, "water never overshoots the range and only sags");
        CHECK(layoutStream(Element::Water, 0, 0, 0, 0, 1, 5.0f, 0, 1.0f, a) == 0, "no points before the stream leaves the nozzle");
    }
    // Fire: one authored jet from the muzzle, scaled (mutant: fire scale ignored).
    {
        const int n1 = layoutStream(Element::Fire, 0, 50, 0, 0, 1, 200.0f, 0, 1.0f, a);
        const int n2 = layoutStream(Element::Fire, 0, 50, 0, 0, 1, 250.0f, 0, 1.25f, b);
        CHECK(n1 == 1 && a[0].kind == Kind::Muzzle, "fire is a single muzzle jet");
        CHECK(n2 == 1 && std::fabs(b[0].scale - 1.25f) < 1e-6f, "damaged fire scale 1.25 reaches the point");
        CHECK(look(Element::Fire, Kind::Muzzle).effect == EFF_Tank_Fire && !look(Element::Fire, Kind::Muzzle).burst,
              "fire uses P1 EFF_Tank_Fire with its authored emission");
    }
    // Gas: puffs march out along the arm and never pass the range; widen with distance.
    {
        const int n = layoutStream(Element::Gas, 0, 0, 0, 0, 1, 480.0f, 0, 1.0f, a);
        CHECK(n >= 2, "gas emits puffs along an arm");
        bool inRange = true, widen = true;
        float prev = 0.0f;
        for (int i = 0; i < n; ++i) {
            inRange &= dist2(a[i], 0, 0) <= 480.0f + 1e-3f;
            if (a[i].kind == Kind::Body) { widen &= a[i].scale >= prev; prev = a[i].scale; }
        }
        CHECK(inRange && widen, "gas puffs stay inside the arm and widen outward");
        CHECK(look(Element::Gas, Kind::Body).effect == EFF_Kinoko_AttackCloud, "gas uses the P1 Puffstool cloud");
    }
    // Determinism and tick phasing (mutant: random layout per call).
    {
        layoutStream(Element::Water, 10, 6, 20, 1, 0, 100.0f, 0, 1.0f, a);
        layoutStream(Element::Water, 10, 6, 20, 1, 0, 100.0f, 0, 1.0f, b);
        bool same = true;
        for (int i = 0; i < 8; ++i) same &= a[i].x == b[i].x && a[i].y == b[i].y && a[i].z == b[i].z;
        CHECK(same, "same inputs give the same layout");
        layoutStream(Element::Water, 10, 6, 20, 1, 0, 100.0f, 1, 1.0f, b);
        CHECK(b[1].x > a[1].x, "odd ticks interleave half a slot");
    }
    // Electric arc: endpoints pinned on the two nodes, interior jittered, deterministic, changes per tick.
    {
        Point arc[MAX_ARC_POINTS], arc2[MAX_ARC_POINTS];
        const int n = layoutArc(0, 20, 0, 100, 20, 0, 3, 1, 10.0f, arc);
        CHECK(n == MAX_ARC_POINTS, "arc has the full point count");
        CHECK(arc[0].x == 0 && arc[n - 1].x == 100 && arc[0].z == 0 && arc[n - 1].z == 0, "arc endpoints sit on the nodes");
        bool jitter = false, bound = true;
        for (int i = 1; i < n - 1; ++i) { jitter |= std::fabs(arc[i].z) > 0.01f; bound &= std::fabs(arc[i].z) <= 10.0f + 1e-3f; }
        CHECK(jitter && bound, "arc interior zigzags within the jitter bound");
        layoutArc(0, 20, 0, 100, 20, 0, 3, 1, 10.0f, arc2);
        bool same = true;
        for (int i = 0; i < n; ++i) same &= arc[i].z == arc2[i].z;
        CHECK(same, "arc is deterministic for a tick");
        layoutArc(0, 20, 0, 100, 20, 0, 4, 1, 10.0f, arc2);
        bool differs = false;
        for (int i = 1; i < n - 1; ++i) differs |= arc[i].z != arc2[i].z;
        CHECK(differs, "arc crackles frame to frame");
        CHECK(layoutArc(5, 0, 5, 5, 0, 5, 0, 0, 10.0f, arc) == 0, "zero-length arc emits nothing");
        CHECK(look(Element::Elec, Kind::Arc).effect == EFF_Rocket_Biri, "elec uses the P1 electric spark");
    }
    // Lifecycle: begin once, count, end once, nothing outstanding (mutant: effects outlive the attack).
    {
        Session s;
        CHECK(!s.end(), "ending an idle session is a no-op");
        CHECK(s.begin(Element::Gas), "first begin starts");
        CHECK(!s.begin(Element::Gas), "a repeated begin of the same element does not restart");
        s.note(12, 12);
        s.note(12, 11);
        CHECK(s.ticks == 2 && s.points == 24 && s.generators == 23, "session counts ticks, points and generators");
        CHECK(s.outstanding() == 1, "a running session is outstanding");
        CHECK(s.end(), "end returns true for an active session");
        CHECK(s.outstanding() == 0 && !s.active, "nothing outstanding after end");
        CHECK(!s.end(), "a second end is a no-op");
        CHECK(s.begin(Element::Elec) && s.ticks == 0, "a new session starts from zero counters");
    }
    // Every element has a real look for every kind it emits (mutant: missing effect id = silent no-op).
    {
        bool ok = true;
        const Element els[5] = {Element::Fire, Element::Water, Element::Gas, Element::Elec, Element::WaterBall};
        const Kind kinds[5] = {Kind::Muzzle, Kind::Body, Kind::Tip, Kind::Node, Kind::Arc};
        for (Element e : els)
            for (Kind k : kinds) {
                const Look l = look(e, k);
                ok &= l.effect > 0 && (!l.burst || l.life > 0);
            }
        CHECK(ok, "every element/kind maps to a P1 effect with a lifetime when bursting");
    }
    // Monster Pump water looks: every candidate has a ball, a burst and a shot piece with a positive
    // scale and lifetime; the default is a valid index; ring may be absent (scale 0 = skipped).
    {
        bool ok = DEFAULT_WATER_LOOK >= 0 && DEFAULT_WATER_LOOK < WATER_LOOKS;
        for (int v = 0; v < WATER_LOOKS; ++v) {
            const WaterLook& w = waterLook(v);
            ok &= w.name && w.shot.effect > 0 && w.ball.effect > 0 && w.splash.effect > 0;
            ok &= w.ball.every > 0 && w.ball.scale > 0 && w.splash.scale > 0 && w.shot.scale > 0;
        }
        CHECK(ok, "every water look has shot, ball and splash pieces (trail and ring optional)");
        waterVariant() = 1;
        const Look ball = look(Element::WaterBall, Kind::Body), ring = look(Element::WaterBall, Kind::Ring);
        CHECK(ball.effect == waterLook(1).ball.effect && ring.effect == waterLook(1).ring.effect, "WaterBall looks follow the selected variant");
        waterVariant() = 0;
        CHECK(look(Element::WaterBall, Kind::Ring).scale == 0.0f, "a look without a ring draws no ring");
        waterVariant() = DEFAULT_WATER_LOOK;
        CHECK(look(Element::Water, Kind::Body).effect == EFF_Frog_Water2, "the Tank stream look is unchanged by the Titan water looks");
    }
    if (gFail) { std::printf("%d failure(s)\n", gFail); return 1; }
    std::puts("p2_attack_fx_test: ok");
    return 0;
}
