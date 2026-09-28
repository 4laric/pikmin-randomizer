#include "pc_p2_groink_map_trace.h"
#include "MapMgr.h"
#include <cmath>

namespace {
bool boundedTraceVector(const P2GroinkVec3& value) {
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z)
        && std::fabs(value.x) <= 100000.f && std::fabs(value.y) <= 100000.f
        && std::fabs(value.z) <= 100000.f;
}
}

void P2GroinkTraceProxy::clear() {
    wall = false;
    mGroundTriangle = nullptr;
    mCollisionOccurred = 0;
    mHasCollChangedVelocity = 0;
    mCurrCollisionModel = nullptr;
    mCollPlatform = nullptr;
    mCollNormal = nullptr;
    mPikiPlatformTriangle = nullptr;
}

void P2GroinkMapTrace::reset(MapMgr* map) {
    mMap = map;
    mProxy.clear();
    mCalls = mFloors = mWalls = 0;
}

bool P2GroinkMapTrace::trace(void* context, const P2GroinkVec3& center,
    const P2GroinkVec3& velocity, float delta, float radius, P2GroinkTraceResult& result) {
    if (!context || !boundedTraceVector(center) || !boundedTraceVector(velocity)
        || !std::isfinite(delta) || std::fabs(delta-P2GroinkPolicy::kSourceDelta)>1e-6f
        || radius != P2GroinkPolicy::kShellRadius) return false;
    auto& state = *static_cast<P2GroinkMapTrace*>(context);
    if (!state.mMap || !state.mMap->mMapModel) return false;
    state.mProxy.clear();
    // P1 accepts a sphere BASE, adding the radius before collision and
    // subtracting it afterward. The P2 shell policy stores its CENTER.
    MoveTrace movement(Vector3f(center.x, center.y-radius, center.z),
                       Vector3f(velocity.x, velocity.y, velocity.z), radius, true);
    state.mMap->traceMove(&state.mProxy, movement, delta);
    ++state.mCalls;
    P2GroinkTraceResult next;
    next.position = {movement.mPosition.x, movement.mPosition.y+radius, movement.mPosition.z};
    next.velocity = {movement.mVelocity.x, movement.mVelocity.y, movement.mVelocity.z};
    next.floor = state.mProxy.mGroundTriangle != nullptr;
    next.wall = state.mProxy.wall;
    if (!boundedTraceVector(next.position) || !boundedTraceVector(next.velocity)) return false;
    if (next.floor || next.wall) {
        next.groundY = state.mMap->getMinY(next.position.x, next.position.z, false);
        if (!std::isfinite(next.groundY)) return false;
        next.hasGroundY = true;
    }
    state.mFloors += next.floor;
    state.mWalls += next.wall;
    result = next;
    return true;
}
