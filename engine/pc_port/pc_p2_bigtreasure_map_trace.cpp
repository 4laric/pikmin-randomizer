#include "pc_p2_bigtreasure_map_trace.h"
#include "MapMgr.h"
#include <cmath>

namespace {
constexpr float kTraceCoordinateLimit = 100000.0f;
constexpr float kSourceDelta = 1.0f / 30.0f;
constexpr float kElecTraceRadius = 20.0f;

bool boundedTraceVector(const P2BigTreasureVec3& value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z)
        && std::fabs(value.x) <= kTraceCoordinateLimit && std::fabs(value.y) <= kTraceCoordinateLimit
        && std::fabs(value.z) <= kTraceCoordinateLimit;
}
} // namespace

void P2BigTreasureTraceProxy::clear()
{
    wall                    = false;
    mGroundTriangle         = nullptr;
    mCollisionOccurred      = 0;
    mHasCollChangedVelocity = 0;
    mCurrCollisionModel     = nullptr;
    mCollPlatform           = nullptr;
    mCollNormal             = nullptr;
    mPikiPlatformTriangle   = nullptr;
}

void P2BigTreasureMapTrace::reset(MapMgr* map)
{
    mMap = map;
    mProxy.clear();
    mCalls = mFloors = mWalls = 0;
}

bool P2BigTreasureMapTrace::trace(void* context, const P2BigTreasureVec3& position,
                                  const P2BigTreasureVec3& velocity, float delta, float radius,
                                  float bounceFactor, P2BigTreasureTraceResult& result)
{
    if (!context || !boundedTraceVector(position) || !boundedTraceVector(velocity)
        || !std::isfinite(delta) || std::fabs(delta - kSourceDelta) > 1e-6f
        || radius != kElecTraceRadius || !std::isfinite(bounceFactor) || bounceFactor <= 0.0f
        || bounceFactor > 1.0f) {
        return false;
    }
    P2BigTreasureMapTrace& state = *static_cast<P2BigTreasureMapTrace*>(context);
    if (!state.mMap || !state.mMap->mMapModel) {
        return false;
    }
    state.mProxy.clear();
    // P1 accepts a sphere BASE, adding the radius before collision and
    // subtracting it afterward. The P2 policies store sphere CENTERS.
    MoveTrace movement(Vector3f(position.x, position.y - radius, position.z),
                       Vector3f(velocity.x, velocity.y, velocity.z), radius, true);
    state.mMap->traceMove(&state.mProxy, movement, delta);
    ++state.mCalls;
    P2BigTreasureTraceResult next;
    next.position = P2BigTreasureVec3{ movement.mPosition.x, movement.mPosition.y + radius,
                                       movement.mPosition.z };
    next.velocity = P2BigTreasureVec3{ movement.mVelocity.x, movement.mVelocity.y,
                                       movement.mVelocity.z };
    next.floor    = state.mProxy.mGroundTriangle != nullptr;
    next.wall     = state.mProxy.wall;
    if (!boundedTraceVector(next.position) || !boundedTraceVector(next.velocity)) {
        return false;
    }
    if (next.floor || next.wall) {
        next.groundY = state.mMap->getMinY(next.position.x, next.position.z, false);
        if (!std::isfinite(next.groundY)) {
            return false;
        }
        next.hasGroundY = true;
    }
    state.mFloors += next.floor;
    state.mWalls += next.wall;
    result = next;
    return true;
}

bool P2BigTreasureMapTrace::ground(void* context, float x, float z, float* outY)
{
    if (!context || !outY || !std::isfinite(x) || !std::isfinite(z)
        || std::fabs(x) > kTraceCoordinateLimit || std::fabs(z) > kTraceCoordinateLimit) {
        return false;
    }
    P2BigTreasureMapTrace& state = *static_cast<P2BigTreasureMapTrace*>(context);
    if (!state.mMap || !state.mMap->mMapModel) {
        return false;
    }
    float y = state.mMap->getMinY(x, z, false);
    if (!std::isfinite(y)) {
        return false;
    }
    *outY = y;
    return true;
}
