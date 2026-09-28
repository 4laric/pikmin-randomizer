#include "pc_p2_bombsarai_terrain.h"

#include <cmath>

namespace {
// Same bound as the Groink adapter: rejects NaN/Inf and absurd coordinates.
bool bounded(const P2BombSaraiVec3& value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z)
        && std::fabs(value.x) <= 100000.0f && std::fabs(value.y) <= 100000.0f
        && std::fabs(value.z) <= 100000.0f;
}
}

void P2BombSaraiTerrainAdapter::reset(P2BombSaraiTraceMoveFn traceMove, void* traceMoveContext,
                                      P2BombSaraiGetMinYFn getMinYFn, void* getMinYContext)
{
    mTraceMove = traceMove;
    mTraceMoveContext = traceMoveContext;
    mGetMinY = getMinYFn;
    mGetMinYContext = getMinYContext;
}

bool P2BombSaraiTerrainAdapter::trace(void* context, const P2BombSaraiVec3& center,
                                      const P2BombSaraiVec3& velocity, float delta, float radius,
                                      P2BombSaraiTraceResult& result)
{
    if (!context || !bounded(center) || !bounded(velocity) || !std::isfinite(delta)
        || std::fabs(delta - P2BombSaraiBomb::kSourceDelta) > 0.000001f
        || !std::isfinite(radius) || radius <= 0.0f) {
        return false;
    }
    P2BombSaraiTerrainAdapter& self = from(context);
    if (!self.mTraceMove || !self.mGetMinY) {
        return false;
    }

    // Center-to-base conversion: P1 traceMove adds the radius before
    // collision and subtracts it afterward, so hand it the sphere base.
    const P2BombSaraiVec3 base{ center.x, center.y - radius, center.z };
    P2BombSaraiRawTrace raw;
    if (!self.mTraceMove(self.mTraceMoveContext, base, velocity, radius, delta, raw)) {
        return false;
    }

    P2BombSaraiTraceResult next;
    next.position = { raw.position.x, raw.position.y + radius, raw.position.z };
    next.velocity = raw.velocity;
    next.floor = raw.groundTriangle;
    next.wall = raw.wall;
    if (!bounded(next.position) || !bounded(next.velocity)) {
        return false;
    }

    if (next.floor || next.wall) {
        const float groundY = self.mGetMinY(self.mGetMinYContext, next.position.x, next.position.z);
        if (!std::isfinite(groundY)) {
            return false; // contact without a terrain sample: never invent ground
        }
        next.groundY = groundY;
        next.hasGroundY = true;
        if (next.floor && next.position.y < groundY) {
            // Landing correction: clamp the center to the sampled terrain.
            // The Groink shell used ground+10 because its source raises a
            // below-ground+20 shell to ground+10; the source bomb rests on
            // its floor triangle without that offset, so the clamp target is
            // the ground itself. Any visual rest offset is a converter/asset
            // input owned by the host, not this adapter.
            next.position.y = groundY;
        }
    }

    result = next;
    return true;
}

bool P2BombSaraiTerrainAdapter::getMinY(void* context, float x, float z, float& outY)
{
    if (!context || !std::isfinite(x) || !std::isfinite(z)) {
        return false;
    }
    P2BombSaraiTerrainAdapter& self = from(context);
    if (!self.mGetMinY) {
        return false;
    }
    const float y = self.mGetMinY(self.mGetMinYContext, x, z);
    if (!std::isfinite(y)) {
        return false;
    }
    outY = y;
    return true;
}
