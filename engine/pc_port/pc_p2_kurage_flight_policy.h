// Isolated source policy for the Lesser Spotted Jellyfloat (Kurage, enemy ID 57).
//
// Transcribed from US GPVE01 rev 0 native/pikmin2-research:
//   include/Game/Entities/Kurage.h       (states, parms, anim IDs)
//   src/plugProjectNishimuraU/Kurage.cpp (setHeightVelocity, pitch offsets,
//                                         updateFallTimer, getFlyingNextState,
//                                         getSearchedTarget, isSuck, suckPikmin)
//   src/plugProjectNishimuraU/KurageState.cpp (state transitions)
//
// Dependency-free: hosts supply per-tick facts and consume the returned
// numbers/decisions. The lane already has a bounded receiver/digestion host;
// this header adds the retrieved source flight and suction numeric contract.
#ifndef PC_P2_KURAGE_FLIGHT_POLICY_H
#define PC_P2_KURAGE_FLIGHT_POLICY_H

#include <cmath>
#include <cstdint>

namespace p2kurage {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 2.0f * kPi;
constexpr float kDeg2Rad = kPi / 180.0f;

// Shared-base selector for the two Jellyfloat species. `Lesser` is Kurage
// (enemy ID 57) and MUST remain bit-for-bit identical to the original policy;
// `Greater` is OniKurage (enemy ID 72), which shares every transition but uses
// different pitch amplitudes and keyframe offsets (OniKurage.cpp:301-421).
enum class Variant : std::uint8_t { Lesser, Greater };

constexpr float lesserMovePitchAmplitude = 50.0f;  // Kurage.cpp getMovePitchOffset
constexpr float greaterMovePitchAmplitude = 20.0f; // OniKurage.cpp getMovePitchOffset

// Kurage.h ProperParms defaults (retail asset values override at runtime).
struct Parms {
    float flightHeight = 90.0f;  // fp01
    float riseFactor = 1.0f;     // fp02
    float groundTime = 3.0f;     // fp10
    float suckTime = 5.0f;       // fp11
    float suckChance = 0.025f;   // fp12
    float shakeTime = 3.0f;      // fp04
    int minFallPiki = 10;        // ip01
    int maxSuckPiki = 10;        // ip11
};

// setHeightVelocity(): vertical velocity toward mapY + flightHeight + yOffset,
// scaled by (speedFactor + fp02). Returns the current altitude above the map.
inline float heightVelocity(const Parms& parms, float yOffset, float speedFactor,
                            float mapY, float positionY)
{
    return (speedFactor + parms.riseFactor) * ((yOffset + parms.flightHeight + mapY) - positionY);
}
inline float altitude(float mapY, float positionY) { return positionY - mapY; }

// Linear keyframe sampling shared by the pitch-offset helpers (source loops
// stop one segment before the final key, matching the decomp).
inline float keyframeOffset(const float* frames, const float* offsets, int segments, float frame)
{
    float value = 0.0f;
    for (int i = 0; i < segments; ++i) {
        const int j = i + 1;
        const float prevKey = frames[i];
        if (frame >= prevKey) {
            const float nextKey = frames[j];
            if (frame < nextKey) {
                const float factor = (frame - prevKey) / (nextKey - prevKey);
                value = factor * offsets[j] + (1.0f - factor) * offsets[i];
            }
        }
    }
    return value;
}

// getMovePitchOffset(): free-running sine driven by a separate timer.
inline float movePitchOffset(float& timer, float deltaTime, float amplitude)
{
    timer += deltaTime * kPi;
    if (timer > kTau) timer -= kTau;
    return amplitude * std::sin(timer);
}

// Legacy Kurage entry point (amplitude 50); preserved verbatim.
inline float movePitchOffset(float& timer, float deltaTime)
{
    return movePitchOffset(timer, deltaTime, lesserMovePitchAmplitude);
}

inline float attackPitchOffset(float motionFrame, Variant variant)
{
    static const float frames[7] = { 0.0f, 30.0f, 65.0f, 80.0f, 95.0f, 108.0f, 120.0f };
    static const float lesser[7] = { 0.0f, -20.0f, 15.0f, -30.0f, 0.0f, -25.0f, 0.0f };
    static const float greater[7] = { 0.0f, -30.0f, 30.0f, -50.0f, 0.0f, -40.0f, 0.0f };
    return keyframeOffset(frames, variant == Variant::Greater ? greater : lesser, 6, motionFrame);
}
inline float attackPitchOffset(float motionFrame) { return attackPitchOffset(motionFrame, Variant::Lesser); }

inline float flickPitchOffset(float motionFrame, Variant variant)
{
    static const float frames[7] = { 0.0f, 10.0f, 15.0f, 20.0f, 30.0f, 40.0f, 60.0f };
    static const float lesser[7] = { 0.0f, -50.0f, 50.0f, -50.0f, 20.0f, -20.0f, 0.0f };
    static const float greater[7] = { 0.0f, -80.0f, 80.0f, -100.0f, 30.0f, -50.0f, 0.0f };
    return keyframeOffset(frames, variant == Variant::Greater ? greater : lesser, 6, motionFrame);
}
inline float flickPitchOffset(float motionFrame) { return flickPitchOffset(motionFrame, Variant::Lesser); }

inline float takeOffPitchOffset(float motionFrame, Variant variant)
{
    static const float frames[5] = { 32.0f, 40.0f, 52.0f, 70.0f, 80.0f };
    static const float lesser[5] = { 0.0f, -45.0f, -60.0f, -10.0f, -10.0f };
    static const float greater[5] = { 0.0f, -50.0f, -60.0f, -10.0f, -10.0f };
    return keyframeOffset(frames, variant == Variant::Greater ? greater : lesser, 4, motionFrame);
}
inline float takeOffPitchOffset(float motionFrame) { return takeOffPitchOffset(motionFrame, Variant::Lesser); }

// getFallPitchOffset(): source scales the state timer by 30 then samples only
// the first four of eight segments (transcribed verbatim).
inline float fallPitchOffset(float stateTimer, Variant variant)
{
    const float frame = 30.0f * stateTimer;
    static const float frames[8] = { 7.0f, 17.0f, 27.0f, 37.0f, 47.0f, 57.0f, 67.0f, 77.0f };
    static const float lesser[8] = { -20.0f, -15.0f, -35.0f, -25.0f, -40.0f, -35.0f, -65.0f, 0.0f };
    static const float greater[8] = { -25.0f, -15.0f, -40.0f, -30.0f, -45.0f, -35.0f, -70.0f, 0.0f };
    return keyframeOffset(frames, variant == Variant::Greater ? greater : lesser, 4, frame);
}
inline float fallPitchOffset(float stateTimer) { return fallPitchOffset(stateTimer, Variant::Lesser); }

// updateFallTimer(): only accumulates while Pikmin are stuck to the body.
inline void updateFallTimer(int stuckPikminCount, float& fallTimer, float deltaTime)
{
    if (stuckPikminCount != 0) fallTimer += deltaTime;
    else fallTimer = 0.0f;
}

// getFlyingNextState()
enum class FlyingNext : std::uint8_t { Null, Dead, Fall, FlyFlick };

inline FlyingNext flyingNextState(const Parms& parms, float health, bool purpleStuck,
                                  float fallTimer, int stuckPikminCount)
{
    if (health <= 0.0f) return FlyingNext::Dead;
    if (purpleStuck) return FlyingNext::Fall;
    if (fallTimer > parms.shakeTime || stuckPikminCount >= parms.minFallPiki) {
        return stuckPikminCount < parms.minFallPiki ? FlyingNext::FlyFlick : FlyingNext::Fall;
    }
    return FlyingNext::Null;
}

// getSearchedTarget() / isSuck() vertical window: currY - offset - 50 < y < currY.
inline bool inSuctionWindow(float positionY, float offset, float candidateY)
{
    const float minY = positionY - offset - 50.0f;
    return candidateY > minY && candidateY < positionY;
}
inline float viewHalfAngle(float viewAngleDeg) { return kPi * (kDeg2Rad * viewAngleDeg); }

// getSearchedTarget() candidate admission (position-independent flags supplied
// by the host). Returns true when the candidate is a legal scan participant.
struct SearchCandidate {
    bool alive = true;
    bool isPikmin = true;
    bool stickerIsSelf = false;
    float y = 0.0f;
    float sqrDistXZ = 0.0f;
    float angleRad = 0.0f;  // getAngDist(candidate)
};

inline bool searchAdmit(float positionY, float offset, float viewAngleDeg, float sightRadius,
                        const SearchCandidate& candidate)
{
    if (!candidate.alive || !candidate.isPikmin || candidate.stickerIsSelf) return false;
    if (!inSuctionWindow(positionY, offset, candidate.y)) return false;
    if (candidate.sqrDistXZ >= sightRadius * sightRadius) return false;
    if (candidate.angleRad > viewHalfAngle(viewAngleDeg)
        || -candidate.angleRad > viewHalfAngle(viewAngleDeg)) {
        return false;
    }
    return true;
}
inline bool inAttackRange(float positionY, float offset, float maxAttackRange, float candidateY,
                          float candidateSqrDistXZ)
{
    if (!inSuctionWindow(positionY, offset, candidateY)) return false;
    return candidateSqrDistXZ < maxAttackRange * maxAttackRange;
}

// suckPikmin() admission: within mAttackRadius and the y window, under the cap,
// and passing the per-candidate fp12 chance roll.
inline bool suckAdmit(const Parms& parms, float positionY, float offset, float attackRadius,
                      float candidateY, float candidateSqrDistXZ, int suckedCount, float randomUnit)
{
    if (suckedCount >= parms.maxSuckPiki) return false;
    if (!(randomUnit < parms.suckChance)) return false;
    if (!inSuctionWindow(positionY, offset, candidateY)) return false;
    return candidateSqrDistXZ < attackRadius * attackRadius;
}

// OniKurage StateDrop::exec (OniKurageState.cpp:486): request finish when the
// body is within 25 units of the ground, is already rising, or has fallen for
// more than three seconds. Shared by the bounded host's Drop falling behaviour.
inline bool dropShouldFinish(float positionY, float mapY, float velocityY, float stateTimer)
{
    return (positionY - mapY) < 25.0f || velocityY > 0.0f || stateTimer > 3.0f;
}

// OniKurage suckNavi()/getSearchedTarget() treat living Navi (captains) as
// first-class targets in addition to Pikmin. The host supplies the flags; the
// policy only reports whether a captain is a legal scan participant.
inline bool naviSearchAdmit(bool alive, bool stickerIsSelf, float candidateY,
                            float positionY, float offset, float sqrDistXZ, float attackRange)
{
    if (!alive || stickerIsSelf) return false;
    if (!inSuctionWindow(positionY, offset, candidateY)) return false;
    return sqrDistXZ < attackRange * attackRange;
}

} // namespace p2kurage

#endif
