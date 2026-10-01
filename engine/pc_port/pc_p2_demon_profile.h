// Bumbling Snitchbug (Demon, P2 enemy ID 32) species profile for the Sarai host.
//
// Transcribed from US GPVE01 rev 0 pikmin2-research:
//   include/Game/Entities/Demon.h        Demon::Obj : Sarai::Obj, mAttackTimer
//   src/plugProjectNishimuraU/Demon.cpp   getAttackableTarget / catchTarget
//   src/plugProjectNishimuraU/Sarai.cpp   onInit resetAttackableTimer(12800),
//                                         setHeightVelocity, setRandTarget
//   src/plugProjectNishimuraU/SaraiState.cpp  FallMeck::cleanup resetAttackableTimer(0)
//   src/plugProjectYamashitaU/enemyBase.cpp   doSimulationFlying / Ground
//   include/Game/EnemyParmsBase.h         general parm ids
//
// Demon runs Sarai's eleven-state FSM unchanged (p2sarai::Fsm). What differs
// is the target: naviMgr captains, gated by a 3 s attack timer that only
// advances while getAttackableTarget() is queried (Wait/Move exec), and the
// view test uses the FULL TORADIANS(mViewAngle) (Sarai uses PI*DEG2RAD*angle).
// The first navi that passes is returned (iteration order, not nearest).
//
// Dependency-free: no engine objects, no I/O beyond the staged parms stream.
#ifndef PC_P2_DEMON_PROFILE_H
#define PC_P2_DEMON_PROFILE_H

#include "pc_p2_sarai_policy.h"
#include <cmath>
#include <istream>
#include <map>
#include <string>

namespace p2demon {

constexpr unsigned kSourceId = 32;

// EnemyParmsBase general parms used by the Sarai/Demon exec paths. Defaults
// are the EnemyParmsBase code defaults; the retail demon/enemyparm.txt values
// replace every one of them at load (all rows are required).
struct General {
    float life = 100.0f;            // fp00
    float moveSpeed = 80.0f;        // fp06 (unused by Sarai exec: fp04/fp05 drive flight)
    float turnSpeed = 0.1f;         // fp08
    float maxTurnAngle = 10.0f;     // fp28 (degrees)
    float territoryRadius = 200.0f; // fp09
    float homeRadius = 15.0f;       // fp10
    float sightRadius = 200.0f;     // fp12
    float viewAngle = 90.0f;        // fp13 (degrees)
    float shakeChance = 1.0f;       // fp16
    float shakeKnockback = 300.0f;  // fp17
    float shakeDamage = 0.0f;       // fp18
    float attackDamage = 10.0f;     // fp24 (InteractFallMeck damage)
};

struct Parms {
    General general;
    p2sarai::Parms proper;
    bool retail = false; // every staged row was read
};

// P2_DEMON_PARMS_1 <64-hex digest> <count>, then `<general|proper> <fpNN> <value>`.
inline bool loadParms(std::istream& in, Parms& out)
{
    std::string magic, digest;
    int count = 0;
    if (!(in >> magic >> digest >> count) || magic != "P2_DEMON_PARMS_1" || digest.size() != 64
        || count < 1 || count > 64)
        return false;
    Parms parsed;
    std::map<std::string, float*> general{
        {"fp00", &parsed.general.life}, {"fp06", &parsed.general.moveSpeed},
        {"fp08", &parsed.general.turnSpeed}, {"fp28", &parsed.general.maxTurnAngle},
        {"fp09", &parsed.general.territoryRadius}, {"fp10", &parsed.general.homeRadius},
        {"fp12", &parsed.general.sightRadius}, {"fp13", &parsed.general.viewAngle},
        {"fp16", &parsed.general.shakeChance}, {"fp17", &parsed.general.shakeKnockback},
        {"fp18", &parsed.general.shakeDamage}, {"fp24", &parsed.general.attackDamage}};
    std::map<std::string, float*> proper{
        {"fp01", &parsed.proper.normalFlightHeight}, {"fp02", &parsed.proper.grabFlightHeight},
        {"fp03", &parsed.proper.stateTransitionHeight}, {"fp04", &parsed.proper.normalMovementSpeed},
        {"fp05", &parsed.proper.grabMovementSpeed}, {"fp06", &parsed.proper.waitTime},
        {"fp11", &parsed.proper.climbingFactor0}, {"fp12", &parsed.proper.climbingFactor5},
        {"fp21", &parsed.proper.payoffProbability1}, {"fp22", &parsed.proper.payoffProbability5},
        {"fp23", &parsed.proper.strugglingTime}, {"fp31", &parsed.proper.huntDescentFactor},
        {"fp32", &parsed.proper.postHuntDecayRate}, {"fp41", &parsed.proper.fallMeckSpeed}};
    const std::size_t wanted = general.size() + proper.size();
    std::size_t seen = 0;
    for (int i = 0; i < count; ++i) {
        std::string scope, key;
        float value = 0.0f;
        if (!(in >> scope >> key >> value) || !std::isfinite(value) || value < 0.0f || value > 100000.0f)
            return false;
        if (scope != "general" && scope != "proper") return false;
        auto& table = scope == "general" ? general : proper;
        auto it = table.find(key);
        if (it == table.end() || !it->second) return false;
        *it->second = value;
        it->second = nullptr; // duplicates rejected
        ++seen;
    }
    std::string extra;
    if (in >> extra) return false;
    if (seen != wanted) return false;
    parsed.retail = true;
    out = parsed;
    return true;
}

// Demon::mAttackTimer. Sarai::onInit resetAttackableTimer(12800) arms an
// immediate first grab; FallMeck::cleanup resetAttackableTimer(0) makes the
// next grab wait > 3 s of Wait/Move queries.
class AttackTimer {
public:
    void reset(float value) { mTimer = value; }
    float value() const { return mTimer; }
    // One getAttackableTarget() call: advance, then gate.
    bool query(float dt)
    {
        mTimer += dt;
        return mTimer > 3.0f;
    }

private:
    float mTimer = 12800.0f;
};

// Demon.cpp getAttackableTarget() per-navi test (after the timer gate).
// angleRad is getAngDist(navi) wrapped to [-PI, PI].
inline bool captainTargetable(const General& g, float sqrDistHomeXZ, bool alive, bool stickToMouth,
                              float angleRad, float sqrDistXZ)
{
    if (!(sqrDistHomeXZ < g.territoryRadius * g.territoryRadius)) return false;
    if (!alive || stickToMouth) return false;
    if (!(std::fabs(angleRad) <= g.viewAngle * p2sarai::kDeg2Rad)) return false;
    return sqrDistXZ < g.sightRadius * g.sightRadius;
}

// EnemyBase::turnToTarget: signed turn clamped to maxTurnAngle.
inline float turnStep(float angleDist, float turnSpeed, float maxTurnDegrees)
{
    const float cap = maxTurnDegrees * p2sarai::kDeg2Rad;
    float turn = angleDist * turnSpeed;
    if (turn > cap) turn = cap;
    if (turn < -cap) turn = -cap;
    return turn;
}

inline float wrapPi(float a)
{
    while (a > p2sarai::kPi) a -= 2.0f * p2sarai::kPi;
    while (a < -p2sarai::kPi) a += 2.0f * p2sarai::kPi;
    return a;
}

// Attack hunt descent (SaraiState.cpp Attack exec, 10 < frame <= 30).
inline float huntDescentVelocity(const p2sarai::Parms& p, float targetY, float selfY, float dt)
{
    if (!(dt > 0.0f)) return 0.0f;
    float v = (((targetY + 17.5f) - selfY) / dt) * p.huntDescentFactor;
    if (v < -2500.0f) v = -2500.0f;
    if (v > 1000.0f) v = 1000.0f;
    return v;
}

// EnemyBase simulation step. Untargetable (flying) states pull the whole
// velocity toward the target velocity; the others are ground states that pull
// XZ only and add gravity. accelScale = dt / s003 accel (0.1 for Demon).
struct Velocity { float x = 0, y = 0, z = 0; };
inline Velocity simulate(Velocity current, Velocity target, bool flying, float dt, float accel, float gravity)
{
    float k = accel > 0.0f ? dt / accel : 1.0f;
    if (k > 1.0f) k = 1.0f;
    if (flying) {
        current.x += (target.x - current.x) * k;
        current.y += (target.y - current.y) * k;
        current.z += (target.z - current.z) * k;
    } else {
        current.x += (target.x - current.x) * k;
        current.z += (target.z - current.z) * k;
        current.y -= gravity * dt;
    }
    return current;
}

} // namespace p2demon

#endif
