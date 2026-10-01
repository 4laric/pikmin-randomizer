#pragma once
#include <cmath>

// Engine-free source policy for the Mitite (TamagoMushi, EnemyID 68), issue #992
// (owner playtest 2026-09-30). Source: src/plugProjectMorimuraU/tamagoMushi.cpp,
// tamagoMushiState.cpp, tamagoMushiMgr.cpp at research revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail GPVE01 rev 0 enemyparm.txt
// (proper fp01 survival 180, fp02 appearance range 120, fp03 honey 1, ip01/ip02
// walk 25..80 ticks, ip03/ip04 appearance 20..90 ticks; general fp06 speed 100,
// fp09 territory 120, fp24 attack power 0).
//
// What the source says the creature is: a hidden swarm that bursts out when found.
// A Mitite starts in StateAppear, invisible and non-colliding (setAtari(false),
// setAlive(false), stopMotion on the appear clip). When a Pikmin or captain comes
// within the appearance range the LEADER calls createFellow (Mgr::createGroup with
// count 10, so nine more), each member waits a random 20..90 ticks, then all
// emerge; at the appear clip's KEYEVENT_2 the leader astonishes every Pikmin
// within 150 units (appearPanic). Afterwards any Pikmin that touches a Mitite, or
// damages one, is astonished too (InteractAstonish -> PikiPanicState,
// PIKIPANIC_Panic: freeze, notice, panic-run for the Pikmin panic time, then walk
// again). Nothing damages or kills a Pikmin; the threat is the panic scatter.
// After 0.8..1.0 x 180 ticks of walking the member dives (StateHide) and is killed.
namespace p2tamagopolicy {

constexpr float TickSeconds = 1.0f / 30.0f; // P2 update tick (one tick per frame)

constexpr int GroupCount = 10;              // Obj::createFellow -> createGroup(this, 10, false)
constexpr int EggGroupCount = 10;           // egg.cpp EGGDROP_Mitites
constexpr int BigFootGroupCount = 30;       // TAMAGOMUSHI_GROUP_COUNT, Raging Long Legs drop
constexpr float AppearRange = 120.0f;       // proper fp02 (disc), isFound search radius
constexpr float PanicRadius = 150.0f;       // Parms::mPanicInduceRadius, appearPanic
constexpr float SurvivalTicks = 180.0f;     // proper fp01 (disc)
constexpr int WalkMinTicks = 25;            // ip01
constexpr int WalkMaxTicks = 80;            // ip02
constexpr int AppearMinTicks = 20;          // ip03
constexpr int AppearMaxTicks = 90;          // ip04
constexpr float Territory = 120.0f;         // general fp09
constexpr float MoveSpeed = 100.0f;         // general fp06
constexpr float GroundSpread = 45.0f;       // createGroup distanceOffsetFactor
constexpr float ContactRadius = 28.0f;      // coll root r18 + Pikmin contact fp34 10
constexpr float AppearEventSeconds = 2.0f / 30.0f; // `set` KEYEVENT_2 frame 2

// Obj::onInit: mActiveMaxTime = (0.8 + 0.2 rand) * survival.
inline float activeMaxTicks(float rand01) { return (0.8f + 0.2f * rand01) * SurvivalTicks; }
inline bool shouldHide(float activeTicks, float activeMax) { return activeTicks > activeMax; }

// StateWalk::init / StateAppear::init random tick windows (max parm is absolute).
inline float randomTicks(int minTicks, int maxTicks, float rand01)
{
    return float(maxTicks - minTicks) * rand01 + float(minTicks);
}
inline float walkSeconds(float rand01) { return randomTicks(WalkMinTicks, WalkMaxTicks, rand01) * TickSeconds; }
inline float appearDelaySeconds(float rand01)
{
    return randomTicks(AppearMinTicks, AppearMaxTicks, rand01) * TickSeconds;
}

// Obj::isFound: nearest Pikmin or navi inside the appearance radius (XZ).
inline bool isFound(bool pikminInRange, bool naviInRange) { return pikminInRange || naviInRange; }
inline bool withinAppearRange(float distanceXZ) { return distanceXZ < AppearRange; }

// Mgr::createGroup(leader, count, false): ground birth offsets.
struct Offset {
    float x, z, faceDir;
};
inline Offset fellowOffset(int i, int count, float rand01)
{
    const float tau = 6.28318531f;
    const float radius = 0.8f * rand01 + 0.2f;
    float face = tau * float(i) / float(count);
    Offset o;
    o.x = radius * GroundSpread * std::sin(face);
    o.z = radius * GroundSpread * std::cos(face);
    if (i % 2 == 1) face = -face;
    o.faceDir = face;
    return o;
}
inline int fellowCount(int groupCount) { return groupCount > 1 ? groupCount - 1 : 0; }
// Mgr::createGroup(BirthArg, ...) refuses when the pool cannot hold the group.
inline bool poolHoldsGroup(int freeSlots, int groupCount) { return freeSlots >= groupCount; }

// InteractAstonish eligibility (interactPiki.cpp:473, tamagoMushi.cpp:222-228,
// 247-251): the Pikmin must not be Purple, invincible or already panicking or in
// flight. Piki state ids mirror include/PikiState.h (engine-free duplicates).
enum PikiStateId {
    StGrow = 1, StBury = 2, StNukare = 3, StNukareWait = 4, StAutoNuki = 5,
    StDying = 6, StDead = 7, StSwallowed = 8, StBubble = 10,
    StFlying = 14, StEmit = 15, StDrown = 24, StFlown = 25,
    StPressed = 33, StDenkiDying = 35, StPanic = 36
};
inline bool stateAstonishable(int state)
{
    switch (state) {
    case StGrow: case StBury: case StNukare: case StNukareWait: case StAutoNuki:
    case StDying: case StDead: case StSwallowed: case StBubble: case StFlying:
    case StEmit: case StDrown: case StFlown: case StPressed: case StDenkiDying:
    case StPanic:
        return false;
    default:
        return true;
    }
}
inline bool astonishAccepts(bool alive, bool purple, int state)
{
    return alive && !purple && stateAstonishable(state);
}
// The Pikmin panic then runs for PikiParms p055 panicMaxTime (3 s) x 1.0..1.1; the
// InteractAstonish argument (mPikiPanicMaxTime 30) is stored but not used by
// actPiki, so the scatter lasts seconds, not thirty.
constexpr float PikminPanicSeconds = 3.0f;

// Harm: none. The Mitite has attack power 0 and no bite; it scares Pikmin only.
struct PikminEffect {
    bool damages;
    bool scares;
};
inline PikminEffect pikminEffect() { return {false, true}; }

} // namespace p2tamagopolicy
