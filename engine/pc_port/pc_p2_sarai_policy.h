// Isolated source policy for Swooping Snitchbug (Sarai, enemy ID 23).
//
// Dependency-free contract transcribed from US GPVE01 rev 0
// native/pikmin2-research:
//   include/Game/Entities/Sarai.h            (FSM, parms, mouth slots)
//   src/plugProjectNishimuraU/Sarai.cpp      (setHeightVelocity, getNextStateOnHeight,
//                                             setRandTarget, fallMeckGround, catchTarget)
//   src/plugProjectNishimuraU/SaraiState.cpp (Attack/CatchFly/FallMeck/Fail exec)
//
// This header owns no engine state and performs no I/O. Hosts supply per-tick
// facts (carried Pikmin, body-latched attacker count, Purple latch, map height,
// random unit) and consume the returned decisions. It is the lane's first
// source-accuracy slice; it does not claim native actor registration, mouth
// attachment, animation playback or rendering.
#ifndef PC_P2_SARAI_POLICY_H
#define PC_P2_SARAI_POLICY_H

#include <cstdint>

namespace p2sarai {

// Sarai.h: mMouthSlots.alloc(2); each slot radius 15.0f ("rkamujnt"/"lkamujnt").
constexpr int kMouthSlots = 2;
constexpr float kMouthRadius = 15.0f;

constexpr float kPi = 3.14159265358979323846f;
constexpr float kDeg2Rad = kPi / 180.0f;

// Sarai.cpp setHeightVelocity(): MAX_PIKMIN_STUCK_FACTOR 5, and the payoff
// interpolation indexes 0..4 (getNextStateOnHeight()).
constexpr int kMaxWeightFactor = 5;
constexpr int kMaxPayoffIndex = 4;

// Sarai.h ProperParms defaults (retail asset values override at runtime).
struct Parms {
    float normalFlightHeight = 100.0f;   // fp01
    float grabFlightHeight = 80.0f;      // fp02
    float stateTransitionHeight = 50.0f; // fp03
    float normalMovementSpeed = 100.0f;  // fp04
    float grabMovementSpeed = 75.0f;     // fp05
    float waitTime = 3.0f;               // fp06
    float climbingFactor0 = 1.5f;        // fp11
    float climbingFactor5 = 1.0f;        // fp12
    float payoffProbability1 = 0.1f;     // fp21
    float payoffProbability5 = 0.7f;     // fp22
    float strugglingTime = 3.0f;         // fp23
    float huntDescentFactor = 0.3f;      // fp31
    float postHuntDecayRate = 0.95f;     // fp32
    float fallMeckSpeed = 200.0f;        // fp41
};

// getStickPikminNum(): body-latched Pikmin exclude the mouth-carried captives.
inline int stickPikminNum(int bodyStuckCount, int mouthCarried)
{
    return bodyStuckCount - mouthCarried;
}

// setHeightVelocity() climb factor: lerp(climbingFactor0, climbingFactor5, w/5)
// where w = clamp(bodyStuckCount, 0, 5). Returns the factor only; the vertical
// velocity also scales the height error (mapY + flightHeight - positionY).
inline float climbingFactor(const Parms& parms, int bodyStuckCount)
{
    int weight = bodyStuckCount < 0 ? 0 : (bodyStuckCount <= kMaxWeightFactor ? bodyStuckCount : kMaxWeightFactor);
    const float f = float(kMaxWeightFactor);
    const float w = float(weight);
    return ((f - w) / f) * parms.climbingFactor0 + (w / f) * parms.climbingFactor5;
}

// setHeightVelocity(): positive means "rise toward mapY + flightHeight".
inline float heightVelocity(const Parms& parms, int bodyStuckCount, bool carrying,
                            float mapY, float positionY)
{
    const float flightHeight = carrying ? parms.grabFlightHeight : parms.normalFlightHeight;
    return climbingFactor(parms, bodyStuckCount) * ((mapY + flightHeight) - positionY);
}

// setHeightVelocity() also returns the current altitude above the map.
inline float altitude(float mapY, float positionY) { return positionY - mapY; }

// getNextStateOnHeight(): source payoff/escape decision while CatchFly climbs.
enum class HeightDecision : std::uint8_t { None, Fall, Flick };

// randomUnit must be in [0, 1) (host randWeightFloat(1.0f)).
inline HeightDecision nextStateOnHeight(const Parms& parms, float health, int mouthCarried,
                                        int bodyStuckCount, bool purpleLatched, float randomUnit)
{
    if (health <= 0.0f) return HeightDecision::Fall;

    // Source: if (stuckPiki) { ... } return NULL. bodyStuckCount >= mouthCarried
    // holds in the source, so a non-positive value means "no body attackers".
    const int stuckPiki = stickPikminNum(bodyStuckCount, mouthCarried);
    if (stuckPiki <= 0) return HeightDecision::None;
    if (purpleLatched) return HeightDecision::Fall;

    int index = stuckPiki - 1;
    if (index < 0) index = 0;
    if (index > kMaxPayoffIndex) index = kMaxPayoffIndex;

    const float f = float(kMaxPayoffIndex);
    const float v = float(index);
    const float fallChance = ((f - v) / f) * parms.payoffProbability1 + (v / f) * parms.payoffProbability5;
    return randomUnit < fallChance ? HeightDecision::Flick : HeightDecision::Fall;
}

// setRandTarget(): radius selection. randomUnit is in [0, 1).
inline float randTargetRadius(const Parms& /*parms*/, float homeRadius, float territoryRadius,
                              bool carrying, bool inCave, float randomUnit)
{
    if (carrying) return homeRadius * randomUnit;
    if (inCave) return 50.0f + 50.0f * randomUnit;
    return homeRadius + (territoryRadius - homeRadius) * randomUnit;
}

// fallMeckGround(): the released captive receives this downward velocity.
inline float fallMeckVelocity(const Parms& parms) { return -parms.fallMeckSpeed; }

// Attack (SaraiState.cpp): catchTarget() is only called once frame > 16.0f.
constexpr float kCatchFrameThreshold = 16.0f;
inline bool attackMayCatch(float motionFrame) { return motionFrame > kCatchFrameThreshold; }

// Attack/CatchFly/Fail transition decisions, symbolic (numeric KEYEVENT values
// are engine-defined and intentionally not hard-coded here).
enum class AttackExit : std::uint8_t { None, Fail, CatchFly, Move };

inline AttackExit attackExit(bool atFailEvent, bool atEnd, bool caught)
{
    if (atFailEvent && !caught) return AttackExit::Fail;
    if (atEnd) return caught ? AttackExit::CatchFly : AttackExit::Move;
    return AttackExit::None;
}

// CatchFly escape trigger: height above the transition height, or a stuck
// general timer, or the motion END. Returns true when the host should ask
// nextStateOnHeight() for the next state.
inline bool catchFlyReadyForHeightDecision(float heightAboveMap, float generalTimer,
                                           const Parms& parms, bool atEnd)
{
    if (heightAboveMap > parms.stateTransitionHeight || generalTimer > 3.0f || atEnd) return true;
    return false;
}

// --- getAttackableTarget() geometry (Sarai.cpp) ------------------------------
//
// The source only scans while Sarai is inside its territory, then admits a
// candidate that is alive, a Pikmin, not already mouth-stuck, not stuck to this
// Sarai, and standing on a floor triangle, within the view half-angle and the
// sight radius. `viewHalfAngle` transcribes the source expression verbatim
// (`PI * (DEG2RAD * mViewAngle)`).
struct TargetCandidate {
    bool alive = true;
    bool isPikmin = true;
    bool stickToMouth = false;
    bool stickerIsSelf = false;
    bool floorTriangle = true;
    float angleRad = 0.0f;      // getAngDist(candidate)
    float sqrDistXZ = 0.0f;     // squared XZ distance to Sarai
};

struct TargetQuery {
    float sqrDistToHome = 0.0f;
    float territoryRadius = 0.0f;
    float viewAngleDeg = 0.0f;  // mViewAngle
    float sightRadius = 0.0f;   // mSightRadius
};

inline float viewHalfAngle(float viewAngleDeg) { return kPi * (kDeg2Rad * viewAngleDeg); }

inline bool targetable(const TargetQuery& query, const TargetCandidate& candidate)
{
    if (query.sqrDistToHome >= query.territoryRadius * query.territoryRadius) return false;
    if (!candidate.alive || !candidate.isPikmin || candidate.stickToMouth
        || candidate.stickerIsSelf || !candidate.floorTriangle) {
        return false;
    }
    if (candidate.angleRad > viewHalfAngle(query.viewAngleDeg)
        || -candidate.angleRad > viewHalfAngle(query.viewAngleDeg)) {
        return false;
    }
    if (candidate.sqrDistXZ >= query.sightRadius * query.sightRadius) return false;
    return true;
}

} // namespace p2sarai

#endif
