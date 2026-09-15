#include "pc_p2_rock_hazard.h"

#include <cmath>

namespace {
bool finite(float value) { return std::isfinite(value); }
bool finite(const P2RockHazardVec3& value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}

bool validConfig(const P2RockHazardConfig& config)
{
    return finite(config.fallSpeed) && config.fallSpeed >= 0.0f
        && finite(config.fallOffset) && config.fallOffset >= 0.0f
        && finite(config.scaleUpRate) && config.scaleUpRate > 0.0f
        && finite(config.sightRadius) && config.sightRadius >= 0.0f
        && finite(config.attackDamage) && config.attackDamage >= 0.0f
        && finite(config.collisionRadius) && config.collisionRadius > 0.0f
        && finite(config.health) && config.health > 0.0f;
}
} // namespace

void P2RockHazard::reset(const P2RockHazardConfig& config)
{
    mConfig = config;
    mPhase = P2RockHazardPhase::Inactive;
    mPosition = P2RockHazardVec3{};
    mVelocity = P2RockHazardVec3{};
    mTargetVelocity = P2RockHazardVec3{};
    mScale = 1.0f;
    mTimer = 0.0f;
    mHealth = 0.0f;
    mTimedAppear = false;
    mSourceToken = 0;
    mSelfToken = 0;
    mAtari = true;
    mUntargetable = false;
    mHardConstrained = false;
    mAnimating = true;
    mModelHidden = false;
    mCullable = true;
    mCullSound = true;
    mShadow = false;
    mShadowForced = false;
    mFallEffect = false;
    mDeadEffect = false;
    mAnimationCullingOff = false;
    mColliding = false;
    mMotion = P2RockHazardMotion::None;
    mMotionStopped = false;
}

bool P2RockHazard::onInit(const P2RockHazardInit& init)
{
    if (mPhase != P2RockHazardPhase::Inactive || !validConfig(mConfig)
        || !finite(init.position) || !finite(init.initialTimer) || init.initialTimer < 0.0f) {
        return false;
    }

    mPosition = init.position;
    mSourceToken = init.sourceToken;
    mSelfToken = init.selfToken;
    mTimer = 0.0f; // Rock.cpp:67
    mHealth = mConfig.health;

    // Rock.cpp:57-65: invulnerable, no damage anim / carcass / death effect /
    // lifegauge, bitter-immune. Only the flags this FSM turns back on are
    // tracked; the rest are constant host flags.
    mAtari = true;
    mUntargetable = false;
    mHardConstrained = false;
    mAnimating = true;
    mModelHidden = false;
    mCullable = true;
    mCullSound = true;
    mShadow = true;
    mShadowForced = false;
    mFallEffect = false;
    mDeadEffect = false;
    mAnimationCullingOff = false;
    mColliding = false;
    mMotion = P2RockHazardMotion::None;
    mMotionStopped = false;
    mVelocity = P2RockHazardVec3{};
    mTargetVelocity = P2RockHazardVec3{};

    // Rock.cpp:73-76: a timed (mExistDuration != 0) falling rock is never
    // culled and seeds mTimer with randWeightFloat(1.5) on the host side.
    mTimedAppear = init.timedAppear;
    if (mTimedAppear) {
        mCullable = false;
        mTimer = init.initialTimer;
    }

    if (init.dropGroupNone) {
        // Rock.cpp:51-55,78-80: hidden 0.0001 scale and ROCK_Wait.
        mScale = kInitialHiddenScale;
        mPhase = P2RockHazardPhase::Wait;

        // StateWait::init (RockState.cpp:30-42).
        mAtari = false;
        mUntargetable = true;
        mHardConstrained = true;
        mAnimating = false;
        mModelHidden = true;
        mTargetVelocity = P2RockHazardVec3{};
        mMotion = P2RockHazardMotion::Run;
        mMotionStopped = true;

        mAnimationCullingOff = true; // doAnimationCullingOff (Rock.cpp:80)
    } else {
        // Rock.cpp:82-84: drop-group Rock starts ROCK_DropWait. The default
        // scale is the EnemyBase 1.0.
        mScale = 1.0f;
        mPhase = P2RockHazardPhase::DropWait;

        // StateDropWait::init (RockState.cpp:137-141).
        mMotion = P2RockHazardMotion::Run;
        mMotionStopped = false;
    }

    mShadow = false; // shadowMgr->delShadow(this) (Rock.cpp:86)
    return true;
}

void P2RockHazard::enterAppear()
{
    // StateWait::cleanup (RockState.cpp:77-83).
    mHardConstrained = false;
    mAnimating = true;
    mModelHidden = false;

    // StateAppear::init (RockState.cpp:89-107).
    mPosition.y += mConfig.fallOffset;
    mModelHidden = true;
    mCullable = false;
    mCullSound = false;
    mTargetVelocity = P2RockHazardVec3{};
    mMotion = P2RockHazardMotion::Run;
    mMotionStopped = false;
    mShadow = true;
    mShadowForced = true;
    mPhase = P2RockHazardPhase::Appear;
}

void P2RockHazard::enterFall()
{
    // StateFall::init (RockState.cpp:170-176).
    mVelocity = { 0.0f, -mConfig.fallSpeed, 0.0f };
    mFallEffect = true;
    mPhase = P2RockHazardPhase::Fall;
}

void P2RockHazard::enterFallFromAppear()
{
    // StateAppear::cleanup (RockState.cpp:125-131).
    mAtari = true;
    mUntargetable = false;
    mModelHidden = false;
    enterFall();
}

void P2RockHazard::enterFallFromDropWait()
{
    // StateDropWait::cleanup (RockState.cpp:156-164).
    mCullable = false;
    mCullSound = false;
    mShadow = true;
    mShadowForced = true;
    enterFall();
}

void P2RockHazard::enterDead()
{
    // StateFall::cleanup (RockState.cpp:195-204): the force-visible shadow is
    // released and the fall effect is faded; camera/rumble are host-owned.
    mShadowForced = false;
    mFallEffect = false;

    // StateDead::init (RockState.cpp:261-269).
    mTargetVelocity = P2RockHazardVec3{};
    mMotion = P2RockHazardMotion::Dead;
    mMotionStopped = false;
    mShadow = false;
    mDeadEffect = true;
    mColliding = false;
    mPhase = P2RockHazardPhase::Dead;
}

bool P2RockHazard::update(float delta, const P2RockHazardDetection& detection,
                          P2RockHazardTraceFn trace, void* traceContext)
{
    if (!finite(delta) || std::fabs(delta - kSourceDelta) > 0.000001f) {
        return false;
    }

    if (mPhase == P2RockHazardPhase::Wait) {
        if (mTimedAppear) {
            // RockState.cpp:51-55.
            mTimer += delta;
            if (mTimer > kAppearTimerSeconds) {
                enterAppear();
            }
        } else if (detection.olimarInSight || detection.pikminInSight) {
            // RockState.cpp:56-69: isThereOlimar then isTherePikmin.
            enterAppear();
        }
        return true;
    }

    if (mPhase == P2RockHazardPhase::Appear) {
        // fallRockScaleUp (Rock.cpp:310-327).
        if (mScale < 1.0f) {
            bool done = false;
            float scale = mConfig.scaleUpRate * delta + mScale;
            if (scale >= 1.0f) {
                done = true;
                scale = 1.0f;
            }
            mScale = scale;
            if (done) {
                enterFallFromAppear();
            }
        }
        return true;
    }

    if (mPhase == P2RockHazardPhase::DropWait) {
        // StateDropWait::exec (RockState.cpp:147-150): immediate Fall.
        enterFallFromDropWait();
        return true;
    }

    if (mPhase == P2RockHazardPhase::Fall) {
        if (!finite(mPosition) || !finite(mVelocity)) {
            enterDead();
            return true;
        }

        // EB_Colliding is reset each source frame (EnemyBase::doUpdateCommon,
        // enemyBase.cpp:1657-1665); consume the contact flag recorded since the
        // previous update.
        bool floorOrColliding = mColliding;
        mColliding = false;

        P2RockHazardTraceResult traced;
        const bool tracedOk = trace
            && trace(traceContext, mPosition, mVelocity, delta, mConfig.collisionRadius, traced);
        if (tracedOk) {
            if (!finite(traced.position) || !finite(traced.velocity)) {
                enterDead();
                return true;
            }
            mPosition = traced.position;
            mVelocity = traced.velocity;
            floorOrColliding = floorOrColliding || traced.floorTriangle || traced.colliding;
        } else {
            mPosition.x += mVelocity.x * delta;
            mPosition.y += mVelocity.y * delta;
            mPosition.z += mVelocity.z * delta;
        }

        // StateFall::exec (RockState.cpp:182-189).
        if (floorOrColliding) {
            enterDead();
        }
        return true;
    }

    return false;
}

P2RockHazardContactResult P2RockHazard::contact(P2RockHazardContactKind kind, bool targetOnFloor,
                                                bool targetIsRock, std::uint64_t targetToken)
{
    P2RockHazardContactResult result;
    // No CollEvent reaches collisionCallback while atari is off (Wait/Appear)
    // and the Dead first exec disables it (RockState.cpp:275-281).
    if (!mAtari || !isAlive()) {
        return result;
    }
    if (shouldIgnoreAtari(targetToken)) {
        result.ignored = true;
        return result;
    }

    const bool isNaviOrPiki = (kind == P2RockHazardContactKind::NaviPiki);
    bool notRock = true;

    if (isNaviOrPiki) {
        // Only a grounded Navi/Piki receives InteractPress (Rock.cpp:210-220).
        if (targetOnFloor) {
            result.strikeEmitted = true;
            result.strike.kind = P2RockHazardStrikeKind::Press;
            result.strike.damage = mConfig.attackDamage;
            result.strike.targetToken = targetToken;
            result.strike.attributedToSource = (mSourceToken != 0);
            result.strike.attributedToken = result.strike.attributedToSource ? mSourceToken : mSelfToken;
        }
    } else if (kind == P2RockHazardContactKind::Teki) {
        // Teki take a fixed 250 InteractAttack attributed to the Rock
        // (Rock.cpp:221-223).
        result.strikeEmitted = true;
        result.strike.kind = P2RockHazardStrikeKind::Attack;
        result.strike.damage = kTekiAttackDamage;
        result.strike.targetToken = targetToken;
        result.strike.attributedToken = mSelfToken;
        if (targetIsRock) {
            notRock = false; // Rock-vs-Rock mutual suppression (Rock.cpp:225-227)
        }
    }

    // Any non-Navi/Piki contact forces mHealth to zero (Rock.cpp:230-232).
    if (!isNaviOrPiki) {
        mHealth = 0.0f;
        result.healthZeroed = true;
    }
    // setCollEvent enables EB_Colliding (enemyBase.cpp:2928-2932); StateFall
    // then transits to Dead. Rock-vs-Rock suppresses it.
    if (notRock) {
        mColliding = true;
    } else {
        result.selfCollisionSuppressed = true;
    }
    return result;
}

bool P2RockHazard::notifyWallContact()
{
    // wallCallback (Rock.cpp:244-249) transits only from ROCK_Move, a Stone
    // rolling state that EnemyID_Rock never enters. Faithful no-op here.
    return false;
}

bool P2RockHazard::notifyHipdrop(bool bittered)
{
    // hipdropCallBack (Rock.cpp:190-198) transits only from ROCK_Move. Faithful
    // no-op here; the falling Rock is unaffected by a hipdrop.
    (void)bittered;
    return false;
}

bool P2RockHazard::finishDeath()
{
    // StateDead::exec (RockState.cpp:283-285): KEYEVENT_END -> kill(nullptr).
    if (mPhase != P2RockHazardPhase::Dead) {
        return false;
    }
    // Obj::onKill (Rock.cpp:100-106): finish the fall/rolling effects.
    mFallEffect = false;
    mPhase = P2RockHazardPhase::Killed;
    return true;
}

bool P2RockHazard::forceDeath()
{
    // Host lifetime cull (source birthArg.mExistenceLength): the same enterDead()
    // the floor-contact path uses, so the Dead -> Killed teardown still runs via
    // finishDeath(). A no-op unless the rock is currently alive.
    if (mPhase != P2RockHazardPhase::Wait && mPhase != P2RockHazardPhase::Appear
        && mPhase != P2RockHazardPhase::DropWait && mPhase != P2RockHazardPhase::Fall) {
        return false;
    }
    mHealth = 0.0f;
    enterDead();
    return true;
}

bool P2RockHazard::shouldIgnoreAtari(std::uint64_t targetToken) const
{
    // ignoreAtari (Rock.cpp:298-304): ignore mSourceEnemy for the first second.
    return mSourceToken != 0 && targetToken == mSourceToken && mTimer < kAtariGraceSeconds;
}

P2RockHazard* P2RockHazardPool::spawn(const P2RockHazardInit& init,
                                      const P2RockHazardConfig& config)
{
    if (!finite(init.position) || !finite(init.initialTimer) || init.initialTimer < 0.0f) {
        return nullptr;
    }
    const int limit = mCapacity < kMaxRocks ? mCapacity : kMaxRocks;
    for (int i = 0; i < limit; ++i) {
        const bool free = !mUsed[i] || mRocks[i].phase() == P2RockHazardPhase::Inactive
            || mRocks[i].phase() == P2RockHazardPhase::Killed;
        if (!free) {
            continue;
        }
        mRocks[i].reset(config);
        if (!mRocks[i].onInit(init)) {
            return nullptr; // invalid config/input: no partial state
        }
        mUsed[i] = true;
        return &mRocks[i];
    }
    return nullptr; // exhausted: silent tolerance, matches failed manager birth
}

P2RockHazard* P2RockHazardPool::spawn(const P2RockHazardVec3& position, bool dropGroupNone,
                                      bool timedAppear, float initialTimer,
                                      std::uint64_t sourceToken, std::uint64_t selfToken,
                                      const P2RockHazardConfig& config)
{
    P2RockHazardInit init;
    init.position = position;
    init.dropGroupNone = dropGroupNone;
    init.timedAppear = timedAppear;
    init.initialTimer = initialTimer;
    init.sourceToken = sourceToken;
    init.selfToken = selfToken;
    return spawn(init, config);
}

int P2RockHazardPool::activeCount() const
{
    int count = 0;
    for (int i = 0; i < mCapacity && i < kMaxRocks; ++i) {
        if (mUsed[i] && mRocks[i].isAlive()) {
            ++count;
        }
    }
    return count;
}
