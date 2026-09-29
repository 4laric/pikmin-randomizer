// Fiery/Watery Blowhog breath exposure regression (issue #884). Engine-free:
// drives the same pc_p2_tank_breath.h decision path the runtime uses, with
// fake actors whose receiver mirrors InteractFire/InteractBubble immunity
// (p2_species_immune). Source: Tank.cpp:266-368, TankState.cpp:862-900.
#include "pc_p2_tank_breath.h"
#include "pc_p2_species_policy.h"
#include "pc_p2_tank_policy.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <random>
#include <set>
#include <vector>

namespace {
using namespace p2tankbreath;
int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)
#define CHECK_EQ(a, b) do { const long long va_ = (long long)(a), vb_ = (long long)(b); if (va_ != vb_) { std::fprintf(stderr, "%s:%d: CHECK_EQ failed: %s == %s (%lld != %lld)\n", __FILE__, __LINE__, #a, #b, va_, vb_); ++failures; } } while (0)
#define CHECK_NEAR(a, b, eps) do { const double va_ = (a), vb_ = (b); if (!(std::fabs(va_ - vb_) <= (eps))) { std::fprintf(stderr, "%s:%d: CHECK_NEAR failed: %s ~ %s (%.6f vs %.6f)\n", __FILE__, __LINE__, #a, #b, va_, vb_); ++failures; } } while (0)

struct Fake { int id; float x, y, z; bool alive; int species; int offered = 0; int stimulated = 0; };
struct FakeNavi { int id; float x, y, z; bool alive; };

auto pos = [](auto* a, float& x, float& y, float& z) { x = a->x; y = a->y; z = a->z; };
auto alive = [](auto* a) { return a->alive; };

// Receiver stand-in: rejects immune species exactly as the P1/P2 receivers do.
auto receiver(int kind) {
    const int hazard = kind ? P2HazardWater : P2HazardFire;
    return [hazard](Fake* a) {
        ++a->offered;
        if (p2_species_immune(a->species, hazard)) return false;
        ++a->stimulated;
        return true;
    };
}

// Full-range Tank at origin facing +Z. Emitter (0, 6.3969, 35.8169); the box is
// z in (35.82, 155.82), |x| < 25, |y - 6.40| < 25.
Frame full(float heading = 0.0f) { return frame(0, 0, 0, heading, p2tank::params(0).attackRange, p2tank::params(0).attackRadius); }
constexpr float IN_Z = 100.0f;

std::vector<Fake> line(int n, int species, int firstId, float x0 = -20.0f) {
    std::vector<Fake> v;
    for (int i = 0; i < n; ++i) v.push_back(Fake{firstId + i, x0 + 2.0f * float(i), 0.0f, IN_Z + float(i), true, species});
    return v;
}
std::vector<Fake*> ptrs(std::vector<Fake>& v) { std::vector<Fake*> p; for (auto& a : v) p.push_back(&a); return p; }

int breath(int kind, std::vector<Fake*>& population, std::vector<Fake*>* exposedOut = nullptr) {
    std::vector<Fake*> snap;
    collect(full(), population, pos, alive, snap);
    if (exposedOut) *exposedOut = snap;
    return dispatch(snap, alive, receiver(kind));
}

void caseMoreThanSix() {
    auto blues = line(20, P2SpeciesBlue, 0);
    auto pop = ptrs(blues);
    std::vector<Fake*> snap;
    CHECK_EQ(breath(0, pop, &snap), 20);
    CHECK_EQ(snap.size(), 20);
    for (auto& b : blues) CHECK_EQ(b.stimulated, 1);
}

void caseImmuneCannotShield(int kind, int immune, int vulnerable) {
    std::vector<Fake> actors = line(6, immune, 0);
    auto rest = line(10, vulnerable, 100, -10.0f);
    actors.insert(actors.end(), rest.begin(), rest.end());
    auto pop = ptrs(actors);
    CHECK_EQ(breath(kind, pop), 10);
    for (int i = 0; i < 6; ++i) { CHECK_EQ(actors[i].offered, 1); CHECK_EQ(actors[i].stimulated, 0); }
    for (int i = 6; i < 16; ++i) CHECK_EQ(actors[i].stimulated, 1);
}

void caseOrderIndependence() {
    std::mt19937 rng(884);
    std::uniform_real_distribution<float> xs(-40.0f, 40.0f), zs(0.0f, 170.0f), ys(-15.0f, 25.0f);
    std::vector<Fake> actors;
    for (int i = 0; i < 30; ++i) actors.push_back(Fake{i, xs(rng), ys(rng), zs(rng), (i % 11) != 5, i % 6});
    auto base = ptrs(actors);
    auto run = [&](std::vector<Fake*> pop, std::set<int>& ids) {
        std::vector<Fake*> snap;
        collect(full(), pop, pos, alive, snap);
        for (auto* a : snap) ids.insert(a->id);
        return dispatch(snap, alive, [](Fake* a) { return !p2_species_immune(a->species, P2HazardFire); });
    };
    std::set<int> ref;
    const int refAccepted = run(base, ref);
    CHECK(ref.size() > 6);           // population is large enough to hit the old cap
    CHECK(ref.size() < actors.size()); // and some actors are outside the box
    std::vector<std::vector<Fake*>> orders{base, std::vector<Fake*>(base.rbegin(), base.rend())};
    for (int i = 0; i < 20; ++i) { auto o = base; std::shuffle(o.begin(), o.end(), rng); orders.push_back(o); }
    for (auto& o : orders) {
        std::set<int> ids;
        CHECK_EQ(run(o, ids), refAccepted);
        CHECK(ids == ref);
    }
}

void caseGeometry() {
    const Frame f = full();
    CHECK(exposed(f, 0, 0, 100));
    CHECK(exposed(f, 24, 0, 100));
    CHECK(!exposed(f, 30, 0, 100));
    CHECK(!exposed(f, 0, 0, 20));   // behind the emitter
    CHECK(!exposed(f, 0, 0, -10));  // behind the Blowhog (old 360-degree inner disc)
    CHECK(!exposed(f, 0, 0, 35.8f)); // at the emitter, fwd <= 0
    CHECK(!exposed(f, 0, 0, 156));  // fwd >= range
    CHECK(!exposed(f, 0, 40, 100)); // |dy| >= radius
    CHECK(!exposed(f, 50, 0, 100)); // inside the old +-0.6 rad cone, outside the source box
    const Frame side = full(3.14159265f / 2.0f);
    CHECK(exposed(side, 100, 0, 0));
    CHECK(!exposed(side, 0, 0, 100));
}

void caseRangeGrowth() {
    Emit e;
    const float dt = 1.0f / 30.0f, maxRange = p2tank::params(0).attackRange;
    const float fwd100z = EMIT_FORWARD + 100.0f;
    bool sawHidden = false, sawExposed = false;
    float prev = -1.0f;
    for (int n = 1; n <= 40; ++n) {
        const float r = advance(e, maxRange, dt);
        if (n == 1) {
            CHECK(r == 0.0f);
            CHECK(!exposed(frame(0, 0, 0, 0, r, 25), 0, 0, EMIT_FORWARD + 1.0f));
        } else {
            const double expect = maxRange * std::min(1.0, 0.001 + (n - 1) / 15.0);
            CHECK_NEAR(r, expect, 1e-3);
            if (n < 16) CHECK(r > prev && r < maxRange);
        }
        if (n >= 16) CHECK(r == maxRange);
        const bool ex = exposed(frame(0, 0, 0, 0, r, 25), 0, 0, fwd100z);
        CHECK(ex == (r > 100.0f));
        if (ex) sawExposed = true; else if (!sawExposed) sawHidden = true;
        prev = r;
    }
    CHECK(sawHidden && sawExposed);
}

void caseTiming() {
    CHECK_NEAR(keyEventSeconds(), 55.0 / 30.0, 1e-6);
    CHECK(keyEventSeconds() < ATTACK_CLIP_FRAMES / ANIM_FPS);
    // Ordering driver mirroring TNK_ATTACK: discharge if latched, then latch.
    const float dt = 1.0f / 30.0f;
    float t = 0.0f;
    bool discharging = false;
    int armFrame = -1, firstDispatch = -1, dispatchesBeforeKey = 0;
    for (int frameNo = 1; frameNo <= ATTACK_CLIP_FRAMES; ++frameNo) {
        t += dt;
        if (discharging) { if (firstDispatch < 0) firstDispatch = frameNo; if (t < keyEventSeconds()) ++dispatchesBeforeKey; }
        if (!discharging && t >= keyEventSeconds()) { discharging = true; armFrame = frameNo; }
    }
    CHECK_EQ(dispatchesBeforeKey, 0);
    CHECK(armFrame == 55 || armFrame == 56);
    CHECK_EQ(firstDispatch, armFrame + 1);
}

void caseRemovalDuringDispatch() {
    std::vector<Fake> store = line(4, P2SpeciesYellow, 0);
    Fake extra{99, 0, 0, IN_Z, true, P2SpeciesYellow};
    std::vector<Fake*> pop = ptrs(store);
    Fake *a = pop[0], *b = pop[1], *c = pop[2], *d = pop[3];
    std::vector<Fake*> snap;
    collect(full(), pop, pos, alive, snap);
    CHECK_EQ(snap.size(), 4);
    auto base = receiver(0);
    const int accepted = dispatch(snap, alive, [&](Fake* x) {
        const bool ok = base(x);
        if (x == a) { b->alive = false; pop.push_back(&extra); }
        return ok;
    });
    CHECK_EQ(accepted, 3);
    CHECK_EQ(b->offered, 0);
    CHECK_EQ(c->stimulated, 1);
    CHECK_EQ(d->stimulated, 1);
    CHECK_EQ(extra.offered, 0);
    CHECK(std::find(snap.begin(), snap.end(), &extra) == snap.end());

    // Killing an already-processed actor changes nothing.
    std::vector<Fake> store2 = line(4, P2SpeciesYellow, 10);
    auto pop2 = ptrs(store2);
    std::vector<Fake*> snap2;
    collect(full(), pop2, pos, alive, snap2);
    const int accepted2 = dispatch(snap2, alive, [&](Fake* x) {
        const bool ok = base(x);
        if (x == pop2[2]) pop2[0]->alive = false;
        return ok;
    });
    CHECK_EQ(accepted2, 4);
    for (auto& f : store2) CHECK_EQ(f.stimulated, 1);
}

void caseNullAndDead() {
    std::vector<Fake> store = line(3, P2SpeciesBlue, 0);
    store[1].alive = false;
    std::vector<Fake*> pop{nullptr, &store[0], nullptr, &store[1], &store[2]};
    std::vector<Fake*> snap;
    collect(full(), pop, pos, alive, snap);
    CHECK_EQ(snap.size(), 2);
    CHECK_EQ(dispatch(snap, alive, receiver(0)), 2);
    CHECK_EQ(store[1].offered, 0);
}

void caseCaptains() {
    std::vector<FakeNavi> navis{{0, 0, 0, IN_Z, true}, {1, 10, 0, IN_Z + 20, true}, {2, 0, 0, -20, true}};
    std::vector<FakeNavi*> pop;
    for (auto& n : navis) pop.push_back(&n);
    std::vector<FakeNavi*> snap;
    collect(full(), pop, pos, alive, snap);
    CHECK_EQ(snap.size(), 2);
    CHECK_EQ(dispatch(snap, alive, [](FakeNavi*) { return true; }), 2);
}

// Attack trigger == isAttackable(false) (Tank.cpp:266-319, TankState.cpp:91).
bool triggers(float heading, float x, float y, float z) {
    const p2tank::Params& p = p2tank::params(0);
    const Frame f = triggerFrame(0, 0, 0, heading, p.attackRange, p.attackRadius);
    Fake a{0, x, y, z, true, P2SpeciesRed};
    std::vector<Fake*> pop{&a};
    return firstExposed(f, pop, pos, alive) == &a;
}

// Does a breath committed now reach a stationary actor at (x,y,z)? Discharge
// runs from the frame after KEYEVENT_2 to the end of attack.bca.
bool breathReaches(float heading, float x, float y, float z) {
    const p2tank::Params& p = p2tank::params(0);
    Emit e;
    for (int n = KEYEVENT2_FRAME + 1; n <= ATTACK_CLIP_FRAMES; ++n) {
        const float r = advance(e, p.attackRange, 1.0f / ANIM_FPS);
        if (exposed(frame(0, 0, 0, heading, r, p.attackRadius), x, y, z)) return true;
    }
    return false;
}

void caseTriggerSubsetOfBreath() {
    // Growth reaches full range well inside the discharge window.
    CHECK(ATTACK_CLIP_FRAMES - KEYEVENT2_FRAME >= 16);
    int triggered = 0, whiffs = 0;
    for (float heading : {0.0f, 0.7f, -2.3f, 3.1f}) {
        for (float x = -200.0f; x <= 200.0f; x += 4.0f)
            for (float z = -200.0f; z <= 200.0f; z += 4.0f)
                for (float y : {-30.0f, -10.0f, 0.0f, 20.0f, 35.0f}) {
                    if (!triggers(heading, x, y, z)) continue;
                    ++triggered;
                    if (!breathReaches(heading, x, y, z)) ++whiffs;
                }
    }
    CHECK(triggered > 1000);
    CHECK_EQ(whiffs, 0);
}

void caseNoWhiffTriggers() {
    // Reviewer positions inside the old attackable() cone (distXZ<120 from the
    // feet, |angle|<0.6 rad) that the source box never contains.
    const float polar[][2] = {{100, 0.50f}, {60, 0.45f}, {30, 0.0f}, {80, 0.35f}, {10, 0.0f}};
    for (auto& c : polar) {
        const float x = c[0] * std::sin(c[1]), z = c[0] * std::cos(c[1]);
        CHECK(!triggers(0.0f, x, 0.0f, z));
        CHECK(!breathReaches(0.0f, x, 0.0f, z));
    }
    // Full-range box edge: beyond the old 120-unit trigger but inside the box.
    CHECK(triggers(0.0f, 0.0f, 0.0f, EMIT_FORWARD + 110.0f));
    CHECK(breathReaches(0.0f, 0.0f, 0.0f, EMIT_FORWARD + 110.0f));
}

void caseTriggerTargetIsInBox() {
    // The nearest actor (under the snout) cannot start a breath; an in-box
    // actor further away is the source mTargetCreature.
    const p2tank::Params& p = p2tank::params(0);
    const Frame f = triggerFrame(0, 0, 0, 0.0f, p.attackRange, p.attackRadius);
    Fake nearOut{0, 0, 0, 20.0f, true, P2SpeciesRed}, farIn{1, 5, 0, IN_Z, true, P2SpeciesRed};
    Fake deadIn{2, 0, 0, IN_Z, false, P2SpeciesRed};
    std::vector<Fake*> pop{&nearOut, &deadIn, &farIn};
    CHECK(firstExposed(f, pop, pos, alive) == &farIn);
    std::vector<Fake*> none{&nearOut, &deadIn, nullptr};
    CHECK(firstExposed(f, none, pos, alive) == nullptr);
    // Captains trigger too (isNavi(), Tank.cpp:295).
    FakeNavi navi{0, 0, 0, IN_Z, true};
    std::vector<FakeNavi*> navis{&navi};
    CHECK(firstExposed(f, navis, pos, alive) == &navi);
}

void caseParams() {
    for (int kind = 0; kind < 2; ++kind) {
        CHECK(p2tank::params(kind).attackRange == 120.0f);
        CHECK(p2tank::params(kind).attackRadius == 25.0f);
    }
    CHECK(p2tank::params(0).attackDamage == 10.0f);
    CHECK(p2tank::params(1).attackDamage == 0.0f);
}
} // namespace

int main() {
    caseMoreThanSix();
    caseImmuneCannotShield(0, P2SpeciesRed, P2SpeciesBlue);       // Tank: six Red, ten Blue
    caseImmuneCannotShield(1, P2SpeciesBlue, P2SpeciesRed);       // Wtank: six Blue, ten Red
    caseImmuneCannotShield(0, P2SpeciesBulbmin, P2SpeciesYellow); // Bulbmin vs both kinds
    caseImmuneCannotShield(1, P2SpeciesBulbmin, P2SpeciesYellow);
    caseOrderIndependence();
    caseGeometry();
    caseRangeGrowth();
    caseTiming();
    caseRemovalDuringDispatch();
    caseNullAndDead();
    caseCaptains();
    caseTriggerSubsetOfBreath();
    caseNoWhiffTriggers();
    caseTriggerTargetIsInBox();
    caseParams();
    if (failures) { std::fprintf(stderr, "p2_tank_breath_test: %d failure(s)\n", failures); return 1; }
    std::puts("p2_tank_breath_test: all cases passed");
    return 0;
}
