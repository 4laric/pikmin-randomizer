#include "pc_p2_bombsarai_map_trace.h"
#include "MapMgr.h"
#include <cmath>
#include <limits>

namespace {
bool boundedTraceVector(const P2BombSaraiVec3& value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z)
        && std::fabs(value.x) <= 100000.0f && std::fabs(value.y) <= 100000.0f
        && std::fabs(value.z) <= 100000.0f;
}
}

void P2BombSaraiTraceProxy::clear()
{
    wall = false;
    mGroundTriangle = nullptr;
    mCollisionOccurred = 0;
    mHasCollChangedVelocity = 0;
    mCurrCollisionModel = nullptr;
    mCollPlatform = nullptr;
    mCollNormal = nullptr;
    mPikiPlatformTriangle = nullptr;
}

void P2BombSaraiMapBinding::reset(MapMgr* map)
{
    mMap = map;
    mProxy.clear();
    mCalls = mFloors = mWalls = 0;
}

bool P2BombSaraiMapBinding::traceMove(void* context, const P2BombSaraiVec3& sphereBase,
                                      const P2BombSaraiVec3& velocity, float radius, float delta,
                                      P2BombSaraiRawTrace& result)
{
    if (!context || !boundedTraceVector(sphereBase) || !boundedTraceVector(velocity)
        || !std::isfinite(delta)
        || std::fabs(delta - P2BombSaraiBomb::kSourceDelta) > 0.000001f
        || !std::isfinite(radius) || radius <= 0.0f) {
        return false;
    }
    P2BombSaraiMapBinding& self = *static_cast<P2BombSaraiMapBinding*>(context);
    if (!self.mMap || !self.mMap->mMapModel) {
        return false;
    }
    self.mProxy.clear();
    // The adapter already converted center to base; P1 accepts the sphere
    // base and adds the radius internally. ignoreDynColl=true: static-map-
    // only testing, explicitly labeled (Groink prototype doc).
    MoveTrace movement(Vector3f(sphereBase.x, sphereBase.y, sphereBase.z),
                       Vector3f(velocity.x, velocity.y, velocity.z), radius, true);
    self.mMap->traceMove(&self.mProxy, movement, delta);
    ++self.mCalls;
    result.position = { movement.mPosition.x, movement.mPosition.y, movement.mPosition.z };
    result.velocity = { movement.mVelocity.x, movement.mVelocity.y, movement.mVelocity.z };
    result.groundTriangle = self.mProxy.mGroundTriangle != nullptr;
    result.wall = self.mProxy.wall;
    if (!boundedTraceVector(result.position) || !boundedTraceVector(result.velocity)) {
        return false;
    }
    self.mFloors += result.groundTriangle;
    self.mWalls += result.wall;
    return true;
}

float P2BombSaraiMapBinding::getMinY(void* context, float x, float z)
{
    if (!context || !std::isfinite(x) || !std::isfinite(z)) {
        return std::numeric_limits<float>::quiet_NaN(); // adapter rejects non-finite samples
    }
    P2BombSaraiMapBinding& self = *static_cast<P2BombSaraiMapBinding*>(context);
    if (!self.mMap) {
        return std::numeric_limits<float>::quiet_NaN();
    }
    return self.mMap->getMinY(x, z, false);
}
