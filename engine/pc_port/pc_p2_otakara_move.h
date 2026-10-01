#pragma once
// Engine-free OtakaraBase move decision (#884) shared by pc_p2_otakara.cpp and
// tools/p2_otakara_move_test.cpp. Encodes the P2 source decision logic
// (pikmin2-research @ 632af93787b9c95b63f0c13be32b161375ce3a96):
//   * OtakaraBase::Obj::isMovePositionSet  (OtakaraBase.cpp:361-389)
//       treasure target -> destination = treasure position (pursuit);
//       creature target -> destination = getTargetPosition(target) (escape).
//   * OtakaraBase::Obj::getTargetPosition  (OtakaraBase.cpp:424-444)
//       one moveSpeed step AWAY from the creature, projected onto the home
//       territory circle when it would leave it.
//   * EnemyFunc::getNearestPikminOrNavi    (enemyAction.cpp:746-762, :17-61, :368-400)
//       nearest navi then a strictly-closer searchable piki; view angle fp13=180
//       (full circle); ConditionNotStickClientAndItem (ConditionNotStick.h:28-46)
//       and Piki::isSearchable (Piki.h:243-251) filter the piki.
//   * StateWait/Move/Turn/Flick::exec      (OtakaraBaseState.cpp:89-136,165-199,225-269,297-334)
//       THIRD_PI facing gate, Flick then Dead override, commit at KEYEVENT_END.
//   * EnemyBase::turnToTarget              (EnemyBase.h:463-471), walkToTarget
//       (enemyAction.cpp:2102-2107).
//   * EnemyFunc::isStartFlick              (enemyAction.cpp:1209-1244)
//       hit count (mFlickTimer, +1 per addDamage, OtakaraBase.cpp:563-574 /
//       enemyBase.cpp:2762-2773) against the ip01-ip07 thresholds keyed on the stuck
//       Pikmin count; reset by Flick event 2 (OtakaraBaseState.cpp:107).
// BombOtakara (93) chases its target (StateBombMove, OtakaraBaseState.cpp:812-848),
// so it uses Mode::Pursue and is never inverted. Its chase runs a 1.5 s fuse
// (stimulateBomb, OtakaraBase.cpp:699-707) and keeps the port territory bound
// (pursuePosition).
#include <cmath>

namespace p2otakaramove {

struct Vec2 {
    float x, z;
};

constexpr float kPi = 3.14159265f;
constexpr float kTwoPi = 6.28318531f;
constexpr float kFacingGate = 1.04719755f; // THIRD_PI, OtakaraBaseState.cpp:125/172/232/305
constexpr float kTurnFactor = 0.25f;       // fp08 turn speed (retail)
constexpr float kMaxTurnDeg = 4.0f;        // fp28 max turn angle per source tick (retail)
constexpr float kViewAngleDeg = 180.0f;    // fp13 view angle (retail): full circle
constexpr float kSourceHz = 30.0f;         // assumed source tick rate (unverified, design 2.6)

enum class Mode { Escape, Pursue };
enum class TargetKind { None, Creature, Treasure };

struct Candidate {
    Vec2 pos;
    bool isNavi;
    bool alive;
    bool stuckToSelf;  // ConditionNotStickClientAndItem: mSticker == this dweevil
    bool stuckToMouth; // Piki::isSearchable: !isStickToMouth()
};

inline float distSqXZ(Vec2 a, Vec2 b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}
inline float distXZ(Vec2 a, Vec2 b) { return std::sqrt(distSqXZ(a, b)); }

inline float wrapPi(float a) {
    while (a > kPi) a -= kTwoPi;
    while (a < -kPi) a += kTwoPi;
    return a;
}

// angXZ(dest, self) (trig.h:79-83): atan2(dx, dz).
inline float headingTo(Vec2 self, Vec2 dest) { return std::atan2(dest.x - self.x, dest.z - self.z); }

// getNearestPikminOrNavi: nearest navi within sight (strict <), then a piki must be
// strictly closer than the navi (shared targetDist). The view angle is a full circle,
// so no angle test is needed. Returns the candidate index or -1.
inline int selectThreat(const Candidate* c, int n, Vec2 self, float sight) {
    const float sightSq = sight * sight;
    float best = sightSq;
    int pick = -1;
    for (int i = 0; i < n; ++i) { // getNearestNavi (enemyAction.cpp:17-61)
        if (!c[i].isNavi || !c[i].alive) continue;
        const float d = distSqXZ(c[i].pos, self);
        if (d < best) { best = d; pick = i; }
    }
    for (int i = 0; i < n; ++i) { // getNearestPikmin (enemyAction.cpp:368-400)
        if (c[i].isNavi || !c[i].alive || c[i].stuckToMouth || c[i].stuckToSelf) continue;
        const float d = distSqXZ(c[i].pos, self);
        if (d < best) { best = d; pick = i; }
    }
    return pick;
}

// OtakaraBase::Obj::getTargetPosition (OtakaraBase.cpp:424-444). A zero separation
// normalises to zero (Vector3.h:636-648), so the destination is self.
inline Vec2 escapePosition(Vec2 self, Vec2 threat, Vec2 home, float moveSpeed, float territory,
                           bool* clamped = nullptr) {
    Vec2 sep{self.x - threat.x, self.z - threat.z};
    const float len = std::sqrt(sep.x * sep.x + sep.z * sep.z);
    if (len > 0.0f) {
        sep.x /= len;
        sep.z /= len;
    } else {
        sep = Vec2{0.0f, 0.0f};
    }
    sep.x = sep.x * moveSpeed + self.x;
    sep.z = sep.z * moveSpeed + self.z;
    bool clip = false;
    if (distSqXZ(sep, home) > territory * territory) {
        // Vector3f::getFlatDirectionFromTo(home, sep) (Vector3.h:230-235)
        Vec2 dir{sep.x - home.x, sep.z - home.z};
        const float dl = std::sqrt(dir.x * dir.x + dir.z * dir.z);
        if (dl > 0.0f) {
            dir.x /= dl;
            dir.z /= dl;
        }
        sep = Vec2{home.x + dir.x * territory, home.z + dir.z * territory};
        clip = true;
    }
    if (clamped) *clamped = clip;
    return sep;
}

// BombOtakara (93) chase destination. Source StateBombMove/StateBombTurn walk at the
// chase target with no territory rule (OtakaraBaseState.cpp:823-831, 887-897): the
// chase is bounded by the stimulateBomb fuse instead (bombFuseStep), and the source
// carrier is killed once its payload is gone (OtakaraBase.cpp:94-101 clears
// mTargetCreature; OtakaraBaseState.cpp:761-764/816-819/880-883 kill). The port
// carrier outlives its blast, so the port keeps the pre-#884 territory rule (old
// pc_p2_otakara.cpp:810-811) as its bound: once the body is outside the territory
// the destination is home (clamped=true), otherwise the target.
inline Vec2 pursuePosition(Vec2 self, Vec2 target, Vec2 home, float territory, bool* clamped = nullptr) {
    const bool out = distSqXZ(self, home) > territory * territory;
    if (clamped) *clamped = out;
    return out ? home : target;
}

// isMovePositionSet destination. Treasure -> treasure position (OtakaraBase.cpp:370-372,
// never produced at runtime: no treasure is staged); Creature+Escape -> getTargetPosition;
// Creature+Pursue -> pursuePosition (StateBombMove walkToTarget, OtakaraBaseState.cpp:823-831,
// plus the port territory bound).
inline Vec2 movePosition(Mode mode, TargetKind kind, Vec2 self, Vec2 target, Vec2 home, float moveSpeed,
                         float territory, bool* clamped = nullptr) {
    if (clamped) *clamped = false;
    switch (kind) {
    case TargetKind::Treasure:
        return target;
    case TargetKind::Creature:
        if (mode == Mode::Pursue) return pursuePosition(self, target, home, territory, clamped);
        return escapePosition(self, target, home, moveSpeed, territory, clamped);
    default:
        return self;
    }
}

// |angDist(angXZ(dest, self), faceDir)| <= THIRD_PI (OtakaraBaseState.cpp:170-172, 230-232).
inline bool facingWithinGate(float heading, Vec2 self, Vec2 dest) {
    return std::fabs(wrapPi(headingTo(self, dest) - heading)) <= kFacingGate;
}

// EnemyBase::turnToTarget (EnemyBase.h:463-471) per dt: clamp(angDist*turnSpeed,
// TORADIANS(maxTurnAngle)) per source tick, converted to dt at kSourceHz.
inline float turnStep(float heading, Vec2 self, Vec2 dest, float dt) {
    const float ticks = kSourceHz * dt;
    const float angDist = wrapPi(headingTo(self, dest) - heading);
    const float factor = 1.0f - std::pow(1.0f - kTurnFactor, ticks);
    const float maxTurn = kMaxTurnDeg * (kPi / 180.0f) * ticks;
    float step = angDist * factor;
    if (step > maxTurn) step = maxTurn;
    if (step < -maxTurn) step = -maxTurn;
    return wrapPi(heading + step);
}

// Retail ShakeOff thresholds ip01-ip07 (EnemyParmsBase.h:95-101; disc values
// 6/5/12/10/17/20/22 for every Otakara, docs/PIKMIN2_DWEEVIL_ASSETS.md:144,
// experimental/pikmin2_dweevil_assets.py:150-151).
struct ShakeOff {
    int blowA;     // ip01
    int sticking1; // ip02
    int blowB;     // ip03
    int sticking2; // ip04
    int blowC;     // ip05
    int sticking3; // ip06
    int blowD;     // ip07
};
constexpr ShakeOff kRetailShakeOff{6, 5, 12, 10, 17, 20, 22};

// EnemyFunc::isStartFlick(enemy, false) (enemyAction.cpp:1209-1244). flickTimer is the
// source mFlickTimer: +1.0 per addDamage (Otakara damageTreasure -> addDamage(damage,
// 1.0f), OtakaraBase.cpp:563-574; EB_FlickEnabled from EnemyBase::onInit,
// enemyBase.cpp:1074), reset to 0 by Flick event 2 (OtakaraBaseState.cpp:107).
// stuckCount is mStuckPikminCount (Pikmin stuck to this enemy). Rounded half away
// from zero and truncated to u8, as the source does.
inline bool isStartFlick(float flickTimer, int stuckCount, const ShakeOff& p = kRetailShakeOff) {
    const float flickVal = flickTimer >= 0.0f ? flickTimer + 0.5f : flickTimer - 0.5f;
    const int flickInt = int(static_cast<unsigned char>(int(flickVal)));
    if (stuckCount < p.sticking1) return flickInt > p.blowA;
    if (stuckCount < p.sticking2) return flickInt > p.blowB;
    if (stuckCount < p.sticking3) return flickInt > p.blowC;
    return flickInt > p.blowD;
}

// Obj::stimulateBomb (OtakaraBase.cpp:699-707), called each frame of StateBombMove/
// StateBombTurn (OtakaraBaseState.cpp:821, 885): the timer (mItemSearchDelayTimer,
// reset by StateBombWait::init, OtakaraBaseState.cpp:748) grows by dt and the payload
// is forced once it exceeds 1.5 s. Returns true when the bomb must be forced.
constexpr float kBombFuseSeconds = 1.5f;
inline bool bombFuseStep(float& timer, float dt) {
    timer += dt;
    return timer > kBombFuseSeconds;
}

enum class St { Dead, Flick, Wait, Move, Turn, Take, ItemWait, ItemMove, ItemTurn, ItemFlick, ItemDrop };

struct In {
    St cur;
    bool hasTarget;
    bool facing;
    bool flick;
    bool dead;
};

// The state requested this frame (mNextState). Returning `cur` means no request.
// Source priority: target decision, then Flick, then Dead override
// (OtakaraBaseState.cpp:165-199 / 225-269 / 297-334). A no-target Wait stays Wait:
// the source Wait has no idle transition.
inline St decide(const In& in) {
    St next = in.cur;
    switch (in.cur) {
    case St::Wait:
        if (in.hasTarget) next = in.facing ? St::Move : St::Turn;
        break;
    case St::Move:
        next = in.hasTarget ? (in.facing ? St::Move : St::Turn) : St::Wait;
        break;
    case St::Turn:
        next = in.hasTarget ? (in.facing ? St::Move : St::Turn) : St::Wait;
        break;
    default:
        break;
    }
    if (in.flick) next = St::Flick;
    if (in.dead) next = St::Dead;
    return next;
}

// StateFlick KEYEVENT_END (OtakaraBaseState.cpp:115-133).
inline St afterFlick(bool dead, bool hasTarget, bool facing) {
    if (dead) return St::Dead;
    if (hasTarget) return facing ? St::Move : St::Turn;
    return St::Wait;
}

// finishMotion -> KEYEVENT_END gate: a looped clip reaches its end when stateTime
// crosses a whole multiple of the clip duration.
inline bool clipEndCrossed(float prevStateTime, float stateTime, float clipDuration) {
    if (!(clipDuration > 0.0f)) return true;
    return std::floor(stateTime / clipDuration) > std::floor(prevStateTime / clipDuration);
}

} // namespace p2otakaramove
