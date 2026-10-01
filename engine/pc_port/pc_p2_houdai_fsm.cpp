#include "pc_p2_houdai_fsm.h"

#include <cmath>

namespace {
constexpr float kPi = 3.14159265f;
constexpr float kTau = 6.28318531f;
constexpr int kKeyEnd = 100;

float wrapPi(float a)
{
    while (a > kPi) a -= kTau;
    while (a < -kPi) a += kTau;
    return a;
}

float clamp01(float v) { return v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v); }

float distXZ(const P2HoudaiVec& a, const P2HoudaiVec& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}

// Step `value` toward `target` by at most `rate` (radians, shortest way).
float stepAngle(float value, float target, float rate)
{
    const float d = wrapPi(target - value);
    if (std::fabs(d) > rate) return value + (d > 0.0f ? rate : -rate);
    return target;
}

// Key event reached when the clip clock lands on `frame` (enemyanimmgr.txt).
int keyAt(P2LongLegsState state, int frame)
{
    switch (state) {
    case P2LongLegsState::Land:
        if (frame == 54) return 2;
        if (frame == 84) return 3;
        if (frame == 100) return 4;
        if (frame == 130) return 5;
        if (frame == 150) return 6;
        if (frame >= P2HoudaiFsm::kLandingFrames) return kKeyEnd;
        return -1;
    case P2LongLegsState::Wait:
        if (frame == 0) return 0;
        if (frame == 39) return 1;
        if (frame >= P2HoudaiFsm::kWaitFrames) return kKeyEnd;
        return -1;
    case P2LongLegsState::Flick:
        if (frame == 40) return 2;
        if (frame == 45) return 3;
        if (frame == 68) return 4;
        if (frame >= P2HoudaiFsm::kFlickFrames) return kKeyEnd;
        return -1;
    case P2LongLegsState::Shot:
        if (frame == 33) return 2;
        if (frame == 34) return 0;
        if (frame == 35) return 3;
        if (frame == 37) return 4;
        if (frame == 38) return 1;
        if (frame == 39) return 5;
        if (frame >= P2HoudaiFsm::kAttackFrames) return kKeyEnd;
        return -1;
    case P2LongLegsState::Dead:
        if (frame >= P2HoudaiFsm::kDeadFrames) return kKeyEnd;
        return -1;
    default:
        return -1;
    }
}

// Loop pair (key 0 start, key 1 end) of a looping clip; -1 when none.
int loopStart(P2LongLegsState state)
{
    if (state == P2LongLegsState::Wait) return 0;
    if (state == P2LongLegsState::Shot) return 34;
    return -1;
}
int loopEnd(P2LongLegsState state)
{
    if (state == P2LongLegsState::Wait) return 39;
    if (state == P2LongLegsState::Shot) return 38;
    return -1;
}
} // namespace

bool P2HoudaiFsm::isStartFlickFor(const P2HoudaiParms& p, int stuck, float flickTimer)
{
    // EnemyFunc::isStartFlick (enemyAction.cpp:1209): round the hit counter,
    // truncate to u8, compare against the blow tier of the stuck count.
    const float rounded = flickTimer >= 0.0f ? flickTimer + 0.5f : flickTimer - 0.5f;
    const int flickInt = static_cast<int>(static_cast<unsigned char>(static_cast<int>(rounded)));
    if (stuck < p.shakeOffSticking1) return flickInt > p.shakeOffBlowA;
    if (stuck < p.shakeOffSticking2) return flickInt > p.shakeOffBlowB;
    if (stuck < p.shakeOffSticking3) return flickInt > p.shakeOffBlowC;
    return flickInt > p.shakeOffBlowD;
}

bool P2HoudaiFsm::isStartFlick(int stuck) const
{
    return isStartFlickFor(mParms, stuck, mFlickTimer);
}

void P2HoudaiFsm::reset(const P2HoudaiParms& parms, const P2HoudaiVec& home, float faceDir)
{
    *this = P2HoudaiFsm();
    mParms = parms;
    mHome = home;
    mTarget = home;      // onInit: mTargetPosition = mHomePosition
    mGunAim = home;      // onInit: mShotGunTargetPosition = mHomePosition
    mFace = faceDir;
    mState = P2LongLegsState::Stay;
    mStopped = true;     // StateStay::init stopMotion
}

void P2HoudaiFsm::requestFlick(P2HoudaiOutput& out, float chance, float knock, float damage,
                               const char* cause)
{
    out.flickStuck = true;
    out.flickChance = chance;
    out.flickKnockback = knock;
    out.flickDamage = damage;
    out.flickCause = cause;
}

void P2HoudaiFsm::enter(P2LongLegsState next, const P2HoudaiInput& in, P2HoudaiOutput& out)
{
    out.from = mState;
    out.entered = true;
    mState = next;
    mFrame = 0;
    mKey = -1;
    mStopped = false;
    mFinish = false;
    mHasNext = false;
    switch (next) {
    case P2LongLegsState::Land:
        break;
    case P2LongLegsState::Wait:
        mStateTimer = 0.0f;
        mStateDuration = 1.5f + clamp01(in.roll[0]) * 1.5f; // HoudaiState.cpp StateWait::init
        out.chosenSeconds = mStateDuration;
        break;
    case P2LongLegsState::Flick:
        mStateTimer = 0.0f;
        break;
    case P2LongLegsState::Walk:
        mStateTimer = 0.0f;
        mStateDuration = 3.5f + clamp01(in.roll[0]) * 3.5f; // StateWalk::init
        out.chosenSeconds = mStateDuration;
        // startIKMotion: legs reset, the next IK update starts a stride.
        mIkActive = true;
        mIkInMotion = true;
        mStrideT = mParms.strideSeconds;
        walkTargetRule(in); // getTargetPosition
        break;
    case P2LongLegsState::Shot:
        mStateTimer = 0.0f;
        mShotState = 0;
        mSearchTimer = 0.0f;
        break;
    case P2LongLegsState::Dead:
        mIkInMotion = false; // forceFinishIKMotion
        mIkActive = false;
        break;
    default:
        break;
    }
}

void P2HoudaiFsm::walkTargetRule(const P2HoudaiInput& in)
{
    // Houdai::getTargetPosition (Houdai.cpp): nearest non-stuck Pikmin in the
    // view cone and sight radius; otherwise a fresh random point on the home
    // ring once the current target is reached (25 units); home when outside
    // the territory.
    if (distXZ(in.pos, mHome) < mParms.territoryRadius) {
        if (in.walkPikiFound) {
            mTarget = in.walkPiki;
        } else if (distXZ(in.pos, mTarget) < 25.0f) {
            const float range = mParms.territoryRadius - mParms.homeRadius;
            const float randDist = mParms.homeRadius + clamp01(in.roll[1]) * range;
            const float ang = std::atan2(in.pos.x - mHome.x, in.pos.z - mHome.z)
                + clamp01(in.roll[2]) * kPi + 0.5f * kPi;
            mTarget.x = randDist * std::sin(ang) + mHome.x;
            mTarget.y = mHome.y;
            mTarget.z = randDist * std::cos(ang) + mHome.z;
        }
    } else {
        mTarget = mHome;
    }
}

void P2HoudaiFsm::startStride(const P2HoudaiVec& pos, float face)
{
    // IKSystemMgr::setNextCentrePosition.
    mStrideT = 0.0f;
    mStrideFrom = pos;
    mFaceFrom = face;
    const float toTarget = std::atan2(mTarget.x - pos.x, mTarget.z - pos.z);
    float angDist = wrapPi(toTarget - face);
    P2HoudaiVec next = pos;
    const float view = mParms.ikViewAngleDeg * kPi / 180.0f;
    const float maxTurn = mParms.maxTurnDeg * kPi / 180.0f;
    if (std::fabs(angDist) <= view) {
        const float dist = distXZ(pos, mTarget);
        if (dist > mParms.strideLength && dist > 1.0e-6f) {
            next.x = pos.x + (mTarget.x - pos.x) / dist * mParms.strideLength;
            next.z = pos.z + (mTarget.z - pos.z) / dist * mParms.strideLength;
        } else {
            next.x = mTarget.x;
            next.z = mTarget.z;
        }
    } else if (std::fabs(angDist) > maxTurn) {
        angDist = angDist > 0.0f ? maxTurn : -maxTurn;
    }
    mStrideTo = next;
    mFaceTo = face + angDist;
}

P2HoudaiVec P2HoudaiFsm::gunOrigin(const P2HoudaiInput& in) const
{
    if (in.gunPosValid) return in.gunPos;
    return P2HoudaiVec{in.pos.x, in.pos.y + mParms.gunHeight * in.modelScale, in.pos.z};
}

P2HoudaiVec P2HoudaiFsm::gunDirection() const
{
    return P2HoudaiVec{std::sin(mTilt) * std::sin(mYaw), -std::cos(mTilt), std::sin(mTilt) * std::cos(mYaw)};
}

bool P2HoudaiFsm::poseAdvancing() const
{
    if (mStopped || mState == P2LongLegsState::Stay || mState == P2LongLegsState::Walk) return false;
    if (mState == P2LongLegsState::Dead && mFrame >= kDeadFrames) return false;
    const int le = loopEnd(mState);
    if (le >= 0 && mFrame >= le) return false;  // the loop seam is not continuous
    return true;
}

void P2HoudaiFsm::gunUpdate(const P2HoudaiInput& in)
{
    // HoudaiShotGunMgr::doUpdate: search rotation (always "locks on") or the
    // return to rest after finishRotation.
    if (!mRotation) return;
    if (mGunFinished) {
        mYaw = stepAngle(mYaw, mFace, 0.025f);
        mTilt = stepAngle(mTilt, 0.0f, 0.025f);
        if (std::fabs(wrapPi(mYaw - mFace)) < 0.01f && std::fabs(mTilt) < 0.01f) {
            mRotation = false;
            mLockOn = true;
        }
        return;
    }
    const P2HoudaiVec gun = gunOrigin(in);
    const float sx = mGunAim.x - gun.x, sy = mGunAim.y - gun.y, sz = mGunAim.z - gun.z;
    const float yawTarget = std::atan2(sx, sz);
    const float tiltTarget = std::atan2(std::sqrt(sx * sx + sz * sz), -sy); // from straight down
    mYaw = stepAngle(mYaw, yawTarget, 0.05f);
    mTilt = stepAngle(mTilt, tiltTarget, 0.05f);
    mLockOn = true; // searchShotGunRotation always returns true
}

void P2HoudaiFsm::emit(const P2HoudaiInput& in, P2HoudaiOutput& out)
{
    // HoudaiShotGunMgr::emitShotGun: gun x axis, per-axis jitter of
    // +-mAttackHitAngle, 45 units ahead of the gun joint, speed 600.
    float dx = std::sin(mTilt) * std::sin(mYaw);
    float dy = -std::cos(mTilt);
    float dz = std::sin(mTilt) * std::cos(mYaw);
    const float a = mParms.attackHitAngle;
    dx += clamp01(in.roll[1]) * 2.0f * a - a;
    dy += clamp01(in.roll[2]) * 2.0f * a - a;
    dz += clamp01(in.roll[3]) * 2.0f * a - a;
    const float len = std::sqrt(dx * dx + dy * dy + dz * dz);
    if (len > 1.0e-6f) { dx /= len; dy /= len; dz /= len; }
    out.fireShell = true;
    const P2HoudaiVec gun = gunOrigin(in);
    out.shellPos = P2HoudaiVec{gun.x + dx * mParms.gunMuzzle, gun.y + dy * mParms.gunMuzzle,
                               gun.z + dz * mParms.gunMuzzle};
    out.shellVel = P2HoudaiVec{dx * mParms.shellSpeed, dy * mParms.shellSpeed, dz * mParms.shellSpeed};
}

void P2HoudaiFsm::update(const P2HoudaiInput& in, P2HoudaiOutput& out)
{
    out = P2HoudaiOutput();
    out.from = mState;
    const float dt = kDelta;

    // addDamage (flickSpeed 1.0 per accepted hit) and updateShotGunTimer run
    // before the state exec.
    mFlickTimer += static_cast<float>(in.hits);
    if (in.tookDamage) mBurstTimer = 0.0f;
    else mBurstTimer += dt;

    const int key = mKey;
    mKey = -1;

    switch (mState) {
    case P2LongLegsState::Stay:
        if (in.damageAttempt || in.wake) enter(P2LongLegsState::Land, in, out);
        break;

    case P2LongLegsState::Land:
        if (key == 2 || key == 4 || key == 5 || key == 6 || key == kKeyEnd)
            requestFlick(out, 1.0f, 100.0f, 0.0f, "land");
        if (key == kKeyEnd) {
            if (in.health <= 0.0f) enter(P2LongLegsState::Dead, in, out);
            else if (isStartFlick(in.stuck)) enter(P2LongLegsState::Flick, in, out);
            else enter(P2LongLegsState::Wait, in, out);
        }
        break;

    case P2LongLegsState::Wait:
        mStateTimer += dt;
        if (in.health <= 0.0f) { mNext = P2LongLegsState::Dead; mHasNext = true; mFinish = true; }
        else if (isStartFlick(in.stuck)) { mNext = P2LongLegsState::Flick; mHasNext = true; mFinish = true; }
        else if (mBurstTimer > mParms.burstCooldown) { mNext = P2LongLegsState::Shot; mHasNext = true; mFinish = true; }
        else if (mStateTimer > mStateDuration) { mNext = P2LongLegsState::Walk; mHasNext = true; mFinish = true; }
        if (key == kKeyEnd && mHasNext) enter(mNext, in, out);
        break;

    case P2LongLegsState::Flick:
        if (key == 3) {
            requestFlick(out, mParms.shakeChance, mParms.shakeKnockback, mParms.shakeDamage, "flick");
            mFlickTimer = 0.0f;
        } else if (key == kKeyEnd) {
            enter(in.health <= 0.0f ? P2LongLegsState::Dead : P2LongLegsState::Shot, in, out);
        }
        break;

    case P2LongLegsState::Walk: {
        walkTargetRule(in);
        mStateTimer += dt;
        if (isStartFlick(in.stuck)) { mNext = P2LongLegsState::Flick; mHasNext = true; mIkInMotion = false; }
        else if (mStateTimer > mStateDuration) { mNext = P2LongLegsState::Wait; mHasNext = true; mIkInMotion = false; }
        const bool ikFinished = !mIkInMotion && mStrideT >= mParms.strideSeconds;
        if (in.health <= 0.0f) enter(P2LongLegsState::Dead, in, out);
        else if (ikFinished && mHasNext) enter(mNext, in, out);
        break;
    }

    case P2LongLegsState::Shot: {
        if (mStopped) {
            if (mShotState != 0) {
                if (mFinish || mSearchTimer > mParms.maxShootingOff) {
                    // setShotGunEmitKeepTimerOn
                    mSearchTimer = clamp01(in.roll[0]) * (mParms.maxShootingOn - mParms.minShootingOn);
                    mStopped = false;
                    out.burstOn = true;
                }
            } else if (mGunFinished) {
                if (mLockOn && mStateTimer > 2.0f) {
                    mShotState = 0;
                    mStateTimer = 0.0f;
                    mStopped = false;
                }
            } else if (mLockOn && mStateTimer > 2.0f) {
                mShotState = 1;
                mSearchTimer = 0.0f;
                mStateTimer = 0.0f;
                mStopped = false;
                out.burstOn = true;
            }
        }
        if (mRotation) {
            // setShotGunTargetPosition
            if (in.gunTargetFound) {
                mGunAim = in.gunTarget;
            } else if (mBurstTimer > 1.0f) {
                mBurstTimer = 0.0f;
                const float ang = clamp01(in.roll[1]) * kTau;
                const float dist = clamp01(in.roll[2]) * mParms.searchDistance;
                mGunAim = P2HoudaiVec{dist * std::sin(ang) + in.pos.x, in.pos.y,
                                      dist * std::cos(ang) + in.pos.z};
            }
            if (mStateTimer > mParms.maxAimSeconds) {
                mStateTimer = 0.0f;
                mFinish = true;
            }
        }
        mSearchTimer += dt;
        mStateTimer += dt;
        if (in.health <= 0.0f) {
            if (mStopped) mStopped = false;
            mFinish = true;
        }
        if (key == 2) {
            mStateTimer = 0.0f;
            mStopped = true;
            // startRotation: head/gun relative angles reset to rest.
            mRotation = true;
            mLockOn = false;
            mGunFinished = false;
            mYaw = mFace;
            mTilt = 0.0f;
            out.aimStart = true;
        } else if (key == 3) {
            if (!mFinish) {
                requestFlick(out, mParms.shakeChance, mParms.shakeKnockback, mParms.shakeDamage, "shot");
                mFlickTimer = 0.0f;
                emit(in, out);
            }
        } else if (key == 4) {
            if (!mFinish && mParms.maxAimSeconds - mStateTimer > mParms.maxShootingOff
                    && mSearchTimer > mParms.maxShootingOn) {
                // setShotGunEmitKeepTimerOff
                mSearchTimer = clamp01(in.roll[0]) * (mParms.maxShootingOff - mParms.minShootingOff);
                mStopped = true;
                out.burstOff = true;
            }
        } else if (key == 5) {
            mShotState = 0;
            mStateTimer = 0.0f;
            mStopped = true;
            mLockOn = false;     // finishRotation
            mGunFinished = true;
            out.aimEnd = true;
        } else if (key == kKeyEnd) {
            mRotation = false;
            enter(in.health <= 0.0f ? P2LongLegsState::Dead : P2LongLegsState::Walk, in, out);
        }
        break;
    }

    case P2LongLegsState::Dead:
        if (key == kKeyEnd) out.deadEnd = true;
        break;
    }

    // IK update (Houdai::updateIKSystem) after the state exec.
    out.moving = false;
    if (mIkActive && mState == P2LongLegsState::Walk) {
        if (mStrideT >= mParms.strideSeconds && mIkInMotion) {
            startStride(in.pos, mFace);
            out.strideStart = true;
            out.strideTo = mStrideTo;
            out.strideFace = mFaceTo;
        }
        if (mStrideT < mParms.strideSeconds) {
            mStrideT += dt;
            const float t = clamp01(mStrideT / mParms.strideSeconds);
            out.moving = true;
            out.bodyPos = P2HoudaiVec{mStrideFrom.x + (mStrideTo.x - mStrideFrom.x) * t, in.pos.y,
                                      mStrideFrom.z + (mStrideTo.z - mStrideFrom.z) * t};
            mFace = mFaceFrom + wrapPi(mFaceTo - mFaceFrom) * t;
        }
    }
    out.bodyFace = mFace;
    out.walkTarget = mTarget;

    // Shot-gun rotation (doUpdateShotGun) after the IK update.
    gunUpdate(in);

    // Animation advance: produces the key event read by the next exec.
    if (mState != P2LongLegsState::Stay && !out.entered && !mStopped && mState != P2LongLegsState::Walk) {
        if (!(mState == P2LongLegsState::Dead && mFrame >= kDeadFrames)) {
            ++mFrame;
            mKey = keyAt(mState, mFrame);
            const int le = loopEnd(mState);
            if (le >= 0 && mFrame == le && !mFinish) {
                mFrame = loopStart(mState); // loop back to key 0
            }
        }
    }

    // Body pose for the rig draw: the clip the current state plays, else hold the last one (Walk).
    {
        int clip = -1, last = 0;
        switch (mState) {
        case P2LongLegsState::Stay:
        case P2LongLegsState::Land: clip = kPoseLanding; last = kLandingFrames - 1; break;
        case P2LongLegsState::Wait: clip = kPoseWait; last = kWaitFrames - 1; break;
        case P2LongLegsState::Flick: clip = kPoseFlick; last = kFlickFrames - 1; break;
        case P2LongLegsState::Shot: clip = kPoseAttack; last = kAttackFrames - 1; break;
        case P2LongLegsState::Dead: clip = kPoseDead; last = kDeadFrames - 1; break;
        default: break;
        }
        if (clip >= 0) {
            mPoseClip = clip;
            mPoseFrame = mState == P2LongLegsState::Stay ? 0 : (mFrame < last ? mFrame : last);
        }
    }
    out.state = mState;
    out.drawHidden = mState == P2LongLegsState::Stay;
    out.landDrop = mState == P2LongLegsState::Land ? 1.0f - clamp01(mFrame / 100.0f) : 0.0f;
    out.damageRate = damageRateFor(mState);
}

float P2HoudaiFsm::damageRateFor(P2LongLegsState state) {
    switch (state) {
    case P2LongLegsState::Land: return 0.25f;
    case P2LongLegsState::Stay:
    case P2LongLegsState::Wait:
    case P2LongLegsState::Flick:
    case P2LongLegsState::Walk:
    case P2LongLegsState::Shot: return 1.0f;
    default: return 0.0f;
    }
}
