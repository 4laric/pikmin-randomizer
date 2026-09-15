#include "pc_p2_waterwraith.h"

#include <cmath>

namespace {
constexpr float kShadowRampPerSecond = 1.0f; // reaches full scale ~1 s after the fall
} // namespace

P2WaterwraithRig::P2WaterwraithRig(float properRotationSpeed)
    : mProperRotationSpeed(properRotationSpeed)
{
}

bool P2WaterwraithRig::birth()
{
    if (mAlive) {
        return false;
    }
    mAlive        = true;
    mAttached     = true;
    mInvulnerable = false;
    mTyre         = P2TYRE_Land; // tyre.cpp:79
    mWraith       = P2BM_Walk;
    mHealth       = kTyreMaxHealth;
    mPosition     = P2WaterwraithVec3{};
    mVelocity     = P2WaterwraithVec3{};
    mFacing       = 0.0f;
    mScale        = 1.0f;
    mDistance     = 0.0f;
    mRollAngle    = 0.0f;
    mFalling      = false;
    mShadow       = kShadowMinScale;
    return true;
}

void P2WaterwraithRig::push(const P2WaterwraithVec3& position, const P2WaterwraithVec3& velocity,
                            float facing, float scale)
{
    if (!mAlive) {
        return;
    }
    if (mTyre == P2TYRE_Move || mTyre == P2TYRE_Land) {
        const float dx = position.x - mPosition.x;
        const float dz = position.z - mPosition.z;
        const float step = std::sqrt(dx * dx + dz * dz);
        mDistance += step;
        // Roll rate = distance / circumference, scaled by the proper fp01.
        mRollAngle += (step / kRollerCircumference) * mProperRotationSpeed;
    }
    mPosition = position;
    mVelocity = velocity;
    mFacing   = facing;
    mScale    = scale;
}

bool P2WaterwraithRig::landFloorContact()
{
    if (!mAlive || mTyre != P2TYRE_Land) {
        return false;
    }
    mTyre = P2TYRE_Freeze; // tyreState.cpp:105-115 (flick then freeze)
    return true;
}

bool P2WaterwraithRig::moveRestart()
{
    if (!mAlive || mTyre != P2TYRE_Freeze || !mAttached) {
        return false;
    }
    mTyre = P2TYRE_Move; // Tyre.cpp:565-572
    return true;
}

bool P2WaterwraithRig::quakeFreeze()
{
    if (!mAlive || mTyre != P2TYRE_Move) {
        return false;
    }
    mTyre = P2TYRE_Freeze; // tyre.cpp:347-353
    return true;
}

bool P2WaterwraithRig::damageable() const
{
    if (!mAlive || mTyre == P2TYRE_Dead) {
        return false;
    }
    // Stickable only while frozen, or once the wraith has dismounted.
    return mTyre == P2TYRE_Freeze || mInvulnerable;
}

bool P2WaterwraithRig::applyDamage(float damage, bool* outDead)
{
    if (outDead) {
        *outDead = false;
    }
    if (!damageable() || !(damage > 0.0f)) {
        return false;
    }
    mHealth -= damage;
    if (mHealth < 0.0f) {
        mHealth = 0.0f;
    }
    // Death is gated on the dismounted EB_Invulnerable flag even at zero HP.
    if (outDead) {
        *outDead = mHealth <= 0.0f && mInvulnerable;
    }
    return true;
}

void P2WaterwraithRig::dismount()
{
    if (!mAlive) {
        return;
    }
    mAttached     = false;
    mInvulnerable = true;
    if (mTyre == P2TYRE_Move) {
        mTyre = P2TYRE_Freeze;
    }
}

bool P2WaterwraithRig::beginDead()
{
    if (!mAlive || mTyre == P2TYRE_Dead || !mInvulnerable || mHealth > 0.0f) {
        return false;
    }
    mTyre = P2TYRE_Dead; // tyre_getoff
    return true;
}

bool P2WaterwraithRig::finishDead()
{
    if (!mAlive || mTyre != P2TYRE_Dead) {
        return false;
    }
    mAlive    = false;
    mAttached = false;
    return true;
}

float P2WaterwraithRig::rideRegen(bool riding) const
{
    if (!mAlive || !mAttached || !riding) {
        return 0.0f;
    }
    return kRideRegenPerTick; // blackMan.cpp:843-848
}

void P2WaterwraithRig::beginFall()
{
    mFalling = true;
    mShadow  = kShadowMinScale;
}

float P2WaterwraithRig::tickShadow(float delta)
{
    if (mFalling && delta > 0.0f) {
        mShadow += kShadowRampPerSecond * delta;
        if (mShadow > kShadowMaxScale) {
            mShadow = kShadowMaxScale;
        }
    }
    return mShadow;
}
