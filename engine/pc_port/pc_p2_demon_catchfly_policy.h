#pragma once
#include "pc_p2_demon_attack_window.h"
#include <cmath>
#include <algorithm>
#include <cstdint>

// Bounded translation of SaraiState::StateCatchFly::exec. Physics and turning
// remain owned by the native actor; this only exposes the source decision order.
namespace p2demon {
using HeightNext = P2DemonHeightNext;
struct TargetPoint { float x=0, y=0, z=0; bool valid=false; };
inline TargetPoint selectTarget(float homeX, float homeY, float homeZ, float radius, float angle)
{
    TargetPoint out;
    if (!std::isfinite(homeX) || !std::isfinite(homeY) || !std::isfinite(homeZ) ||
        !std::isfinite(radius) || radius < 0 || !std::isfinite(angle)) return out;
    out.x = homeX + radius * std::sin(angle);
    out.y = homeY;
    out.z = homeZ + radius * std::cos(angle);
    out.valid = std::isfinite(out.x) && std::isfinite(out.y) && std::isfinite(out.z);
    return out;
}
inline TargetPoint selectTargetSeeded(float homeX, float homeY, float homeZ, float radius, std::uint32_t seed)
{
    constexpr float twoPi = 6.28318530717958647692f;
    // Explicit fixture stream: one documented 32-bit sample, no global RNG use.
    const float angle = (float(seed) / 4294967296.0f) * twoPi;
    return selectTarget(homeX, homeY, homeZ, radius, angle);
}
struct CatchFlyInput {
    float x, y, z;
    float targetX, targetY, targetZ;
    float mapY, elapsedSeconds, grabFlightHeight, transitionHeight;
    float riseFactor, climbingFactor, grabSpeed;
    float faceDirection, turnSpeed, maxTurnAngleDegrees;
    int stuckCount;
    HeightNext heightNext;
    bool targetAttached;
};
struct CatchFlyResult {
    float velocityX = 0, velocityY = 0, velocityZ = 0;
    float faceDirection = 0;
    bool finishMotion = false;
    HeightNext heightNext = HeightNext::None;
    P2DemonAttackNext next = P2DemonAttackNext::None;
};

inline CatchFlyResult catchFly(const CatchFlyInput& in)
{
    CatchFlyResult out;
    constexpr float pi = 3.14159265358979323846f;
    if (!std::isfinite(in.x) || !std::isfinite(in.y) || !std::isfinite(in.z) ||
        !std::isfinite(in.targetX) || !std::isfinite(in.targetY) || !std::isfinite(in.targetZ) ||
        !std::isfinite(in.mapY) || !std::isfinite(in.elapsedSeconds) || in.elapsedSeconds < 0 ||
        !std::isfinite(in.grabFlightHeight) || !std::isfinite(in.transitionHeight) ||
        !std::isfinite(in.riseFactor) || !std::isfinite(in.climbingFactor) || !std::isfinite(in.grabSpeed) ||
        !std::isfinite(in.faceDirection) || !std::isfinite(in.turnSpeed) || !std::isfinite(in.maxTurnAngleDegrees))
        return out;
    const float dx = in.targetX - in.x, dz = in.targetZ - in.z;
    const float distance2 = dx * dx + dz * dz;
    if (in.elapsedSeconds > 10.0f || distance2 < 625.0f) {
        out.finishMotion = true;
    } else if (in.grabSpeed > 0 && distance2 > 0 && in.turnSpeed >= 0 && in.maxTurnAngleDegrees >= 0) {
        const float targetAngle = std::atan2(dx, dz);
        float angle = targetAngle - in.faceDirection;
        while (angle > pi) angle -= 2 * pi;
        while (angle < -pi) angle += 2 * pi;
        const float step = std::min(std::fabs(angle) * in.turnSpeed,
                                    in.maxTurnAngleDegrees * pi / 180.0f);
        out.faceDirection = in.faceDirection + (angle < 0 ? -step : step);
        out.velocityX = std::sin(out.faceDirection) * in.grabSpeed;
        out.velocityZ = std::cos(out.faceDirection) * in.grabSpeed;
    }
    // Source checks attachment before height transition and timer increment.
    if (!in.targetAttached) { out.next = P2DemonAttackNext::Move; return out; }
    const int weight = in.stuckCount < 0 ? 0 : (in.stuckCount > 5 ? 5 : in.stuckCount);
    const float t = float(weight) / 5.0f;
    const float factor = (1.0f - t) * in.riseFactor + t * in.climbingFactor;
    out.velocityY = factor * ((in.mapY + in.grabFlightHeight) - in.y);
    const float height = in.y - in.mapY;
    if (height > in.transitionHeight || in.elapsedSeconds > 3.0f)
        out.heightNext = in.heightNext;
    return out;
}
} // namespace p2demon
