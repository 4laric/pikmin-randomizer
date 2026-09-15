#include "pc_p2_rock_host.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include <cmath>
#include <cstdint>

namespace p2rockhost {

void TraceProxy::clear()
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

void TraceProxy::refresh(Graphics&) {}
void TraceProxy::wallCallback(immut Plane&, DynCollObject*) { wall = true; }
void TraceProxy::doKill() {}

bool RockMapBinding::trace(void* context, const P2RockHazardVec3& center,
                           const P2RockHazardVec3& velocity, float delta, float radius,
                           P2RockHazardTraceResult& result)
{
    if (!context || !std::isfinite(center.x) || !std::isfinite(center.y)
        || !std::isfinite(center.z) || !std::isfinite(velocity.x)
        || !std::isfinite(velocity.y) || !std::isfinite(velocity.z)
        || !std::isfinite(delta) || std::fabs(delta - P2RockHazard::kSourceDelta) > 0.000001f
        || !std::isfinite(radius) || radius <= 0.0f) {
        return false;
    }
    RockMapBinding& self = *static_cast<RockMapBinding*>(context);
    if (!self.mMap || !self.mMap->mMapModel) {
        return false;
    }
    self.mProxy.clear();
    const Vector3f base(center.x, center.y - radius, center.z);
    MoveTrace movement(base, Vector3f(velocity.x, velocity.y, velocity.z), radius, true);
    self.mMap->traceMove(&self.mProxy, movement, delta);
    ++self.mCalls;
    result.position = { movement.mPosition.x, movement.mPosition.y + radius,
                        movement.mPosition.z };
    result.velocity = { movement.mVelocity.x, movement.mVelocity.y,
                        movement.mVelocity.z };
    result.floorTriangle = self.mProxy.mGroundTriangle != nullptr;
    result.colliding = false;
    if (!std::isfinite(result.position.x) || !std::isfinite(result.position.y)
        || !std::isfinite(result.position.z) || !std::isfinite(result.velocity.x)
        || !std::isfinite(result.velocity.y) || !std::isfinite(result.velocity.z)) {
        return false;
    }
    self.mFloors += static_cast<std::uint64_t>(result.floorTriangle);
    return true;
}

float ScriptRng::next()
{
    state = state * 1664525u + 1013904223u;
    return static_cast<float>((state >> 8) & 0xffffffu) / 16777216.0f;
}

int ScriptRng::nextInt(int count)
{
    if (count <= 0) {
        return 0;
    }
    int value = static_cast<int>(next() * static_cast<float>(count));
    return value >= count ? count - 1 : value;
}

float rngFloat(void* context) { return static_cast<ScriptRng*>(context)->next(); }
int rngInt(void* context, int count) { return static_cast<ScriptRng*>(context)->nextInt(count); }

P2RockHazardDetection detectRock(const P2RockHazardVec3& from, float sightRadius)
{
    P2RockHazardDetection detection;
    const float sightSq = sightRadius * sightRadius;
    auto inRange = [&](const Creature* creature) {
        const Vector3f& p = creature->mSRT.t;
        const float dx = p.x - from.x, dy = p.y - from.y, dz = p.z - from.z;
        return dx * dx + dy * dy + dz * dz <= sightSq;
    };
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi && navi->isAlive() && inRange(navi)) {
        detection.olimarInSight = true;
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (piki && piki->isAlive() && inRange(piki)) {
                detection.pikminInSight = true;
                break;
            }
        }
    }
    return detection;
}

} // namespace p2rockhost
