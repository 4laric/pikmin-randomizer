// Engine-free regression for the Emperor Bulblax (KingChappy 53) life-cycle rules
// (pc_port/pc_p2_king_life.h): clip map, loop wrap, burrow gate, proximity wake,
// cross-Emperor request, bomb eligibility and stun clock, tongue-tip table and the
// Attack/Eat exits. Each section pins a rule to the decomp lines cited in the header.
#include "pc_p2_king_life.h"

#include <cmath>
#include <cstdio>
#include <cstring>

namespace {
int gFailures = 0;
int gSectionFailures = 0;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            ++gFailures;                                                 \
            ++gSectionFailures;                                          \
            std::printf("  FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); \
        }                                                                \
    } while (0)
void section(const char* name, void (*fn)())
{
    gSectionFailures = 0;
    fn();
    std::printf("%s %s\n", gSectionFailures ? "FAIL" : "PASS", name);
}
bool near(float a, float b, float eps = 1e-3f) { return std::fabs(a - b) <= eps; }

using namespace p2kinglife;

void clips()
{
    // KingChappy.h:319-333 AnimID -> stem (the comments name 'cry', 'move1', 'type1..3', 'wait2', 'waitact1/2').
    CHECK(!std::strcmp(clipStem(Walk), "move1"));
    CHECK(!std::strcmp(clipStem(Attack), "attack"));
    CHECK(!std::strcmp(clipStem(Dead), "dead"));
    CHECK(!std::strcmp(clipStem(Flick), "flick"));
    CHECK(!std::strcmp(clipStem(WarCry), "cry"));
    CHECK(!std::strcmp(clipStem(Damage), "damage"));
    CHECK(!std::strcmp(clipStem(Turn), "waitact1"));
    CHECK(!std::strcmp(clipStem(Eat), "type2"));
    CHECK(!std::strcmp(clipStem(Hide), "dive"));
    CHECK(!std::strcmp(clipStem(HideWait), "wait2"));
    CHECK(!std::strcmp(clipStem(Appear), "type3"));
    CHECK(!std::strcmp(clipStem(Caution), "waitact2"));
    CHECK(!std::strcmp(clipStem(Swallow), "type1"));
}

void loops()
{
    // move1 80 frames, loop 15..54: linear to the loop end, then wrap to 15.
    CHECK(near(clipFrame("move1", 10.0f, 80, false), 10.0f));
    CHECK(near(clipFrame("move1", 53.0f, 80, false), 53.0f));
    CHECK(near(clipFrame("move1", 54.0f, 80, false), 15.0f));
    CHECK(near(clipFrame("move1", 60.0f, 80, false), 21.0f));
    CHECK(near(clipFrame("move1", 54.0f + 39.0f * 3.0f + 4.0f, 80, false), 19.0f));
    // The buried idle loops the whole clip; it never freezes on its last pose.
    CHECK(near(clipFrame("wait2", 41.0f, 40, false), 2.0f));
    // damage loops 65..94 until finishMotion, then plays out to the end.
    CHECK(near(clipFrame("damage", 100.0f, 135, false), 65.0f + std::fmod(35.0f, 29.0f)));
    CHECK(near(clipFrame("damage", 100.0f, 135, true), 100.0f));
    CHECK(near(clipFrame("damage", 500.0f, 135, true), 134.0f));
    // A clip without loop bounds plays once and holds its last frame.
    CHECK(near(clipFrame("type3", 90.0f, 75, false), 74.0f));
    CHECK(near(clipFrame("attack", 30.0f, 95, false), 30.0f));
}

void burrow()
{
    CHECK(underground(Hide) && underground(HideWait) && underground(Appear));
    CHECK(!underground(Walk) && !underground(Caution) && !underground(Attack) && !underground(Dead));
    // EB_LifegaugeVisible: off in HideWait.init, back on at Appear END (Caution onward).
    CHECK(lifeGaugeHidden(HideWait) && lifeGaugeHidden(Appear));
    CHECK(!lifeGaugeHidden(Hide) && !lifeGaugeHidden(Caution) && !lifeGaugeHidden(Walk));
    CHECK(p2king::entryState() == HideWait);   // kingChappy.cpp:107
}

void wake()
{
    // Disc values: fp02 60, ip02 0.
    CHECK(near(WakeRange, 60.0f));
    CHECK(WakeDelayFrames == 0);
    WakeInputs in;
    in.doCheckAppear = true;
    in.framesInState = 1;
    in.naviInRange = true;
    CHECK(hideWaitWakes(in));
    in.naviInRange = false;
    in.pikminInRange = true;
    CHECK(hideWaitWakes(in));
    in.pikminInRange = false;
    CHECK(!hideWaitWakes(in)); // nobody near: stays buried
    // After the first Appear mDoCheckAppear is false: the test needs the timer past ip02.
    in.doCheckAppear = false;
    in.pikminInRange = true;
    in.framesInState = 0;
    CHECK(!hideWaitWakes(in));  // timer not past ip02 (0 > 0 is false)
    in.framesInState = 1;
    CHECK(hideWaitWakes(in));   // timer 1 > ip02 0
    // isThereOlimar / isTherePikmin compare squared distance strictly.
    CHECK(within(59.0f, 0.0f, 0.0f, 60.0f));
    CHECK(!within(60.0f, 0.0f, 0.0f, 60.0f));
    CHECK(within(30.0f, 30.0f, 30.0f, 60.0f));   // 3D: 51.96
    CHECK(!within(40.0f, 40.0f, 40.0f, 60.0f));  // 69.28
    CHECK(near(wakeRadius(1.0f), 60.0f));
    CHECK(near(wakeRadius(1.5f), 90.0f));        // big Emperor scale
    CHECK(near(wakeRadius(1.0f, 400.0f), 400.0f)); // smoke override
    CHECK(near(wakeRadius(1.0f, 0.0f), 60.0f));
    CHECK(AppearShakeFrame == 55);
    CHECK(near(p2king::AppearShakeOffRange, 100.0f) && near(p2king::AppearShakeOffPower, 200.0f));
}

void request()
{
    Peer peers[4];
    peers[0] = {Walk, true, 0.0f};        // the caller
    peers[1] = {HideWait, true, 0.0f};
    peers[2] = {Walk, true, 5.0f};
    peers[3] = {HideWait, true, 0.0f};
    // Appear: the first other Emperor that is buried.
    CHECK(requestState(peers, 4, 0, Appear) == 1);
    // WarCry: a walking one with a running flick timer.
    CHECK(requestState(peers, 4, 0, WarCry) == 2);
    peers[2].flickTimer = 0.0f;
    CHECK(requestState(peers, 4, 0, WarCry) == -1);   // forceTransit refuses a fresh walker
    // Skips the caller, dead and non-alive Emperors, and peers already in the state.
    peers[1].alive = false;
    CHECK(requestState(peers, 4, 0, Appear) == 3);
    peers[3].state = Dead;
    CHECK(requestState(peers, 4, 0, Appear) == -1);
    peers[3].state = Appear;
    CHECK(requestState(peers, 4, 0, Appear) == -1);
    // Only Appear and WarCry are forceable.
    CHECK(!forceAccepts({HideWait, true, 9.0f}, Attack));
    CHECK(!forceAccepts({Attack, true, 9.0f}, WarCry));
    CHECK(!forceAccepts({Walk, true, 1.0f}, Appear));
    // A lone Emperor asks nobody.
    CHECK(requestState(peers, 1, 0, Appear) == -1);
    CHECK(WarCryRequestFrame == 38);
}

void bombs()
{
    // P1 BombAI: Unk0 dormant (0), Unk1 thrown (1), Set lit (2), Bomb blast (3), Mizu (4), Die (5).
    CHECK(bombEatable(0, false));
    CHECK(bombEatable(2, false));
    CHECK(!bombEatable(1, false));
    CHECK(!bombEatable(3, false));
    CHECK(!bombEatable(4, false));
    CHECK(!bombEatable(5, false));
    CHECK(!bombEatable(0, true));   // held by a Pikmin
    CHECK(!bombEatable(2, true));
    CHECK(near(externalBlastDamage(100.0f), 25.0f));   // bombCallBack 0.25 x
    CHECK(near(mouthBombDamage(0), 0.0f));
    CHECK(near(mouthBombDamage(1), 200.0f));           // fp05
    CHECK(near(mouthBombDamage(3), 600.0f));
    CHECK(EatWindowStart == 40);
}

void stun()
{
    DamageClock c;
    int killStep = -1, stunStep = -1, endStep = -1, killCount = 0, stunCount = 0, maxLooped = 0;
    for (int step = 1; step < 2000 && endStep < 0; ++step) {
        const int ev = damageStep(c);
        if (ev & DEvKill) { killStep = step; ++killCount; }
        if (ev & DEvStun) { stunStep = step; ++stunCount; }
        if (!c.finished && c.frame > maxLooped) maxLooped = c.frame;
        if (ev & DEvEnd) endStep = step;
    }
    CHECK(killCount == 1 && stunCount == 1);
    CHECK(killStep == 15);                 // damage.bca 15:4 -> KEYEVENT_4
    CHECK(stunStep == 60);                 // damage.bca 60:6 -> KEYEVENT_6
    CHECK(maxLooped < DamageLoopEnd);      // never past the loop end while stunned
    // ip03 = 180: the timer starts at 1 on step 60, ++ each later step, > 180 finishes.
    // finishMotion at step 60 + 180 = 240; the clip then plays to frame 134.
    CHECK(endStep > 240);
    CHECK(endStep < 240 + 135);
    CHECK(c.finished && c.stun > 180);   // the timer keeps counting until the clip ends
    // A shorter stun (mutation guard for the ip03 constant) ends earlier.
    DamageClock d;
    int shortEnd = -1;
    for (int step = 1; step < 2000 && shortEnd < 0; ++step)
        if (damageStep(d, 10) & DEvEnd) shortEnd = step;
    CHECK(shortEnd > 0 && shortEnd < endStep);
    CHECK(near(p2king::bombDamage(2), 400.0f));
    CHECK(p2king::BombDamageTime == 180);
}

void tongue()
{
    using namespace p2kingtables;
    CHECK(kTongueFrames == 95);
    // bero6 (tip), model space, frame 0 (retail attack.bca): y 49.3, z 50.4.
    const Tongue t0 = tongueAt(0);
    CHECK(near(t0.tip[1], 49.294f, 0.01f) && near(t0.tip[2], 50.449f, 0.01f));
    for (int f = 0; f < kTongueFrames; ++f) {
        const Tongue t = tongueAt(f);
        const float len = std::sqrt(t.dir[0] * t.dir[0] + t.dir[1] * t.dir[1] + t.dir[2] * t.dir[2]);
        CHECK(near(len, 1.0f, 1e-3f));
        // On level ground the sphere base (tip.y) stays above the floor for the whole lick
        // (lowest 2.67 at frame 42), so the source trace only ends it on terrain rising
        // more than that ahead of the feet, or on a wall.
        CHECK(t.tip[1] > 2.0f);
    }
    // Clamped outside the clip.
    CHECK(near(tongueAt(-3).tip[1], tongueAt(0).tip[1]));
    CHECK(near(tongueAt(500).tip[2], tongueAt(94).tip[2]));
    // The tongue reaches out ahead of the mouth around frame 55 (z ~ 133).
    CHECK(tongueAt(55).tip[2] > 130.0f);
    CHECK(near(tongueAt(42).tip[1], 2.672f, 0.01f));
    CHECK(near(TongueSphereRadius, 5.0f) && near(TongueSphereLift, 5.0f));
}

void collision()
{
    using namespace p2kingtables;
    // Retail tree: root 'none' r80 and seven children; only head/hana/kuti are stickable.
    CHECK(kCollNodeCount == 8);
    CHECK(!std::strcmp(kCollNodes[0].id, "none") && near(kCollNodes[0].radius, 80.0f) && kCollNodes[0].parent == -1);
    int stickable = 0;
    for (int i = 1; i < kCollNodeCount; ++i) {
        CHECK(kCollNodes[i].parent == 0);
        if (!std::strcmp(kCollNodes[i].code, "st__")) {
            ++stickable;
            CHECK(!std::strcmp(kCollNodes[i].id, "head") || !std::strcmp(kCollNodes[i].id, "hana") ||
                  !std::strcmp(kCollNodes[i].id, "kuti"));
        }
    }
    CHECK(stickable == 3);
    CHECK(near(kCollNodes[5].radius, 30.0f) && near(kCollNodes[6].radius, 18.0f) && near(kCollNodes[7].radius, 22.0f));
    // Clip lookup and interpolation.
    CHECK(collClipIndex("move1") >= 0 && collClipIndex("dive") >= 0 && collClipIndex("wait2") >= 0);
    CHECK(collClipIndex("carry") == -1 && collClipIndex("nope") == -1);
    const int move = collClipIndex("move1");
    float a[3], b[3], m[3];
    CHECK(collCentre(move, 0.0f, 5, a));
    for (int k = 0; k < 3; ++k) CHECK(near(a[k], kCollClips[move].centre[0][5][k], 1e-4f));
    CHECK(collCentre(move, 1000.0f, 5, b));   // clamped to the last sample
    for (int k = 0; k < 3; ++k) CHECK(near(b[k], kCollClips[move].centre[kCollSamples - 1][5][k], 1e-4f));
    // Halfway between samples 0 and 1 is their mean.
    const float step = float(kCollClips[move].frames - 1) / float(kCollSamples - 1);
    CHECK(collCentre(move, 0.5f * step, 5, m));
    for (int k = 0; k < 3; ++k)
        CHECK(near(m[k], 0.5f * (kCollClips[move].centre[0][5][k] + kCollClips[move].centre[1][5][k]), 1e-3f));
    CHECK(!collCentre(-1, 0.0f, 0, m) && !collCentre(move, 0.0f, 8, m) && !collCentre(move, 0.0f, -1, m));
    // The head rides above the feet plane while walking (retail height), the mouth sits ahead of the root.
    CHECK(a[1] > 20.0f);
    float mouth[3];
    CHECK(collMouth(move, 0.0f, mouth) && mouth[2] > 10.0f);
    CHECK(!collMouth(99, 0.0f, mouth));
    // The buried idle keeps the stickable parts under the floor plane's reach of the stone-cold pose: the
    // dive ends with the head below its walking height.
    const int dive = collClipIndex("dive");
    float headStart[3], headEnd[3];
    CHECK(collCentre(dive, 0.0f, 5, headStart) && collCentre(dive, 1000.0f, 5, headEnd));
    CHECK(headEnd[1] < headStart[1]);
}

void exits()
{
    CHECK(attackExit(0, 0) == Walk);
    CHECK(attackExit(0, 3) == Swallow);
    CHECK(attackExit(2, 0) == Eat);
    CHECK(attackExit(1, 4) == Eat);   // bombs win: mEatenBombs is tested first
    CHECK(eatExit(true) == Damage);
    CHECK(eatExit(false) == Swallow);
    CHECK(crossed(54.0f, 55.0f, 55));
    CHECK(!crossed(55.0f, 56.0f, 55));
    CHECK(!crossed(50.0f, 54.9f, 55));
}
} // namespace

int main()
{
    section("CLIPS", clips);
    section("LOOPS", loops);
    section("BURROW", burrow);
    section("WAKE", wake);
    section("REQUEST", request);
    section("BOMBS", bombs);
    section("STUN", stun);
    section("TONGUE", tongue);
    section("COLLISION", collision);
    section("EXITS", exits);
    std::printf("%s p2_king_life_test failures=%d\n", gFailures ? "FAIL" : "PASS", gFailures);
    return gFailures ? 1 : 0;
}
