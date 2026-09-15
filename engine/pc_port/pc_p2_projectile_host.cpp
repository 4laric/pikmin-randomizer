#include "pc_p2_projectile_host.h"

#include <cmath>

namespace {
bool finite(float value) { return std::isfinite(value); }
bool finite(const P2CannonStoneVec3& value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}

// Same bound as the Groink/BombSarai adapters: rejects NaN/Inf and absurd
// coordinates before they reach the host trace.
bool bounded(const P2CannonStoneVec3& value)
{
    return finite(value) && std::fabs(value.x) <= 100000.0f
        && std::fabs(value.y) <= 100000.0f && std::fabs(value.z) <= 100000.0f;
}
} // namespace

void P2ProjectileHostAdapter::reset(P2ProjectileHostTraceFn traceFn, void* traceContext,
                                    P2ProjectileHostTokenLiveFn tokenLiveFn, void* tokenLiveContext)
{
    mTrace = traceFn;
    mTraceContext = traceContext;
    mTokenLive = tokenLiveFn;
    mTokenLiveContext = tokenLiveContext;
}

P2CannonStoneTarget P2ProjectileHostAdapter::selectTarget(
    const P2CannonStoneVec3& origin, const P2ProjectileHostCandidateSnapshot& snapshot,
    float sightRadius)
{
    P2CannonStoneTarget target;
    if (!finite(origin) || !finite(sightRadius)) {
        return target;
    }

    // Active Navi first, unconditionally (Rock.cpp:372-374). A non-finite
    // supplied position is ignored and selection falls through.
    if (snapshot.hasActiveNavi && finite(snapshot.activeNaviPosition)) {
        target.hasTarget = true;
        target.position = snapshot.activeNaviPosition;
        return target;
    }

    if (!snapshot.candidates || snapshot.candidateCount <= 0) {
        return target;
    }

    const bool unlimited = sightRadius < 0.0f; // getNearestPikminOrNavi semantics
    const float sightSquared = unlimited ? 0.0f : sightRadius * sightRadius;
    float bestSquared = 0.0f;
    for (int i = 0; i < snapshot.candidateCount; ++i) {
        const P2ProjectileHostCandidate& candidate = snapshot.candidates[i];
        if (!candidate.alive || !finite(candidate.position)) {
            continue;
        }
        // Rock.cpp:376 passes a 180-degree searchAngle to getNearestPikminOrNavi
        // (enemyAction.cpp:21 converts it with TORADIANS, :45 tests
        // |angDist| <= searchAngle), so every horizontal angle passes and only
        // the 2D x/z distance below filters. There is no y constraint.
        const float dx = candidate.position.x - origin.x;
        const float dz = candidate.position.z - origin.z;
        const float squared = dx * dx + dz * dz;
        if (!unlimited && squared > sightSquared) {
            continue;
        }
        if (!target.hasTarget || squared < bestSquared) {
            target.hasTarget = true;
            target.position = candidate.position;
            bestSquared = squared;
        }
    }
    return target;
}

bool P2ProjectileHostAdapter::trace(void* context, const P2CannonStoneVec3& center,
                                    const P2CannonStoneVec3& velocity, float delta, float radius,
                                    P2CannonStoneTraceResult& result)
{
    if (!context || !bounded(center) || !bounded(velocity) || !finite(delta)
        || std::fabs(delta - P2CannonStone::kSourceDelta) > 0.000001f
        || !finite(radius) || radius <= 0.0f) {
        return false;
    }
    P2ProjectileHostAdapter& self = from(context);
    if (!self.mTrace) {
        return false;
    }

    // Center-space host trace: no P1 radius base/center conversion here.
    P2ProjectileHostTrace raw;
    if (!self.mTrace(self.mTraceContext, center, velocity, delta, radius, raw)) {
        return false;
    }
    if (!bounded(raw.position) || !bounded(raw.velocity)) {
        return false;
    }
    if ((raw.floor || raw.wall) && (!raw.hasGroundY || !finite(raw.groundY))) {
        return false; // contact without a terrain sample: never invent ground
    }

    result.position = raw.position;
    result.velocity = raw.velocity;
    result.wall = raw.wall;
    return true;
}

P2ProjectileHostStrikeResult P2ProjectileHostAdapter::contact(P2CannonStone& stone,
                                                              P2CannonStoneContactKind kind,
                                                              bool targetOnFloor, bool targetIsRock,
                                                              std::uint64_t targetToken) const
{
    P2ProjectileHostStrikeResult result;
    result.contact = stone.contact(kind, targetOnFloor, targetIsRock, targetToken);
    if (!result.contact.strikeEmitted) {
        return result;
    }

    const P2CannonStoneStrike& strike = result.contact.strike;
    result.targetLive = tokenLive(strike.targetToken);
    result.attributedLive = tokenLive(strike.attributedToken);
    // A stale target cannot receive the strike; the host must not route it.
    result.unreachable = !result.targetLive;
    // Source-enemy attribution falls back to the Stone itself when the
    // attributed token is not live (BombSarai stale-carrier pattern).
    result.attributionToken = result.attributedLive ? strike.attributedToken : stone.selfToken();
    return result;
}

bool P2ProjectileHostAdapter::tokenLive(std::uint64_t token) const
{
    if (token == 0 || !mTokenLive) {
        return false;
    }
    return mTokenLive(mTokenLiveContext, token);
}
