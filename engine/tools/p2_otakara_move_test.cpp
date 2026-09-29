// p2_otakara_move_test (#884): elemental Dweevils (FireOtakara 59, WaterOtakara 60,
// GasOtakara 61, ElecOtakara 62) must ESCAPE from the nearest Pikmin/Navi, bounded by
// their home territory, as P2 OtakaraBase::isMovePositionSet/getTargetPosition
// (OtakaraBase.cpp:361-444) does; BombOtakara (93) keeps chasing (StateBombMove,
// OtakaraBaseState.cpp:812-848) and a treasure target is still pursued
// (OtakaraBase.cpp:370-372). Engine-free: exercises pc_p2_otakara_move.h directly.
//
// Negative control: legacyMovePosition is a verbatim transcription of the old
// pc_p2_otakara.cpp:810-811 destination rule (walk AT the target; home only once
// already outside the territory). The directional and clamp cases run against both,
// the legacy rule must fail all 8 directional cases, and building with
// -DP2_OTAKARA_MOVE_TEST_USE_LEGACY swaps it in as the implementation under test,
// which makes this test exit non-zero (the red state).
//
// Fix round 1 (#884 review) adds two more negative controls, swapped in by the same
// -DP2_OTAKARA_MOVE_TEST_USE_LEGACY switch:
//   * legacyFlickTrigger: the round-0 port Flick trigger (any live Piki within 60,
//     nearestPiki(pos, FLICK_RADIUS) in pc_p2_otakara.cpp @ ead0c008), which made an
//     approaching Pikmin stop the escape and force a discharge before a single hit.
//     Source isStartFlick (enemyAction.cpp:1209-1244) needs more than ip01=6 hits.
//   * roundZeroPursue: the round-0 BombOtakara destination (raw target, no territory
//     rule, pc_p2_otakara_move.h @ ead0c008 :123), which let a Volatile Dweevil be led
//     anywhere; the source bounds its chase with the 1.5 s stimulateBomb fuse.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert():
// release build types define NDEBUG, which would compile assert() out.
#include "pc_p2_otakara_move.h"

#include <cmath>
#include <cstdio>
#include <vector>

using namespace p2otakaramove;

static int failures = 0;

#define CHECK(cond)                                                                        \
    do {                                                                                   \
        if (!(cond)) {                                                                     \
            std::printf("P2_OTAKARA_MOVE_TEST_FAIL line=%d check=%s\n", __LINE__, #cond);  \
            ++failures;                                                                    \
        }                                                                                  \
    } while (0)

namespace {

constexpr float kTerritory = 200.0f; // fp09
constexpr float kSight = 200.0f;     // fp12
constexpr float kSpeed = 80.0f;      // fp06 (Fire/Water/Elec)
constexpr float kGasSpeed = 100.0f;  // fp06 GasOtakara override
constexpr float kDt = 1.0f / 30.0f;
constexpr float kWaitClip = 30.0f / 30.0f;  // wait1 30 frames
constexpr float kMoveClip = 20.0f / 30.0f;  // move1 20 frames
constexpr float kPivotClip = 20.0f / 30.0f; // pivot1 20 frames

using MoveFn = Vec2 (*)(Vec2 self, Vec2 threat, Vec2 home, float speed, float territory, bool* clamped);

// Old pc_p2_otakara.cpp:810-811, verbatim rule:
//   if (distXZ(pos, s.home) > TERRITORY) s.target = s.home;
//   else if (target) s.target = target->getPosition();
Vec2 legacyMovePosition(Vec2 self, Vec2 threat, Vec2 home, float, float territory, bool* clamped) {
    if (clamped) *clamped = false;
    if (distXZ(self, home) > territory) return home;
    return threat;
}

Vec2 newMovePosition(Vec2 self, Vec2 threat, Vec2 home, float speed, float territory, bool* clamped) {
    return movePosition(Mode::Escape, TargetKind::Creature, self, threat, home, speed, territory, clamped);
}

// Flick trigger: hits = mFlickTimer, stuck = mStuckPikminCount, pikiDist = nearest
// live Piki distance (stuck or not).
using FlickFn = bool (*)(float hits, int stuck, float pikiDist);
// Round-0 port trigger: nearestPiki(pos, FLICK_RADIUS=60) != nullptr.
bool legacyFlickTrigger(float, int, float pikiDist) { return pikiDist < 60.0f; }
bool newFlickTrigger(float hits, int stuck, float) { return isStartFlick(hits, stuck); }

// Bomb 93 chase destination: self, target, home, territory.
using PursueFn = Vec2 (*)(Vec2 self, Vec2 target, Vec2 home, float territory);
// Round-0 (ead0c008) Mode::Pursue: `return target;` with no territory rule.
Vec2 roundZeroPursue(Vec2, Vec2 target, Vec2, float) { return target; }
Vec2 newPursue(Vec2 self, Vec2 target, Vec2 home, float territory) {
    return movePosition(Mode::Pursue, TargetKind::Creature, self, target, home, kSpeed, territory);
}

#ifdef P2_OTAKARA_MOVE_TEST_USE_LEGACY
const MoveFn kUnderTest = legacyMovePosition;
const FlickFn kFlickUnderTest = legacyFlickTrigger;
const PursueFn kPursueUnderTest = roundZeroPursue;
const char* kUnderTestName = "legacy";
#else
const MoveFn kUnderTest = newMovePosition;
const FlickFn kFlickUnderTest = newFlickTrigger;
const PursueFn kPursueUnderTest = newPursue;
const char* kUnderTestName = "header";
#endif

bool near(float a, float b, float eps = 1e-3f) { return std::fabs(a - b) <= eps; }
bool nearV(Vec2 a, Vec2 b, float eps = 1e-3f) { return near(a.x, b.x, eps) && near(a.z, b.z, eps); }
bool finiteV(Vec2 v) { return std::isfinite(v.x) && std::isfinite(v.z); }
float len(Vec2 v) { return std::sqrt(v.x * v.x + v.z * v.z); }
Vec2 onCircle(Vec2 c, float r, float deg) {
    const float a = deg * kPi / 180.0f;
    return Vec2{c.x + r * std::sin(a), c.z + r * std::cos(a)};
}

// Case 1: eight approach angles, Dweevil at home, threat 100 away. Returns the
// number of angles that fail (0 = pass). `report` prints each failing angle.
int directionalFailures(MoveFn fn, float speed, bool report) {
    int failed = 0;
    const Vec2 home{0.0f, 0.0f};
    for (int k = 0; k < 8; ++k) {
        const float deg = 45.0f * float(k);
        const Vec2 self = home;
        const Vec2 threat = onCircle(self, 100.0f, deg);
        bool clamped = true;
        const Vec2 dest = fn(self, threat, home, speed, kTerritory, &clamped);
        const Vec2 away{self.x - threat.x, self.z - threat.z};
        const float al = len(away);
        const Vec2 expect{self.x + away.x / al * speed, self.z + away.z / al * speed};
        const float dot = (dest.x - self.x) * away.x + (dest.z - self.z) * away.z;
        const bool ok = finiteV(dest) && nearV(dest, expect) && distXZ(dest, threat) > distXZ(self, threat)
                        && dot > 0.0f && !clamped;
        if (!ok) {
            ++failed;
            if (report) {
                std::printf("P2_OTAKARA_MOVE_TEST_DIRECTION angle=%.0f speed=%.0f self=%.1f,%.1f threat=%.1f,%.1f "
                            "dest=%.1f,%.1f expect=%.1f,%.1f dist_before=%.1f dist_after=%.1f\n",
                            deg, speed, self.x, self.z, threat.x, threat.z, dest.x, dest.z, expect.x, expect.z,
                            distXZ(self, threat), distXZ(dest, threat));
            }
        }
    }
    return failed;
}

// Case 3: territory clamp. Returns the number of failing sub-cases.
int clampFailures(MoveFn fn, bool report) {
    int failed = 0;
    const Vec2 home{0.0f, 0.0f};
    auto one = [&](const char* name, Vec2 self, Vec2 threat, bool ok_fn(Vec2, bool)) {
        bool clamped = false;
        const Vec2 dest = fn(self, threat, home, kSpeed, kTerritory, &clamped);
        const bool ok = finiteV(dest) && ok_fn(dest, clamped) && distXZ(dest, home) <= kTerritory + 1e-3f;
        if (!ok) {
            ++failed;
            if (report) {
                std::printf("P2_OTAKARA_MOVE_TEST_CLAMP case=%s dest=%.2f,%.2f clamped=%d home_dist=%.2f\n", name,
                            dest.x, dest.z, int(clamped), distXZ(dest, home));
            }
        }
    };
    // Fleeing outward from (190,0): 270 is outside, projected onto the circle.
    one("edge_out", Vec2{190.0f, 0.0f}, Vec2{150.0f, 0.0f},
        [](Vec2 d, bool c) { return nearV(d, Vec2{200.0f, 0.0f}) && c; });
    // Fleeing inward from (190,0): 110 stays inside, unclamped.
    one("edge_in", Vec2{190.0f, 0.0f}, Vec2{250.0f, 0.0f},
        [](Vec2 d, bool c) { return nearV(d, Vec2{110.0f, 0.0f}) && !c; });
    // Knocked outside the territory: the destination is back on the circle.
    one("knocked_out", Vec2{260.0f, 0.0f}, Vec2{200.0f, 0.0f},
        [](Vec2 d, bool c) { return nearV(d, Vec2{200.0f, 0.0f}) && c; });
    // Radial along +z.
    one("radial_z", Vec2{0.0f, 190.0f}, Vec2{0.0f, 150.0f},
        [](Vec2 d, bool c) { return near(len(d), 200.0f) && nearV(d, Vec2{0.0f, 200.0f}) && c; });
    // Tangential flee near the edge: (80,190) is outside, |dest| == 200 along it.
    one("tangential", Vec2{0.0f, 190.0f}, Vec2{-100.0f, 190.0f}, [](Vec2 d, bool c) {
        const float l = std::sqrt(80.0f * 80.0f + 190.0f * 190.0f);
        return near(len(d), 200.0f) && nearV(d, Vec2{80.0f / l * 200.0f, 190.0f / l * 200.0f}) && c;
    });
    return failed;
}

float clipFor(St st) {
    switch (st) {
    case St::Move: return kMoveClip;
    case St::Turn: return kPivotClip;
    default: return kWaitClip;
    }
}

struct SimResult {
    bool sawTurn = false;
    bool sawMoveAfterTurn = false;
    bool stayedBounded = true;
    bool destBounded = true;
    float startDist = 0.0f;
    float endDist = 0.0f;
    float maxHome = 0.0f;
};

// Closed loop over the source Wait/Move/Turn decision (decide + clip-end commit),
// turnToTarget (turnStep) and walkToTarget. `chaseSpeed` > 0 makes the threat walk
// at the Dweevil. Starts in Wait facing the threat. The body may pass the circle by
// `bodySlack`: walkToTarget (enemyAction.cpp:2102-2107) has no arrival slowdown, so a
// full step can overshoot a destination that lies on the circle (boundary jitter).
SimResult simulate(MoveFn fn, float angleDeg, int ticks, float speed, float chaseSpeed, float bodySlack) {
    SimResult r;
    const Vec2 home{0.0f, 0.0f};
    Vec2 self = home;
    Vec2 threat = onCircle(self, 100.0f, angleDeg);
    float heading = headingTo(self, threat);
    St st = St::Wait;
    bool pending = false;
    St next = St::Wait;
    float stateTime = 0.0f;
    r.startDist = distXZ(self, threat);
    for (int t = 0; t < ticks; ++t) {
        const float prev = stateTime;
        stateTime += kDt;
        Candidate c[1] = {{threat, false, true, false, false}};
        const bool has = selectThreat(c, 1, self, kSight) >= 0;
        bool clamped = false;
        const Vec2 dest = has ? fn(self, threat, home, speed, kTerritory, &clamped) : self;
        if (distXZ(dest, home) > kTerritory + 1e-3f) r.destBounded = false;
        const bool facing = has && facingWithinGate(heading, self, dest);
        if (st == St::Move && facing) {
            heading = turnStep(heading, self, dest, kDt);
            self.x += std::sin(heading) * speed * kDt;
            self.z += std::cos(heading) * speed * kDt;
        } else if (st == St::Turn && has) {
            heading = turnStep(heading, self, dest, kDt);
        }
        const St d = decide({st, has, facing, false, false});
        if (d != st) {
            pending = true;
            next = d;
        }
        if (pending && clipEndCrossed(prev, stateTime, clipFor(st))) {
            if (next == St::Turn) r.sawTurn = true;
            if (next == St::Move && r.sawTurn) r.sawMoveAfterTurn = true;
            st = next;
            pending = false;
            stateTime = 0.0f;
        }
        const float h = distXZ(self, home);
        if (h > r.maxHome) r.maxHome = h;
        if (h > kTerritory + bodySlack) r.stayedBounded = false;
        if (chaseSpeed > 0.0f) {
            const Vec2 to{self.x - threat.x, self.z - threat.z};
            const float l = len(to);
            if (l > 1.0f) {
                threat.x += to.x / l * chaseSpeed * kDt;
                threat.z += to.z / l * chaseSpeed * kDt;
            }
        }
    }
    r.endDist = distXZ(self, threat);
    return r;
}

struct ApproachResult {
    bool fled = false;           // the Dweevil ended well away from home
    int flicks = 0;              // Flicks committed
    int landedAtFirstFlick = -1; // hits landed in total when the first Flick committed
    float minCounterAtFlick = 1e9f; // hit counter (mFlickTimer) at each Flick commit
    float fleeDist = 0.0f;       // Dweevil distance from home when the run ended
};

// Closed loop over the source Wait/Move/Turn/Flick decision: one Pikmin walks at the
// Dweevil at `pikiSpeed`; with `hitting`, once in melee (< 15) it lands one hit every
// 0.5 s (+1 mFlickTimer each, as addDamage(damage, 1.0f)). `stuck` models
// mStuckPikminCount. Flick event 2 (attack1 frame 12) resets the counter
// (OtakaraBaseState.cpp:107); the attack1 end runs afterFlick.
ApproachResult approach(FlickFn flickFn, float angleDeg, float pikiSpeed, bool hitting, int stuck, int ticks) {
    ApproachResult r;
    const Vec2 home{0.0f, 0.0f};
    Vec2 self = home;
    Vec2 piki = onCircle(self, 100.0f, angleDeg);
    float heading = headingTo(self, piki);
    St st = St::Wait;
    St next = St::Wait;
    bool pending = false;
    float stateTime = 0.0f;
    float hits = 0.0f;
    int landed = 0;
    float hitTimer = 0.0f;
    const float attackClip = 50.0f / 30.0f; // attack1 50 frames
    const float event2 = 12.0f / 30.0f;     // attack1 frame 12, event type 2
    for (int t = 0; t < ticks; ++t) {
        const float prev = stateTime;
        stateTime += kDt;
        const float pikiDist = distXZ(self, piki);
        if (hitting && pikiDist < 15.0f) {
            hitTimer += kDt;
            if (hitTimer >= 0.5f) {
                hitTimer = 0.0f;
                hits += 1.0f;
                ++landed;
            }
        }
        Candidate c[1] = {{piki, false, true, false, false}};
        const bool has = selectThreat(c, 1, self, kSight) >= 0;
        const Vec2 dest = has ? escapePosition(self, piki, home, kSpeed, kTerritory) : self;
        const bool facing = has && facingWithinGate(heading, self, dest);
        if (st == St::Flick) {
            if (prev < event2 && stateTime >= event2) hits = 0.0f;
            if (stateTime >= attackClip) {
                st = afterFlick(false, has, facing);
                stateTime = 0.0f;
                pending = false;
            }
        } else {
            const bool flick = flickFn(hits, stuck, pikiDist);
            if (st == St::Move && facing && !flick) {
                heading = turnStep(heading, self, dest, kDt);
                self.x += std::sin(heading) * kSpeed * kDt;
                self.z += std::cos(heading) * kSpeed * kDt;
            } else if (st == St::Turn && has) {
                heading = turnStep(heading, self, dest, kDt);
            }
            const St d = decide({st, has, facing, flick, false});
            if (d != st) {
                pending = true;
                next = d;
            }
            if (pending && clipEndCrossed(prev, stateTime, clipFor(st))) {
                if (next == St::Flick) {
                    if (r.flicks == 0) r.landedAtFirstFlick = landed;
                    if (hits < r.minCounterAtFlick) r.minCounterAtFlick = hits;
                    ++r.flicks;
                }
                st = next;
                pending = false;
                stateTime = 0.0f;
            }
        }
        const Vec2 to{self.x - piki.x, self.z - piki.z};
        const float l = len(to);
        if (l > 1.0f) {
            const float step = std::fmin(pikiSpeed * kDt, l - 1.0f);
            piki.x += to.x / l * step;
            piki.z += to.z / l * step;
        }
    }
    r.fleeDist = distXZ(self, home);
    r.fled = r.fleeDist > 100.0f;
    return r;
}

// BombOtakara 93 chasing a Navi that walks straight away from home at `naviSpeed`
// (stopping 1000 out). Returns the largest distance from home the Bomb body reached.
float bombLeash(PursueFn fn, float angleDeg, float naviSpeed, int ticks) {
    const Vec2 home{0.0f, 0.0f};
    Vec2 self = home;
    Vec2 navi = onCircle(home, 60.0f, angleDeg);
    const Vec2 dir{std::sin(angleDeg * kPi / 180.0f), std::cos(angleDeg * kPi / 180.0f)};
    float heading = headingTo(self, navi);
    float maxHome = 0.0f;
    for (int t = 0; t < ticks; ++t) {
        const Vec2 dest = fn(self, navi, home, kTerritory);
        if (distXZ(self, dest) > 1.0f) {
            heading = turnStep(heading, self, dest, kDt);
            if (facingWithinGate(heading, self, dest)) {
                self.x += std::sin(heading) * kSpeed * kDt;
                self.z += std::cos(heading) * kSpeed * kDt;
            }
        }
        if (distXZ(navi, home) < 1000.0f) {
            navi.x += dir.x * naviSpeed * kDt;
            navi.z += dir.z * naviSpeed * kDt;
        }
        const float h = distXZ(self, home);
        if (h > maxHome) maxHome = h;
    }
    return maxHome;
}

} // namespace

int main() {
    std::printf("P2_OTAKARA_MOVE_TEST under_test=%s\n", kUnderTestName);

    // 1. Eight approach angles (Fire/Water/Elec speed 80, Gas speed 100).
    const int underTestDirectional =
        directionalFailures(kUnderTest, kSpeed, true) + directionalFailures(kUnderTest, kGasSpeed, true);
    CHECK(underTestDirectional == 0);
    const int legacyDirectional = directionalFailures(legacyMovePosition, kSpeed, false);
    CHECK(legacyDirectional == 8); // negative control: the old rule walks AT the threat
    const int headerDirectional = directionalFailures(newMovePosition, kSpeed, false);

    // 2. Closed-loop per angle: Wait -> Turn -> Move, distance grows, bounded.
    for (int k = 0; k < 8; ++k) {
        const float deg = 45.0f * float(k);
        const SimResult r = simulate(kUnderTest, deg, 90, kSpeed, 0.0f, kSpeed * kDt);
        if (!(r.sawTurn && r.sawMoveAfterTurn && r.endDist > r.startDist && r.stayedBounded && r.destBounded)) {
            std::printf("P2_OTAKARA_MOVE_TEST_SIM angle=%.0f turn=%d move=%d start=%.1f end=%.1f max_home=%.1f\n",
                        deg, int(r.sawTurn), int(r.sawMoveAfterTurn), r.startDist, r.endDist, r.maxHome);
        }
        CHECK(r.sawTurn);
        CHECK(r.sawMoveAfterTurn);
        CHECK(r.endDist > r.startDist);
        CHECK(r.stayedBounded);
        CHECK(r.destBounded);
        // A slower pursuer drives the Dweevil onto its territory edge for 30 s: the
        // destination always stays inside and the body within two steps of the circle.
        const SimResult chased = simulate(kUnderTest, deg, 900, kGasSpeed, 50.0f, 2.0f * kGasSpeed * kDt);
        if (!(chased.stayedBounded && chased.destBounded && chased.maxHome > 150.0f)) {
            std::printf("P2_OTAKARA_MOVE_TEST_CHASE angle=%.0f max_home=%.2f bounded=%d dest_bounded=%d\n", deg,
                        chased.maxHome, int(chased.stayedBounded), int(chased.destBounded));
        }
        CHECK(chased.stayedBounded);
        CHECK(chased.destBounded);
        CHECK(chased.maxHome > 150.0f); // it really fled toward the edge
    }

    // 3. Territory clamp.
    CHECK(clampFailures(kUnderTest, true) == 0);
    const int legacyClamp = clampFailures(legacyMovePosition, false);
    CHECK(legacyClamp > 0);

    // 4. Degenerate: coincident threat -> dest == self, no NaN.
    {
        const Vec2 self{12.0f, -7.0f};
        bool clamped = true;
        const Vec2 dest = escapePosition(self, self, Vec2{0.0f, 0.0f}, kSpeed, kTerritory, &clamped);
        CHECK(finiteV(dest));
        CHECK(nearV(dest, self));
        CHECK(!clamped);
        const float h = turnStep(0.5f, self, dest, kDt);
        CHECK(std::isfinite(h));
    }

    // 5. Threat selection (getNearestPikminOrNavi + ConditionNotStickClientAndItem).
    {
        const Vec2 self{0.0f, 0.0f};
        {
            Candidate c[3] = {{{0.0f, 10.0f}, false, true, true, false},  // stuck to this Dweevil
                              {{0.0f, 20.0f}, false, true, false, true},  // stuck to a mouth
                              {{0.0f, 90.0f}, false, true, false, false}};
            CHECK(selectThreat(c, 3, self, kSight) == 2);
        }
        {
            Candidate in[1] = {{{0.0f, 199.0f}, false, true, false, false}};
            Candidate out[1] = {{{0.0f, 201.0f}, false, true, false, false}};
            CHECK(selectThreat(in, 1, self, kSight) == 0);
            CHECK(selectThreat(out, 1, self, kSight) == -1);
        }
        {
            Candidate behind[1] = {{{0.0f, -100.0f}, false, true, false, false}}; // full-circle view
            CHECK(selectThreat(behind, 1, self, kSight) == 0);
        }
        {
            Candidate tie[2] = {{{0.0f, 50.0f}, false, true, false, false}, {{50.0f, 0.0f}, true, true, false, false}};
            CHECK(selectThreat(tie, 2, self, kSight) == 1); // Navi wins the tie
            Candidate closer[2] = {{{0.0f, 49.9f}, false, true, false, false},
                                   {{50.0f, 0.0f}, true, true, false, false}};
            CHECK(selectThreat(closer, 2, self, kSight) == 0); // strictly closer Piki wins
        }
        {
            Candidate stuck[2] = {{{0.0f, 5.0f}, false, true, true, false}, {{5.0f, 0.0f}, false, true, false, true}};
            CHECK(selectThreat(stuck, 2, self, kSight) == -1);
            Candidate dead[2] = {{{0.0f, 5.0f}, false, false, false, false}, {{5.0f, 0.0f}, true, false, false, false}};
            CHECK(selectThreat(dead, 2, self, kSight) == -1);
        }
    }

    // 6. Pursuit preserved: Bomb 93 chases, a treasure target is pursued.
    {
        const Vec2 home{0.0f, 0.0f};
        for (int k = 0; k < 8; ++k) {
            const Vec2 threat = onCircle(home, 100.0f, 45.0f * float(k));
            const Vec2 dest = movePosition(Mode::Pursue, TargetKind::Creature, home, threat, home, kSpeed, kTerritory);
            CHECK(nearV(dest, threat));
        }
        const Vec2 self{10.0f, 10.0f};
        const Vec2 treasure{60.0f, -40.0f};
        CHECK(nearV(movePosition(Mode::Escape, TargetKind::Treasure, self, treasure, home, kSpeed, kTerritory),
                    treasure));
        CHECK(nearV(movePosition(Mode::Escape, TargetKind::None, self, treasure, home, kSpeed, kTerritory), self));
    }

    // 7. Attack precedence: Flick overrides the move decision, Dead overrides Flick.
    {
        CHECK(decide({St::Move, true, true, true, false}) == St::Flick);
        CHECK(decide({St::Wait, true, true, true, false}) == St::Flick);
        CHECK(decide({St::Turn, true, false, true, false}) == St::Flick);
        CHECK(decide({St::Move, true, true, true, true}) == St::Dead);
        CHECK(decide({St::Wait, false, false, false, false}) == St::Wait); // no idle pivot
        CHECK(decide({St::Wait, true, true, false, false}) == St::Move);
        CHECK(decide({St::Wait, true, false, false, false}) == St::Turn);
        CHECK(decide({St::Move, true, true, false, false}) == St::Move);
        CHECK(decide({St::Move, true, false, false, false}) == St::Turn);
        CHECK(decide({St::Move, false, false, false, false}) == St::Wait);
        CHECK(decide({St::Turn, true, true, false, false}) == St::Move);
        CHECK(decide({St::Turn, false, false, false, false}) == St::Wait);
        CHECK(afterFlick(false, true, true) == St::Move);
        CHECK(afterFlick(false, true, false) == St::Turn);
        CHECK(afterFlick(false, false, true) == St::Wait);
        CHECK(afterFlick(false, false, false) == St::Wait);
        CHECK(afterFlick(true, true, true) == St::Dead);
        CHECK(afterFlick(true, false, false) == St::Dead);
        // Facing gate is THIRD_PI inclusive-ish around the heading.
        const Vec2 o{0.0f, 0.0f};
        CHECK(facingWithinGate(0.0f, o, onCircle(o, 50.0f, 59.0f)));
        CHECK(!facingWithinGate(0.0f, o, onCircle(o, 50.0f, 61.0f)));
        CHECK(facingWithinGate(0.0f, o, onCircle(o, 50.0f, -59.0f)));
        // turnStep: 4 deg per 30 Hz tick at most, 25% proportional below that.
        CHECK(near(turnStep(0.0f, o, onCircle(o, 50.0f, 90.0f), kDt), 4.0f * kPi / 180.0f, 1e-4f));
        CHECK(near(turnStep(0.0f, o, onCircle(o, 50.0f, 8.0f), kDt), 2.0f * kPi / 180.0f, 1e-4f));
    }

    // 8. Clip end gate (finishMotion -> KEYEVENT_END), including loop wraps.
    {
        const float d = 0.6667f;
        CHECK(clipEndCrossed(0.60f, 0.68f, d));
        CHECK(!clipEndCrossed(0.10f, 0.20f, d));
        CHECK(clipEndCrossed(1.30f, 1.34f, d));
        CHECK(!clipEndCrossed(0.70f, 0.80f, d));
        CHECK(clipEndCrossed(0.0f, 1.0f, 1.0f));
        CHECK(clipEndCrossed(0.1f, 0.2f, 0.0f));
    }

    // 9. Source isStartFlick thresholds (retail ip01-ip07 = 6/5/12/10/17/20/22).
    {
        CHECK(!isStartFlick(0.0f, 0));
        CHECK(!isStartFlick(6.0f, 0));
        CHECK(!isStartFlick(6.4f, 0));
        CHECK(isStartFlick(6.5f, 0)); // rounded half up -> 7 > 6
        CHECK(isStartFlick(7.0f, 4));
        CHECK(!isStartFlick(12.0f, 5));
        CHECK(isStartFlick(13.0f, 9));
        CHECK(!isStartFlick(17.0f, 10));
        CHECK(isStartFlick(18.0f, 19));
        CHECK(!isStartFlick(22.0f, 20));
        CHECK(isStartFlick(23.0f, 40));
        CHECK(!isStartFlick(256.0f, 0)); // u8 truncation, as the source
    }

    // 10. Ordinary approach from eight directions, no hit landed: the Dweevil flees and
    // never discharges. The round-0 proximity trigger discharged as soon as the Pikmin
    // closed to 60, before a single hit (negative control).
    int legacyApproachFlicks = 0;
    for (int k = 0; k < 8; ++k) {
        const float deg = 45.0f * float(k);
        const ApproachResult r = approach(kFlickUnderTest, deg, 60.0f, false, 0, 900);
        if (r.flicks != 0 || !r.fled) {
            std::printf("P2_OTAKARA_MOVE_TEST_APPROACH angle=%.0f flicks=%d flee_dist=%.1f\n", deg, r.flicks,
                        r.fleeDist);
        }
        CHECK(r.flicks == 0);
        CHECK(r.fled);
        if (approach(legacyFlickTrigger, deg, 60.0f, false, 0, 900).flicks > 0) ++legacyApproachFlicks;
    }
    CHECK(legacyApproachFlicks == 8);

    // 11. Hits drive the Flick. A Pikmin faster than the Dweevil stays in melee and
    // lands a hit every 0.5 s: every Flick commits with the counter above ip01=6 (0
    // stuck) or ip03=12 (5 stuck), and event 2 resets it, so the Dweevil flees again
    // between discharges instead of discharging back to back.
    for (int k = 0; k < 8; k += 2) {
        const float deg = 45.0f * float(k);
        const ApproachResult r = approach(kFlickUnderTest, deg, 120.0f, true, 0, 1800);
        const ApproachResult stuck = approach(kFlickUnderTest, deg, 120.0f, true, 5, 1800);
        if (r.flicks < 2 || r.minCounterAtFlick < 7.0f || stuck.flicks < 1 || stuck.minCounterAtFlick < 13.0f) {
            std::printf("P2_OTAKARA_MOVE_TEST_HITS angle=%.0f flicks=%d first_at=%d min_counter=%.0f "
                        "stuck_flicks=%d stuck_min_counter=%.0f\n",
                        deg, r.flicks, r.landedAtFirstFlick, r.minCounterAtFlick, stuck.flicks,
                        stuck.minCounterAtFlick);
        }
        CHECK(r.flicks >= 2);
        CHECK(r.landedAtFirstFlick >= 7);
        CHECK(r.minCounterAtFlick >= 7.0f);
        CHECK(stuck.flicks >= 1);
        CHECK(stuck.minCounterAtFlick >= 13.0f);
    }

    // 12. BombOtakara 93: chase keeps a territory bound, plus the stimulateBomb fuse.
    float roundZeroLeash = 0.0f;
    {
        const Vec2 home{0.0f, 0.0f};
        bool clamped = true;
        CHECK(nearV(pursuePosition(Vec2{50.0f, 0.0f}, Vec2{150.0f, 0.0f}, home, kTerritory, &clamped),
                    Vec2{150.0f, 0.0f}));
        CHECK(!clamped);
        // Target outside the territory while the body is inside: still chased.
        CHECK(nearV(pursuePosition(Vec2{190.0f, 0.0f}, Vec2{400.0f, 0.0f}, home, kTerritory, &clamped),
                    Vec2{400.0f, 0.0f}));
        CHECK(!clamped);
        // Body outside the territory: the destination is home, clamped.
        CHECK(nearV(pursuePosition(Vec2{250.0f, 0.0f}, Vec2{400.0f, 0.0f}, home, kTerritory, &clamped), home));
        CHECK(clamped);
        CHECK(nearV(movePosition(Mode::Pursue, TargetKind::Creature, Vec2{250.0f, 0.0f}, Vec2{400.0f, 0.0f}, home,
                                 kSpeed, kTerritory, &clamped),
                    home));
        CHECK(clamped);
        // A Navi walking away at 100 cannot lead the Bomb off: 60 s, 8 directions.
        for (int k = 0; k < 8; ++k) {
            const float deg = 45.0f * float(k);
            const float leash = bombLeash(kPursueUnderTest, deg, 100.0f, 1800);
            if (leash > kTerritory + 2.0f * kSpeed * kDt) {
                std::printf("P2_OTAKARA_MOVE_TEST_BOMB_LEASH angle=%.0f max_home=%.1f\n", deg, leash);
            }
            CHECK(leash <= kTerritory + 2.0f * kSpeed * kDt);
            const float old = bombLeash(roundZeroPursue, deg, 100.0f, 1800);
            if (old > roundZeroLeash) roundZeroLeash = old;
        }
        CHECK(roundZeroLeash > 2.0f * kTerritory); // negative control: round 0 is unbounded
        // stimulateBomb: strictly more than 1.5 s of chase forces the payload.
        float fuse = 1.0f;
        CHECK(!bombFuseStep(fuse, 0.5f));
        CHECK(bombFuseStep(fuse, 0.01f));
        fuse = 0.0f;
        int ticks = 1;
        while (!bombFuseStep(fuse, kDt) && ticks < 1000) ++ticks;
        CHECK(ticks >= 45 && ticks <= 46); // ~1.5 s at 30 Hz
    }

    std::printf("P2_OTAKARA_MOVE_TEST legacy_failures=%d/8 new_failures=%d legacy_clamp_failures=%d/5 "
                "legacy_approach_flicks=%d/8 round0_bomb_max_home=%.0f\n",
                legacyDirectional, headerDirectional, legacyClamp, legacyApproachFlicks, roundZeroLeash);
    std::printf("P2_OTAKARA_MOVE_TEST %s failures=%d\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
