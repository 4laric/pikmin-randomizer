#include "pc_p2_bombsarai_bomb.h"

#include <cmath>

namespace {
bool finite(float value) { return std::isfinite(value); }
bool finite(const P2BombSaraiVec3& value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}
bool validConfig(const P2BombSaraiBombConfig& config)
{
    return finite(config.gravityPerTick) && config.gravityPerTick >= 0.0f
        && finite(config.fuseHealth) && config.fuseHealth > 0.0f
        && config.armLoopTicks > 0
        && finite(config.bombRadius) && config.bombRadius > 0.0f
        && finite(config.blastRadius) && config.blastRadius > 0.0f
        && finite(config.blastHalfHeight) && config.blastHalfHeight >= 0.0f
        && finite(config.tekiDamage) && config.tekiDamage >= 0.0f
        && finite(config.naviPikiDamage) && config.naviPikiDamage >= 0.0f
        && config.ip02TriggerLimit >= 0;
}
bool livePhase(P2BombSaraiBombPhase phase)
{
    return phase == P2BombSaraiBombPhase::Captured
        || phase == P2BombSaraiBombPhase::InFlight
        || phase == P2BombSaraiBombPhase::ArmedLoop
        || phase == P2BombSaraiBombPhase::Burning;
}
}

void P2BombSaraiBomb::reset(const P2BombSaraiBombConfig& config)
{
    mConfig = config;
    mPhase = P2BombSaraiBombPhase::Inactive;
    mPosition = P2BombSaraiVec3{};
    mVelocity = P2BombSaraiVec3{};
    mCarrierToken = 0;
    mEscapeTicks = 0;
    mArmTicksRemaining = 0;
    mFuseHealthRemaining = 0.0f;
    mDetonateDelayTicks = 0;
    mInductionCounter = 0;
    clearBlast();
}

P2BombSaraiVec3 P2BombSaraiBomb::throwVelocity(P2BombSaraiThrowKind kind, float faceDir)
{
    switch (kind) {
    case P2BombSaraiThrowKind::Release:
        return { 50.0f * std::sin(faceDir), 100.0f, 50.0f * std::cos(faceDir) };
    case P2BombSaraiThrowKind::Fall:
        return { 100.0f * std::sin(faceDir), 300.0f, 100.0f * std::cos(faceDir) };
    case P2BombSaraiThrowKind::Death:
    default:
        return { 0.0f, 0.0f, 0.0f };
    }
}

bool P2BombSaraiBomb::capture(std::uint64_t carrierToken, const P2BombSaraiVec3& jointPosition)
{
    if (mPhase != P2BombSaraiBombPhase::Inactive || !validConfig(mConfig)
        || !finite(jointPosition)) {
        return false;
    }
    mCarrierToken = carrierToken;
    mPosition = jointPosition;
    mVelocity = P2BombSaraiVec3{};
    mEscapeTicks = 0;
    mInductionCounter = mConfig.ip02TriggerLimit; // ip02 armed at capture
    mPhase = P2BombSaraiBombPhase::Captured;
    return true;
}

bool P2BombSaraiBomb::followJoint(const P2BombSaraiVec3& jointPosition)
{
    if (mPhase != P2BombSaraiBombPhase::Captured || !finite(jointPosition)) {
        return false;
    }
    mPosition = jointPosition;
    return true;
}

bool P2BombSaraiBomb::throwBomb(P2BombSaraiThrowKind kind, float faceDir)
{
    // Source: throwBomb clears mHeldBomb unconditionally and is a no-op on
    // null; only a captured bomb can be thrown by this policy.
    if (mPhase != P2BombSaraiBombPhase::Captured || !finite(faceDir)) {
        return false;
    }
    mVelocity = throwVelocity(kind, faceDir);
    if (!finite(mVelocity)) {
        return false;
    }
    mEscapeTicks = 0; // StateWait init resets the escape counter (bombState.cpp:43)
    mPhase = P2BombSaraiBombPhase::InFlight;
    return true;
}

void P2BombSaraiBomb::detonate(P2BombSaraiCarrierFn carrier, void* carrierContext)
{
    mBlast = P2BombSaraiBlastEvent{};
    mBlast.center = mPosition;
    mBlast.radius = mConfig.blastRadius;
    mBlast.halfHeight = mConfig.blastHalfHeight;
    mBlast.tekiDamage = mConfig.tekiDamage;
    mBlast.naviPikiDamage = mConfig.naviPikiDamage;
    mBlast.carrierToken = mCarrierToken;
    mBlast.hasCarrier = true;
    // Stale-mCarrier handling: resolve liveness at blast time; an
    // unconfirmed carrier falls back to bomb-self attribution (source
    // mCarrier==nullptr branch), never a dereferenced stale object.
    mBlast.carrierValid = carrier && carrier(carrierContext, mCarrierToken);
    mHasBlast = true;
    mPhase = P2BombSaraiBombPhase::Despawned;
}

bool P2BombSaraiBomb::induce(P2BombSaraiCarrierFn carrier, void* carrierContext)
{
    // Bomb-on-bomb induction: an armed/burning bomb whose blast window
    // reaches another bomb drains that bomb's ip02 trigger-limit counter
    // (bomb.cpp:348-368, 426-440). Only foreign-hosted induce() calls from a
    // detonating bomb reach here: the bomb itself is never a candidate (the
    // host excludes it, source creature != enemy).
    if (mPhase != P2BombSaraiBombPhase::ArmedLoop
        && mPhase != P2BombSaraiBombPhase::Burning) {
        return false;
    }
    if (mInductionCounter <= 0) {
        return false; // spent (0) or disabled; never re-detonates
    }
    if (--mInductionCounter == 0) {
        detonate(carrier, carrierContext);
        return true;
    }
    return false;
}

bool P2BombSaraiBomb::update(float delta, P2BombSaraiTraceFn trace, void* traceContext,
                             P2BombSaraiCarrierFn carrier, void* carrierContext)
{
    if (!livePhase(mPhase) || !finite(delta)
        || std::fabs(delta - kSourceDelta) > 0.000001f) {
        return false;
    }

    // Captured bombs are constrained and invulnerable (bomb.cpp:23-44); the
    // host moves them with the capture joint. Nothing advances here.
    if (mPhase == P2BombSaraiBombPhase::Captured) {
        return true;
    }

    // Escaped-capture despawn counter runs in BOMB_Wait only, i.e. the
    // InFlight and ArmedLoop phases (bombState.cpp:50-58); BOMB_Bomb resets
    // and stops it (StateBomb init, :97-103).
    if (mPhase == P2BombSaraiBombPhase::InFlight || mPhase == P2BombSaraiBombPhase::ArmedLoop) {
        ++mEscapeTicks;
        if (mEscapeTicks > kEscapeTimeoutTicks) {
            mPhase = P2BombSaraiBombPhase::Despawned;
            return true;
        }
    }

    if (mPhase == P2BombSaraiBombPhase::InFlight) {
        if (!finite(mPosition) || !finite(mVelocity)) {
            mPhase = P2BombSaraiBombPhase::Despawned;
            return false;
        }
        bool floorContact = false;
        P2BombSaraiTraceResult traced;
        bool tracedOk = trace && trace(traceContext, mPosition, mVelocity, delta,
                                       mConfig.bombRadius, traced);
        if (tracedOk) {
            if (!finite(traced.position) || !finite(traced.velocity)) {
                mPhase = P2BombSaraiBombPhase::Despawned;
                return false;
            }
            mPosition = traced.position;
            mVelocity = traced.velocity;
            if (traced.floor) {
                if (!traced.hasGroundY || !finite(traced.groundY)) {
                    mPhase = P2BombSaraiBombPhase::Despawned;
                    return false;
                }
                // Landing arms the fuse: floor triangle + escaped capture
                // passes isAnimStart (bomb.cpp:468-476).
                floorContact = true;
            }
            // Wall contact alone does not arm; the bomb keeps the
            // trace-mutated velocity and stays in flight (bounce handling is
            // host-owned, bomb.cpp:383-408 applies only to drop-group births).
        } else {
            mPosition.x += mVelocity.x * delta;
            mPosition.y += mVelocity.y * delta;
            mPosition.z += mVelocity.z * delta;
        }
        mVelocity.y -= mConfig.gravityPerTick;
        if (!finite(mPosition) || !finite(mVelocity)) {
            mPhase = P2BombSaraiBombPhase::Despawned;
            return false;
        }
        if (floorContact) {
            mVelocity = P2BombSaraiVec3{};
            mArmTicksRemaining = mConfig.armLoopTicks;
            mFuseHealthRemaining = mConfig.fuseHealth;
            mPhase = P2BombSaraiBombPhase::ArmedLoop;
        }
        return true;
    }

    if (mPhase == P2BombSaraiBombPhase::ArmedLoop) {
        // Hit-loop plays while fuse health drains at 1.0 per source second
        // (bombState.cpp:60-69). The loop ends on its animation length, then
        // transits to BOMB_Bomb (:76-79); health does not detonate early here.
        mFuseHealthRemaining -= delta * 1.0f;
        if (--mArmTicksRemaining <= 0) {
            mDetonateDelayTicks = 0; // StateBomb init (bombState.cpp:102)
            mPhase = P2BombSaraiBombPhase::Burning;
        }
        return true;
    }

    // Burning (BOMB_Bomb): health keeps draining; once at zero, a fixed
    // 10-tick delay precedes detonation (bombState.cpp:109-117).
    mFuseHealthRemaining -= delta * 1.0f;
    if (mFuseHealthRemaining <= 0.0f) {
        if (++mDetonateDelayTicks >= kDetonateDelayTicks) {
            detonate(carrier, carrierContext);
        }
    }
    return true;
}

int P2BombSaraiBombPool::activeCount() const
{
    int count = 0;
    for (int i = 0; i < mCapacity && i < kMaxBombs; ++i) {
        if (mUsed[i] && livePhase(mBombs[i].phase())) {
            ++count;
        }
    }
    return count;
}

bool P2BombSaraiBombPool::slotLive(int slot) const
{
    return slot >= 0 && slot < mCapacity && slot < kMaxBombs
        && mUsed[slot] && livePhase(mBombs[slot].phase());
}

P2BombSaraiBomb* P2BombSaraiBombPool::bombAt(int slot)
{
    return (slot >= 0 && slot < mCapacity && slot < kMaxBombs) ? &mBombs[slot] : nullptr;
}

const P2BombSaraiBomb* P2BombSaraiBombPool::bombAt(int slot) const
{
    return (slot >= 0 && slot < mCapacity && slot < kMaxBombs) ? &mBombs[slot] : nullptr;
}

P2BombSaraiBomb* P2BombSaraiBombPool::supply(std::uint64_t carrierToken,
                                             const P2BombSaraiVec3& jointPosition,
                                             const P2BombSaraiBombConfig& config)
{
    if (!finite(jointPosition)) {
        return nullptr;
    }
    const int limit = mCapacity < kMaxBombs ? mCapacity : kMaxBombs;
    for (int i = 0; i < limit; ++i) {
        if (mUsed[i] && mBombs[i].phase() == P2BombSaraiBombPhase::Captured
            && mBombs[i].carrierToken() == carrierToken) {
            return nullptr; // source !mHeldBomb guard: one HELD bomb per carrier
        }
    }
    for (int i = 0; i < limit; ++i) {
        const bool free = !mUsed[i] || !livePhase(mBombs[i].phase());
        if (!free) {
            continue;
        }
        mBombs[i].reset(config);
        if (!mBombs[i].capture(carrierToken, jointPosition)) {
            return nullptr;
        }
        mUsed[i] = true;
        return &mBombs[i];
    }
    return nullptr; // exhausted: silent tolerance, no partial state
}
