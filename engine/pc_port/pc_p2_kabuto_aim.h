#pragma once

// Kabuto 75 (Armored Cannon Beetle Larva) target search, attack lane and
// turn/move steering (#884 round 4). Engine-free: the campaign FSM
// (pc_p2_kabuto_fsm.cpp) feeds host snapshots in and applies the decisions;
// tools/p2_kabuto_stone_fleet_test.cpp and p2_kabuto_fsm_policy_test.cpp drive
// the same functions.
//
// Source (projectPiki/pikmin2, read-only checkout native/pikmin2-research):
//   Kabuto.cpp:212-220       getSearchedTarget: getNearestPikminOrNavi(this,
//                            getViewAngle(), sight) and alert reset.
//   Kabuto.cpp:226-262       isAttackableTarget: a Navi / Pikmin in the lane
//                            |dy| < fov, |ortho . diff| < 15,
//                            15 < dir . diff < sight.
//   Kabuto.cpp:296-318       updateCaution / getViewAngle (180 deg while the
//                            alert timer is below fp29, else fp13).
//   Kabuto.cpp:198-206       setRandTarget (wander target).
//   KabutoState.cpp:89-110   StateWait::exec (target seen or > 3 s -> Turn).
//   KabutoState.cpp:139-174  StateTurn::exec (turn to target; Attack only when
//                            isAttackableTarget; no target: turn to the wander
//                            target, Move once within 30 deg).
//   KabutoState.cpp:203-260  StateMove::exec (target -> Turn / Attack; no
//                            target: > 6 s or within 25 -> Wait, otherwise walk
//                            while facing within 30 deg, else Turn).
//   KabutoState.cpp:360-372  StateAttack end: Flick / Turn (target) / Wait.
//   KabutoState.cpp:306-311  StateFlick end -> Attack.
//   enemyAction.cpp:17-60,368-410,746-760 getNearestNavi / getNearestPikmin /
//                            getNearestPikminOrNavi.
//   EnemyBase.h:463-478      turnToTarget: step = clamp(angDist * turnSpeed,
//                            rad(maxTurnAngle)) per exec; trig.h:222
//                            isAngleWithin(angle, degrees).
// Retail Kabuto general parms (experimental/pikmin2_cannon_projectile_assets.py
// DISC_PARMS 'Kabuto', names from EnemyParmsBase.h:55-94): fp06 moveSpeed 60,
// fp08 turnSpeed 0.05, fp28 maxTurnAngle 5 deg, fp09 territory 150, fp10 home
// 30, fp12 sight 350, fp25 fov (visibility height) 100, fp13 viewAngle 90,
// fp29 alertDuration 15.

#include <cmath>

namespace p2kabutoaim {

constexpr float kPi = 3.14159265358979323846f;

struct Vec3 {
    float x = 0.0f, y = 0.0f, z = 0.0f;
};

struct Params {
    float moveSpeed = 60.0f;        // fp06
    float turnSpeed = 0.05f;        // fp08 (fraction of the angle per exec)
    float maxTurnAngleDeg = 5.0f;   // fp28 (cap per exec)
    float territoryRadius = 150.0f; // fp09
    float homeRadius = 30.0f;       // fp10
    float sightRadius = 350.0f;     // fp12
    float fov = 100.0f;             // fp25 (isAttackableTarget |dy| bound)
    float viewAngleDeg = 90.0f;     // fp13
    float alertDuration = 15.0f;    // fp29
};

inline const Params& params()
{
    static const Params p;
    return p;
}

constexpr float kLaneHalfWidth = 15.0f;        // Kabuto.cpp:251
constexpr float kLaneMinForward = 15.0f;       // Kabuto.cpp:253
constexpr float kAlertViewAngleDeg = 180.0f;   // Kabuto.cpp:313-315
constexpr float kSourceHz = 30.0f;             // one enemy exec per 1/30 s
constexpr float kWaitSearchSeconds = 3.0f;     // KabutoState.cpp:100
constexpr float kTurnToMoveDeg = 30.0f;        // KabutoState.cpp:164 (PI / 6)
constexpr float kMoveFaceDeg = 30.0f;          // KabutoState.cpp:232
constexpr float kMoveTimeoutSeconds = 6.0f;    // KabutoState.cpp:227
constexpr float kMoveArriveSq = 625.0f;        // KabutoState.cpp:227 (25^2)

inline float wrapPi(float a)
{
    while (a > kPi) a -= 2.0f * kPi;
    while (a < -kPi) a += 2.0f * kPi;
    return a;
}

inline float toRadians(float deg) { return deg * (kPi / 180.0f); }

// Creature::getAngDist (Creature.h:386-395): signed angle from the facing to
// the XZ direction of `target`.
inline float angDist(const Vec3& pos, float faceDir, const Vec3& target)
{
    return wrapPi(std::atan2(target.x - pos.x, target.z - pos.z) - faceDir);
}

// isAttackableTarget lane test for one candidate position (Kabuto.cpp:228-256).
// Positions are creature base points (getPosition). The source cell sphere
// (centre 0.5 x sight ahead, radius 0.75 x sight, Kabuto.cpp:230-233) contains
// the whole lane, so the lane alone decides.
inline bool inAttackLane(const Vec3& pos, float faceDir, const Vec3& target, const Params& p = params())
{
    const float dirX = std::sin(faceDir), dirZ = std::cos(faceDir);
    const float orthoX = -dirZ, orthoZ = dirX;
    const float dx = target.x - pos.x, dy = target.y - pos.y, dz = target.z - pos.z;
    if (!(std::fabs(dy) < p.fov) || !(std::fabs(orthoX * dx + orthoZ * dz) < kLaneHalfWidth)) {
        return false;
    }
    const float forward = dirX * dx + dirZ * dz;
    return forward > kLaneMinForward && forward < p.sightRadius;
}

// A Navi or Pikmin the host offers to the search / lane test.
//   alive      - isAttackableTarget eligibility: creature->isAlive() and
//                isNavi() or a Piki that isPikmin() (Kabuto.cpp:242-245).
//   searchable - getSearchedTarget eligibility: getNearestNavi takes a live
//                Navi (enemyAction.cpp:43); getNearestPikmin takes
//                Piki::isSearchable() = isPikmin && isAlive && !isStickToMouth
//                (enemyAction.cpp:394, Piki.h:243-249).
struct Candidate {
    Vec3 pos;
    bool navi = false;
    bool alive = true;
    bool searchable = true;
};

// What a host (P1) Pikmin is in P2 terms (#884 rounds 5-6).
//   Active - an ordinary above-ground Piki (includes being plucked:
//            P2 PikiNukareState / AutoNuki are Piki states,
//            PikiState.h:39,44,694-696).
//   Sprout - P1 PIKISTATE_Grow / Bury / NukareWait: a Pikmin planted or in
//            the ground. In P2 that is an ItemPikihead::Item, not a Piki
//            (ItemPikihead.h:198), so neither the search (Piki-only,
//            enemyAction.cpp:368-410) nor the lane (isPiki && isPikmin,
//            Kabuto.cpp:244) ever sees it.
//   Dead   - a P1 state whose P2 PikiState reports dead() == true, so the
//            P2 virtual Piki::isAlive (CF_IsAlive && !mCurrentState->dead(),
//            piki.cpp:319-327) is false and both the lane (Kabuto.cpp:242)
//            and the search (Piki::isSearchable, Piki.h:243-249) reject it:
//              P1 PIKISTATE_Pressed     - P2 PikiPressedState::dead
//                                         (PikiState.h:761);
//              P1 PIKISTATE_DenkiDying  - P2 PikiDenkiDyingState::dead
//                                         (PikiState.h:246);
//              P1 PIKISTATE_Swallowed   - P2 PikiSwallowedState::dead
//                                         (PikiState.h:823); P2
//                                         InteractSwallow::actPiki transits
//                                         every mouth-held Piki to it
//                                         (interactPiki.cpp:672,689).
//            P1 Dying / Dead (P2 PikiState.h:329,215) are already excluded
//            by the host P1 Piki::isAlive (hostAlive = false).
enum class PikminPhase { Active, Sprout, Dead };

inline Candidate pikminCandidate(const Vec3& pos, bool hostAlive, PikminPhase phase)
{
    Candidate c;
    c.pos = pos;
    c.navi = false;
    c.alive = hostAlive && phase == PikminPhase::Active;
    c.searchable = c.alive;
    return c;
}

inline Candidate naviCandidate(const Vec3& pos, bool hostAlive)
{
    Candidate c;
    c.pos = pos;
    c.navi = true;
    c.alive = hostAlive;
    c.searchable = hostAlive;
    return c;
}

// First live Navi / Pikmin in the lane, or -1 (for logs).
inline int attackableIndex(const Vec3& pos, float faceDir, const Candidate* c, int n,
                           const Params& p = params())
{
    for (int i = 0; i < n; ++i) {
        if (c[i].alive && inAttackLane(pos, faceDir, c[i].pos, p)) {
            return i;
        }
    }
    return -1;
}

// isAttackableTarget: true when any live Navi / Pikmin is in the lane.
inline bool isAttackableTarget(const Vec3& pos, float faceDir, const Candidate* c, int n,
                               const Params& p = params())
{
    return attackableIndex(pos, faceDir, c, n, p) >= 0;
}

// Lane coordinates of `target` relative to the facing (for logs / tests).
struct LaneCoords {
    float forward = 0.0f, lateral = 0.0f, dy = 0.0f;
};
inline LaneCoords laneCoords(const Vec3& pos, float faceDir, const Vec3& target)
{
    const float dirX = std::sin(faceDir), dirZ = std::cos(faceDir);
    const float dx = target.x - pos.x, dz = target.z - pos.z;
    LaneCoords l;
    l.forward = dirX * dx + dirZ * dz;
    l.lateral = -dirZ * dx + dirX * dz;
    l.dy = target.y - pos.y;
    return l;
}

// getViewAngle (Kabuto.cpp:311-318).
inline float viewAngleDeg(float alertTimer, const Params& p = params())
{
    return alertTimer < p.alertDuration ? kAlertViewAngleDeg : p.viewAngleDeg;
}

// getNearestPikminOrNavi (enemyAction.cpp:746-760): the nearest Navi within
// the XZ sight radius and |angDist| <= viewAngle is found first; a Pikmin is
// returned only when strictly closer. Returns the candidate index or -1.
inline int searchTarget(const Vec3& pos, float faceDir, float viewDeg, const Candidate* c, int n,
                        const Params& p = params())
{
    const float limit = toRadians(viewDeg);
    float best = p.sightRadius * p.sightRadius;
    int navi = -1, piki = -1;
    for (int pass = 0; pass < 2; ++pass) {
        for (int i = 0; i < n; ++i) {
            if (!c[i].alive || !c[i].searchable || c[i].navi != (pass == 0)) {
                continue;
            }
            if (!(std::fabs(angDist(pos, faceDir, c[i].pos)) <= limit)) {
                continue;
            }
            const float dx = c[i].pos.x - pos.x, dz = c[i].pos.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < best) {
                best = d;
                (pass == 0 ? navi : piki) = i;
            }
        }
    }
    return piki >= 0 ? piki : navi;
}

// turnToTarget (EnemyBase.h:463-470) over a host frame of `dt` seconds. At
// dt = 1/30 it is exactly one source exec: step = clamp(a * turnSpeed,
// rad(maxTurnAngle)). Other host rates scale the per-exec fraction and cap to
// dt * 30 execs. Returns the angDist measured before the step (as the source).
struct TurnStep {
    float faceDir = 0.0f;
    float angleDist = 0.0f;
};

inline TurnStep turnToward(const Vec3& pos, float faceDir, const Vec3& target, float dt,
                           const Params& p = params())
{
    TurnStep r;
    r.angleDist = angDist(pos, faceDir, target);
    const float execs = dt * kSourceHz;
    const float fraction = 1.0f - std::pow(1.0f - p.turnSpeed, execs);
    const float cap = toRadians(p.maxTurnAngleDeg) * execs;
    float step = r.angleDist * fraction;
    if (step > cap) step = cap;
    if (step < -cap) step = -cap;
    r.faceDir = wrapPi(faceDir + step);
    return r;
}

// setRandTarget (Kabuto.cpp:198-206). `u0`, `u1` are uniform [0, 1) draws
// (randWeightFloat(x) = x * rand / RAND_MAX, Dolphin/rand.h:26-29).
inline Vec3 wanderTarget(const Vec3& pos, const Vec3& home, float u0, float u1, const Params& p = params())
{
    const float radius = p.homeRadius + u0 * (p.territoryRadius - p.homeRadius);
    const float away = std::atan2(pos.x - home.x, pos.z - home.z);
    const float angle = kPi / 2.0f + (away + u1 * kPi);
    Vec3 t;
    t.x = radius * std::sin(angle) + home.x;
    t.y = home.y;
    t.z = radius * std::cos(angle) + home.z;
    return t;
}

enum class Next { Stay, Turn, Attack, Move, Wait };

// StateWait::exec target / timer check (KabutoState.cpp:97-103); the host
// latches the result and transits when the wait clip ends (:107-109).
inline bool waitWantsTurn(float waitTimer, bool targetSeen)
{
    return waitTimer > kWaitSearchSeconds || targetSeen;
}

struct TurnResult {
    float faceDir = 0.0f;
    float angleDist = 0.0f;
    int target = -1;
    Next next = Next::Stay;
};

// StateTurn::exec (KabutoState.cpp:150-168). With a searched target it turns
// toward it and asks for Attack only once isAttackableTarget holds, so an
// off-axis target keeps it turning instead of stalling (there is no
// "facing is close enough" exit). Without a target it turns to the wander
// target and asks for Move within 30 deg.
inline TurnResult turnExec(const Vec3& pos, float faceDir, float dt, float viewDeg, const Candidate* c,
                           int n, const Vec3& wander, const Params& p = params())
{
    TurnResult r;
    r.target = searchTarget(pos, faceDir, viewDeg, c, n, p);
    if (r.target >= 0) {
        const TurnStep s = turnToward(pos, faceDir, c[r.target].pos, dt, p);
        r.faceDir = s.faceDir;
        r.angleDist = s.angleDist;
        if (isAttackableTarget(pos, r.faceDir, c, n, p)) {
            r.next = Next::Attack;
        }
        return r;
    }
    const TurnStep s = turnToward(pos, faceDir, wander, dt, p);
    r.faceDir = s.faceDir;
    r.angleDist = s.angleDist;
    if (std::fabs(s.angleDist) <= toRadians(kTurnToMoveDeg)) {
        r.next = Next::Move;
    }
    return r;
}

struct MoveResult {
    float faceDir = 0.0f;
    int target = -1;
    bool walk = false;
    Next next = Next::Stay;
};

// StateMove::exec (KabutoState.cpp:211-243). A searched target sends it to
// Turn, or to Attack when the lane already holds; otherwise it walks toward
// the wander target while facing it within 30 deg.
inline MoveResult moveExec(const Vec3& pos, float faceDir, float dt, float viewDeg, float moveTimer,
                           const Candidate* c, int n, const Vec3& wander, const Params& p = params())
{
    MoveResult r;
    r.faceDir = faceDir;
    r.target = searchTarget(pos, faceDir, viewDeg, c, n, p);
    if (r.target >= 0) {
        r.next = isAttackableTarget(pos, faceDir, c, n, p) ? Next::Attack : Next::Turn;
        return r;
    }
    const float dx = pos.x - wander.x, dz = pos.z - wander.z;
    if (moveTimer > kMoveTimeoutSeconds || dx * dx + dz * dz < kMoveArriveSq) {
        r.next = Next::Wait;
        return r;
    }
    const TurnStep s = turnToward(pos, faceDir, wander, dt, p);
    r.faceDir = s.faceDir;
    if (std::fabs(s.angleDist) <= toRadians(kMoveFaceDeg)) {
        r.walk = true;
    } else {
        r.next = Next::Turn;
    }
    return r;
}

} // namespace p2kabutoaim
