#include "pc_p2_cannon_stone.h"

#include <cmath>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 2.0f * kPi;

bool finite(float value) { return std::isfinite(value); }
bool finite(const P2CannonStoneVec3& value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}

// sysMath.cpp:254-267. Normalises to [0, TAU).
float roundAng(float angle)
{
    if (angle < 0.0f) {
        angle += kTau;
    }
    if (angle >= kTau) {
        angle -= kTau;
    }
    return angle;
}

// sysMath.cpp:273-281. Signed shortest angular difference in [-PI, PI).
float angDist(float angle1, float angle2)
{
    float angle = roundAng(angle1 - angle2);
    if (angle >= kPi) {
        angle = -roundAng(kTau - angle);
    }
    return angle;
}

// trig.h:91-94. angXZ(x, z) = roundAng(atan2(x, z)).
float angXZ(float x, float z) { return roundAng(std::atan2(x, z)); }

bool validConfig(const P2CannonStoneConfig& config)
{
    return finite(config.moveSpeed) && config.moveSpeed >= 0.0f
        && finite(config.searchRumbleSpeed) && config.searchRumbleSpeed >= 0.0f
        && finite(config.turnSpeed) && config.turnSpeed >= 0.0f
        && finite(config.maxTurnAngle) && config.maxTurnAngle >= 0.0f
        && finite(config.attackDamage) && config.attackDamage >= 0.0f
        && finite(config.sightRadius) && config.sightRadius >= 0.0f
        && finite(config.collisionRadius) && config.collisionRadius > 0.0f
        && finite(config.health) && config.health > 0.0f;
}
} // namespace

void P2CannonStone::reset(const P2CannonStoneConfig& config)
{
    mConfig = config;
    mPhase = P2CannonStonePhase::Inactive;
    mPosition = P2CannonStoneVec3{};
    mVelocity = P2CannonStoneVec3{};
    mTargetVelocity = P2CannonStoneVec3{};
    mFaceDir = 0.0f;
    mTimer = 0.0f;
    mScale = kInitialScale;
    mHealth = 0.0f;
    mHoming = false;
    mHealthZeroed = false;
    mSourceToken = 0;
    mSelfToken = 0;
}

P2CannonStoneVec3 P2CannonStone::mouthBirthPosition(const P2CannonStoneVec3& mouthJointWorldPos)
{
    return { mouthJointWorldPos.x, mouthJointWorldPos.y + 25.0f, mouthJointWorldPos.z };
}

P2CannonStoneVec3 P2CannonStone::initialVelocity(float faceDir, float moveSpeed)
{
    return { moveSpeed * std::sin(faceDir), 0.0f, moveSpeed * std::cos(faceDir) };
}

bool P2CannonStone::birth(const P2CannonStoneVec3& mouthPosition, float faceDir, bool homing,
                          std::uint64_t sourceToken, std::uint64_t selfToken)
{
    if (mPhase != P2CannonStonePhase::Inactive || !validConfig(mConfig)
        || !finite(mouthPosition) || !finite(faceDir)) {
        return false;
    }

    mPosition = mouthPosition;
    mFaceDir = roundAng(faceDir);
    mHoming = homing;
    mSourceToken = sourceToken;
    mSelfToken = selfToken;
    mTimer = 0.0f;
    mScale = kInitialScale; // Rock.cpp:51-55 (drop group none)
    mHealth = mConfig.health;
    mHealthZeroed = false;

    // Stone onInit (Rock.cpp:88-93): initMoveVelocity then ROCK_Move. There is
    // no ROCK_Wait / ROCK_Appear / ROCK_Fall for the fired Stone.
    mVelocity = initialVelocity(mFaceDir, mConfig.moveSpeed);
    mTargetVelocity = mVelocity;
    mPhase = P2CannonStonePhase::Move;
    return true;
}

void P2CannonStone::steerTo(const P2CannonStoneVec3& targetPos)
{
    // Creature::getAngDist(Vector3f&) (Creature.h:386-395) + EnemyBase
    // turnToTarget (EnemyBase.h:462-471).
    const float between = angXZ(targetPos.x - mPosition.x, targetPos.z - mPosition.z);
    const float diff = angDist(between, mFaceDir);
    const float limit = mConfig.maxTurnAngle * kPi / 180.0f; // TORADIANS
    float turn = diff * mConfig.turnSpeed;
    if (std::fabs(turn) > limit) {
        turn = (turn > 0.0f) ? limit : -limit;
    }
    mFaceDir = roundAng(mFaceDir + turn);
}

bool P2CannonStone::update(float delta, const P2CannonStoneTarget& target,
                           P2CannonStoneTraceFn trace, void* traceContext)
{
    if (mPhase != P2CannonStonePhase::Move || !finite(delta)
        || std::fabs(delta - kSourceDelta) > 0.000001f) {
        return false;
    }

    // updateMoveVelocity (Rock.cpp:368-398).
    P2CannonStoneVec3 targetPos;
    if (mHoming) {
        if (target.hasTarget && finite(target.position)) {
            targetPos = target.position;
        } else {
            // No target: keep the current heading (Rock.cpp:382-384).
            targetPos = { mPosition.x + mTargetVelocity.x, mPosition.y + mTargetVelocity.y,
                          mPosition.z + mTargetVelocity.z };
        }
        steerTo(targetPos);
        // setTargetSpeed(C_PROPERPARMS.mSearchRumbleSpeed()) (Rock.cpp:388).
        mTargetVelocity = { mConfig.searchRumbleSpeed * std::sin(mFaceDir), mTargetVelocity.y,
                            mConfig.searchRumbleSpeed * std::cos(mFaceDir) };
    } else {
        // 0.01 * mCurrentVelocity + 0.99 * mTargetVelocity (Rock.cpp:391-393).
        mTargetVelocity.x = kNonHomingCurrentWeight * mVelocity.x
            + kNonHomingTargetWeight * mTargetVelocity.x;
        mTargetVelocity.y = kNonHomingCurrentWeight * mVelocity.y
            + kNonHomingTargetWeight * mTargetVelocity.y;
        mTargetVelocity.z = kNonHomingCurrentWeight * mVelocity.z
            + kNonHomingTargetWeight * mTargetVelocity.z;
        targetPos = { mPosition.x + mTargetVelocity.x, mPosition.y + mTargetVelocity.y,
                      mPosition.z + mTargetVelocity.z };
        steerTo(targetPos);
    }

    // Host movement. A trace that reports `wall` maps to wallCallback
    // (Rock.cpp:244-249): Move -> Dead.
    P2CannonStoneTraceResult traced;
    const bool tracedOk = trace ? trace(traceContext, mPosition, mTargetVelocity, delta,
                                        mConfig.collisionRadius, traced)
                                : false;
    if (tracedOk) {
        if (!finite(traced.position) || !finite(traced.velocity)) {
            enterDead();
            return true;
        }
        mPosition = traced.position;
        mVelocity = traced.velocity;
        if (traced.wall) {
            enterDead();
            return true;
        }
    } else {
        // No host trace: integrate the command directly (flat ground).
        mPosition.x += mTargetVelocity.x * delta;
        mPosition.y += mTargetVelocity.y * delta;
        mPosition.z += mTargetVelocity.z * delta;
        mVelocity = mTargetVelocity;
    }

    // moveRockScaleUp (Rock.cpp:333-350) then timer (RockState.cpp:233-235).
    if (mScale < 1.0f) {
        float scale = kRollScaleUpPerSecond * delta + mScale;
        if (scale >= 1.0f) {
            scale = 1.0f;
        }
        mScale = scale;
    }
    mTimer += delta;

    // StateMove::exec destruction gate (RockState.cpp:238-240).
    if (mHealth <= 0.0f || mTimer > kMoveTimeoutSeconds) {
        enterDead();
    }
    return true;
}

void P2CannonStone::enterDead()
{
    // StateDead::init (RockState.cpp:261-269): target velocity zeroed and the
    // dead motion started; shadow removal / effect / sound are host-owned.
    mTargetVelocity = P2CannonStoneVec3{};
    mPhase = P2CannonStonePhase::Dead;
}

P2CannonStoneContactResult P2CannonStone::contact(P2CannonStoneContactKind kind, bool targetOnFloor,
                                                  bool targetIsRock, std::uint64_t targetToken)
{
    P2CannonStoneContactResult result;
    // Dead disables atari on its first exec (RockState.cpp:275-281), so no
    // further CollEvent reaches collisionCallback.
    if (mPhase != P2CannonStonePhase::Move) {
        return result;
    }
    if (shouldIgnoreAtari(targetToken)) {
        result.ignored = true;
        return result;
    }

    const bool isNaviOrPiki = (kind == P2CannonStoneContactKind::NaviPiki);
    bool notRock = true;

    if (isNaviOrPiki) {
        // Only a grounded Navi/Piki receives InteractPress (Rock.cpp:210-220).
        if (targetOnFloor) {
            result.strikeEmitted = true;
            result.strike.kind = P2CannonStoneStrikeKind::Press;
            result.strike.damage = mConfig.attackDamage;
            result.strike.targetToken = targetToken;
            result.strike.attributedToSource = (mSourceToken != 0);
            result.strike.attributedToken = result.strike.attributedToSource ? mSourceToken : mSelfToken;
        }
    } else if (kind == P2CannonStoneContactKind::Teki) {
        // Teki take a fixed 250 InteractAttack attributed to the Stone
        // (Rock.cpp:221-223).
        result.strikeEmitted = true;
        result.strike.kind = P2CannonStoneStrikeKind::Attack;
        result.strike.damage = kTekiAttackDamage;
        result.strike.targetToken = targetToken;
        result.strike.attributedToken = mSelfToken;
        if (mConfig.variant == P2CannonStoneVariant::Rock && targetIsRock) {
            notRock = false; // Rock-vs-Rock mutual collision suppression (Rock.cpp:225-227)
        }
    }

    // Any non-Navi/Piki contact forces health to zero (Rock.cpp:230-232).
    if (!isNaviOrPiki) {
        mHealth = 0.0f;
        mHealthZeroed = true;
        result.healthZeroed = true;
    }
    if (!notRock) {
        result.selfCollisionSuppressed = true;
    }
    return result;
}

bool P2CannonStone::notifyWallContact()
{
    if (mPhase != P2CannonStonePhase::Move) {
        return false;
    }
    enterDead();
    return true;
}

bool P2CannonStone::notifyHipdrop(bool bittered)
{
    // hipdropCallBack (Rock.cpp:190-198): alive, not bittered, in ROCK_Move.
    if (mPhase != P2CannonStonePhase::Move || bittered) {
        return false;
    }
    enterDead();
    return true;
}

bool P2CannonStone::finishDeath()
{
    // StateDead::exec (RockState.cpp:283-285): KEYEVENT_END -> kill(nullptr).
    if (mPhase != P2CannonStonePhase::Dead) {
        return false;
    }
    mPhase = P2CannonStonePhase::Killed;
    return true;
}

bool P2CannonStone::shouldIgnoreAtari(std::uint64_t targetToken) const
{
    // ignoreAtari (Rock.cpp:298-304): ignore mSourceEnemy for the first second.
    return mSourceToken != 0 && targetToken == mSourceToken && mTimer < kAtariGraceSeconds;
}

int P2CannonStonePool::activeCount() const
{
    int count = 0;
    for (int i = 0; i < mCapacity && i < kMaxStones; ++i) {
        if (mUsed[i] && mStones[i].isAlive()) {
            ++count;
        }
    }
    return count;
}

P2CannonStone* P2CannonStonePool::spawn(const P2CannonStoneVec3& mouthPosition, float faceDir,
                                        bool homing, std::uint64_t sourceToken,
                                        std::uint64_t selfToken,
                                        const P2CannonStoneConfig& config)
{
    if (!finite(mouthPosition)) {
        return nullptr;
    }
    const int limit = mCapacity < kMaxStones ? mCapacity : kMaxStones;
    for (int i = 0; i < limit; ++i) {
        const bool free = !mUsed[i] || !mStones[i].isAlive();
        if (!free) {
            continue;
        }
        mStones[i].reset(config);
        if (!mStones[i].birth(mouthPosition, faceDir, homing, sourceToken, selfToken)) {
            return nullptr; // invalid config/input: no partial state
        }
        mUsed[i] = true;
        return &mStones[i];
    }
    return nullptr; // exhausted: silent tolerance, matches failed manager birth
}
