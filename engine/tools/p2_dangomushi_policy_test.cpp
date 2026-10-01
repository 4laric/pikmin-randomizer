// Engine-free regression for the Segmented Crawbster (94) boss loop (#897).
// Every section encodes a decomp rule (see pc_port/pc_p2_dangomushi_policy.h)
// that the pre-#897 port (fork/main 0b9f6c815) violated:
//   WALL   territory-150 Turn exit instead of Obj::wallCallback
//   PRESS  one InteractFlick to the first target once per roll
//   TURN   linear 32..108 window (~2.5 s), clip never looped
//   SHAKE  no setBodyCollision(true) sticker shake at window close
//   FLICK  zero-damage flick to Pikmin only; captains untouched, no Purple rule
// and the #897 review (0cec11053) regressions:
//   CRUSH_LETHAL   InteractPress(10) only stunned a flower/bud Pikmin on P1
//   FLICK_DIR      the claw flick pushed victims toward the crab
//   ROLL_FINISH    15 s timeout jumped straight to Wait (no loop run-out/uncurl)
//   TURN_DEATH     death in Turn skipped the tail (source finishMotion)
// Sections report independently so a mutant run shows exactly what regressed.
#include "pc_p2_dangomushi_policy.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <set>

namespace {
int gFailures = 0;
int gSectionFailures = 0;
#define CHECK(cond)                                                         \
    do {                                                                    \
        if (!(cond)) {                                                      \
            ++gFailures;                                                    \
            ++gSectionFailures;                                             \
            std::printf("  FAIL %s:%d %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                   \
    } while (0)

void section(const char* name, void (*fn)()) {
    gSectionFailures = 0;
    fn();
    std::printf("%s %s\n", gSectionFailures ? "FAIL" : "PASS", name);
}

using namespace p2dango;

void wallSection() {
    // Head-on and 45-degree crashes at roll speed 200 enter Turn.
    CHECK(wallCrash(true, 200.0f, 0.0f, 0.0f, -1.0f, 0.0f, 0.0f));
    CHECK(wallCrash(true, 141.4f, 0.0f, 141.4f, -1.0f, 0.0f, 0.0f)); // dot -0.707
    // Glancing (dot -0.3), slow (90 u/s) and not rolling never crash.
    CHECK(!wallCrash(true, 190.8f, 0.0f, 60.0f, -0.3f, 0.0f, 0.954f));
    CHECK(!wallCrash(true, 90.0f, 0.0f, 0.0f, -1.0f, 0.0f, 0.0f));
    CHECK(!wallCrash(false, 200.0f, 0.0f, 0.0f, -1.0f, 0.0f, 0.0f));
    // The roll does not exit on home distance: 0.75 s at 200 u/s is 150 u,
    // the old territory cut. Far from home with no wall it keeps rolling.
    CHECK(rollExit(0.75f, false, 151.0f) == RollExit::Stay);
    CHECK(rollExit(5.0f, false, 1000.0f) == RollExit::Stay);
    CHECK(rollExit(2.0f, true, 20.0f) == RollExit::Turn);
    CHECK(rollExit(15.01f, false, 0.0f) == RollExit::Wait);
}

void pressSection() {
    PressCrush crush(100.0f, 0.5f);
    PressCandidate c[5];
    c[0].token = 1; c[0].dx = 30.0f;  c[0].grounded = true;
    c[1].token = 2; c[1].dz = -60.0f; c[1].grounded = true;
    c[2].token = 3; c[2].dx = 50.0f; c[2].dz = 50.0f; c[2].grounded = true; // a Navi
    c[3].token = 4; c[3].dx = 10.0f;  c[3].grounded = false; // thrown, airborne
    c[4].token = 5; c[4].dx = 150.0f; c[4].grounded = true;  // out of contact
    std::set<unsigned long long> frame0;
    for (auto& k : c) if (crush.shouldPress(k, 0.0f)) frame0.insert(k.token);
    // Every grounded creature in contact is crushed in the SAME frame.
    CHECK(frame0.size() == 3);
    CHECK(frame0.count(1) && frame0.count(2) && frame0.count(3));
    // Per-target cooldown, then pressed again while the roll lasts.
    int again = 0;
    for (auto& k : c) again += crush.shouldPress(k, 0.1f) ? 1 : 0;
    CHECK(again == 0);
    for (auto& k : c) again += crush.shouldPress(k, 0.6f) ? 1 : 0;
    CHECK(again == 3);
    // A creature that walks into the ball later in the same roll is crushed.
    PressCandidate late; late.token = 9; late.dx = 20.0f; late.grounded = true;
    CHECK(crush.shouldPress(late, 0.7f));
}

void turnSection() {
    float openAt = -1.0f, closeAt = -1.0f, endAt = -1.0f;
    bool loopSeenTwice = false;
    int wraps = 0;
    float prevFrame = -1.0f;
    for (int i = 0; i <= 30 * 12; ++i) {
        const float t = float(i) / 30.0f;
        const TurnClock c = turnClock(t);
        if (c.stickable && openAt < 0.0f) openAt = t;
        if (openAt >= 0.0f && !c.stickable && closeAt < 0.0f) closeAt = t;
        if (c.finished && endAt < 0.0f) endAt = t;
        if (c.looping) {
            CHECK(c.frame >= 32.0f && c.frame < 81.0f);
            if (prevFrame >= 0.0f && c.frame < prevFrame) { ++wraps; loopSeenTwice = true; }
        }
        if (c.tail) CHECK(c.frame >= 81.0f);
        prevFrame = c.frame;
    }
    // LOOP_START opens the window at frame 32.
    CHECK(std::fabs(openAt - 32.0f / 30.0f) < 0.04f);
    // The clip loops 32..81 until FLIP_TIME, so the window lasts >= 5 s
    // (source ~7.4 s), not the old linear 2.5 s.
    CHECK(loopSeenTwice && wraps >= 3);
    CHECK(closeAt > 0.0f && closeAt - openAt >= 5.0f);
    CHECK(closeAt > kFlipTime);
    // Key 3 closes the window before END; END (-> Recover) comes after 7.5 s.
    CHECK(endAt > closeAt && endAt > kFlipTime);
    // The roll clip loops 50..100 while the roll lasts.
    CHECK(attackFrame(10.0f) >= 50.0f && attackFrame(10.0f) < 100.0f);
}

void shakeSection() {
    // Exactly one close edge per Turn: that tick runs setBodyCollision(true).
    int edges = 0;
    TurnClock prev = turnClock(0.0f);
    for (int i = 1; i <= 30 * 12; ++i) {
        const TurnClock now = turnClock(float(i) / 30.0f);
        if (!prev.closed && now.closed) ++edges;
        prev = now;
    }
    CHECK(edges == 1);
    const ReactionOut purple = shakeReaction(TargetKind::PurplePikmin);
    CHECK(purple.kind == Reaction::Flick);
    CHECK(purple.knockback == kShakeKnockback && purple.damage == kShakeDamage);
    CHECK(!purple.leaf);
    const ReactionOut other = shakeReaction(TargetKind::Pikmin);
    CHECK(other.kind == Reaction::Wither && other.leaf);
}

void flickSection() {
    // The hand hits captains: Navi flick with fp24 attack damage.
    const ReactionOut navi = flickReaction(TargetKind::Navi);
    CHECK(navi.kind == Reaction::NaviFlick && navi.damage == kAttackDamage);
    const ReactionOut purple = flickReaction(TargetKind::PurplePikmin);
    CHECK(purple.kind == Reaction::Flick && purple.damage == kShakeDamage);
    const ReactionOut red = flickReaction(TargetKind::Pikmin);
    CHECK(red.kind == Reaction::Wither && red.leaf);
    // attack_2 key windows 26-32, 38-50, 57-65.
    CHECK(armWindow(28.0f) && armWindow(40.0f) && armWindow(60.0f));
    CHECK(!armWindow(20.0f) && !armWindow(33.0f) && !armWindow(52.0f) && !armWindow(70.0f));
    // The arm sweeps in front, not behind.
    CHECK(inArmArc(0.0f, 120.0f, 0.0f));
    CHECK(!inArmArc(0.0f, -120.0f, 0.0f));
}
// P1 PikiPressedState::exec (pikiState.cpp:3133): a pressed Pikmin dies on
// its first tick iff health <= 0 after the press damage; otherwise it recovers.
bool p1PressKills(float health, float damage) { return health - damage <= 0.0f; }

void crushLethalSection() {
    // P2 kills every pressed Pikmin, whatever its maturity/health.
    for (float health : {1.0f, 10.0f, 20.0f, 40.0f, 100.0f})
        CHECK(p1PressKills(health, pressDamage(true, health)));
    // The old fp24-only press left a 20 HP flower Pikmin alive (the r4 bug).
    CHECK(!p1PressKills(20.0f, kAttackDamage));
    // A Navi keeps the source fp24 press damage.
    CHECK(pressDamage(false, 100.0f) == kAttackDamage);
}

void flickDirSection() {
    // Victim in front (+z) and to the right (+x): pushed further away.
    const float dxs[] = {0.0f, 120.0f, -80.0f, 60.0f};
    const float dzs[] = {120.0f, 0.0f, 50.0f, -90.0f};
    for (int i = 0; i < 4; ++i) {
        const float a = flickAngle(dxs[i], dzs[i]);
        const float vx = -std::sin(a), vz = -std::cos(a);
        CHECK(vx * dxs[i] + vz * dzs[i] > 0.0f);
    }
    // Navi hand hit: the flat 300 push of InteractWind::actNavi.
    CHECK(flickReaction(TargetKind::Navi).knockback == 300.0f);
}

void rollFinishSection() {
    // No finish: loops 50..100 forever.
    const AttackClock loop = attackClock(20.0f, -1.0f);
    CHECK(!loop.tail && !loop.finished && loop.frame >= 50.0f && loop.frame < 100.0f);
    // finishMotion at 15 s (frame 450): the loop wraps at 450 (100 + 7*50),
    // then the uncurl tail 100..139 plays and END finishes.
    const AttackClock before = attackClock(14.9f, 15.0f);
    CHECK(!before.tail);
    const AttackClock tail = attackClock(15.0f + 20.0f / kFps, 15.0f);
    CHECK(tail.tail && !tail.finished && std::fabs(tail.frame - 120.0f) < 0.5f);
    const AttackClock done = attackClock(15.0f + 40.0f / kFps, 15.0f);
    CHECK(done.tail && done.finished);
    // A finish requested mid-pass runs that pass out first.
    const AttackClock mid = attackClock(15.2f, 15.1f);
    CHECK(!mid.tail);
}

void turnDeathSection() {
    // Health 0 at 2.0 s (frame 60, inside the loop): finishMotion -> the pass
    // ends at LOOP_END 81, the tail plays, key 3 and END are reached long
    // before FLIP_TIME would have allowed.
    const TurnClock atDeath = turnClock(2.0f, 2.0f);
    CHECK(atDeath.looping && !atDeath.finished);
    const TurnClock tail = turnClock(3.2f, 2.0f);   // frame 96 -> tail 81 + 15
    CHECK(tail.tail && !tail.finished);
    const TurnClock end = turnClock(4.2f, 2.0f);
    CHECK(end.finished && end.closed);
    // Without a death the same time is still inside the loop.
    CHECK(turnClock(4.2f).looping);
}
} // namespace

// CLIP_TABLE: state -> clip (DangoMushiState.cpp anim ids). Pre-fix the crab sat
// in Stay on a LOOPING fly (entrance) clip: "falling in from above over and over".
void clipTableSection() {
    CHECK(std::strcmp(stateClip("stay"), "wait") == 0);
    CHECK(std::strcmp(stateClip("appear"), "fly") == 0);
    CHECK(std::strcmp(stateClip("wait"), "wait") == 0);
    CHECK(std::strcmp(stateClip("move"), "move") == 0);
    CHECK(std::strcmp(stateClip("attack"), "attack") == 0);
    CHECK(std::strcmp(stateClip("turn"), "turn") == 0);
    CHECK(std::strcmp(stateClip("recover"), "recover") == 0);
    CHECK(std::strcmp(stateClip("flick"), "attack_2") == 0);
    CHECK(std::strcmp(stateClip("dead"), "dead") == 0);
    CHECK(stateClip("bogus") == nullptr);
    CHECK(clipLoops("wait"));
    CHECK(clipLoops("move"));
    CHECK(!clipLoops("fly"));
    CHECK(!clipLoops("attack"));
    CHECK(!clipLoops("turn"));
    CHECK(!clipLoops("recover"));
    CHECK(!clipLoops("attack_2"));
    CHECK(!clipLoops("dead"));
    // The only state that may play the entrance clip is Appear.
    const char* const states[] = {"stay", "wait", "move", "attack", "turn", "recover", "flick", "dead"};
    for (const char* st : states) CHECK(std::strcmp(stateClip(st), "fly") != 0);
}

// ROLL_REACH: the roll crush reaches ball radius (60) + the target's own size,
// not the flat 100 from the body centre that hit captains who were not touching.
void rollReachSection() {
    PressCrush crush(60.0f, 0.5f);
    auto at = [](std::uint64_t token, float dist, float reach) {
        PressCandidate c;
        c.token = token;
        c.dx = dist;
        c.grounded = true;
        c.reach = reach;
        return c;
    };
    CHECK(crush.shouldPress(at(1, 65.0f, 10.0f), 0.0f));   // inside 60 + 10
    CHECK(!crush.shouldPress(at(2, 75.0f, 10.0f), 0.0f));  // outside: the old radius 100 hit this
    CHECK(!crush.shouldPress(at(3, 99.0f, 10.0f), 0.0f));
    CHECK(crush.shouldPress(at(4, 69.0f, 10.0f), 0.0f));
}

int main() {
    section("DANGOMUSHI_WALL", wallSection);
    section("DANGOMUSHI_PRESS", pressSection);
    section("DANGOMUSHI_TURN_WINDOW", turnSection);
    section("DANGOMUSHI_SHAKE", shakeSection);
    section("DANGOMUSHI_FLICK", flickSection);
    section("DANGOMUSHI_CRUSH_LETHAL", crushLethalSection);
    section("DANGOMUSHI_FLICK_DIR", flickDirSection);
    section("DANGOMUSHI_ROLL_FINISH", rollFinishSection);
    section("DANGOMUSHI_TURN_DEATH", turnDeathSection);
    section("DANGOMUSHI_CLIP_TABLE", clipTableSection);
    section("DANGOMUSHI_ROLL_REACH", rollReachSection);
    if (gFailures) {
        std::printf("FAIL DANGOMUSHI_POLICY failures=%d\n", gFailures);
        return 1;
    }
    std::puts("PASS DANGOMUSHI_POLICY");
    return 0;
}
