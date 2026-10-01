#include "pc_p2_groink.h"

#include <algorithm>

namespace {
bool finite(float value) { return std::isfinite(value); }
bool finite(const P2GroinkVec3& value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}
P2GroinkVec3 add(P2GroinkVec3 a, P2GroinkVec3 b)
{
    return { a.x + b.x, a.y + b.y, a.z + b.z };
}
P2GroinkVec3 scale(P2GroinkVec3 value, float factor)
{
    return { value.x * factor, value.y * factor, value.z * factor };
}
float length(P2GroinkVec3 value)
{
    return std::sqrt(value.x * value.x + value.y * value.y + value.z * value.z);
}
bool normalise(P2GroinkVec3& value)
{
    const float magnitude = length(value);
    if (!finite(magnitude) || magnitude <= 0.0f) return false;
    value = scale(value, 1.0f / magnitude);
    return finite(value);
}
float wrap(float angle)
{
    constexpr float tau = 6.2831853071795864769f;
    angle = std::fmod(angle, tau);
    return angle < 0.0f ? angle + tau : angle;
}
// Source sysMath.cpp: angDist(a, b) = roundAng(a-b), then maps [pi, tau) negative.
float angDist(float first, float second)
{
    constexpr float pi = 3.14159265358979323846f;
    constexpr float tau = 6.2831853071795864769f;
    float distance = wrap(first - second);
    return distance >= pi ? -wrap(tau - distance) : distance;
}
}

P2GroinkMuzzle p2_groink_rotate_vertical(const P2GroinkMuzzle& muzzle, float angle, bool& valid)
{
    valid = false;
    if (!finite(muzzle.column0) || !finite(muzzle.column1) || !finite(muzzle.column2)
        || !finite(muzzle.column3) || !finite(angle)) return {};
    P2GroinkVec3 x = muzzle.column0, y = muzzle.column1, z = muzzle.column2;
    const float xScale = length(x), yScale = length(y), zScale = length(z);
    if (!finite(xScale) || !finite(yScale) || !finite(zScale) || xScale <= 0.0f
        || yScale <= 0.0f || zScale <= 0.0f) return {};
    x = scale(x, 1.0f / xScale);
    y = scale(y, 1.0f / yScale);
    z = scale(z, 1.0f / zScale);
    const float cosine = std::cos(angle), sine = std::sin(angle);
    // M * Rz: local right-concatenation, matching PSMTXConcat(head, rot, head).
    const P2GroinkVec3 newX = add(scale(x, cosine), scale(y, sine));
    const P2GroinkVec3 newY = add(scale(x, -sine), scale(y, cosine));
    P2GroinkMuzzle result{ scale(newX, xScale), scale(newY, yScale), scale(z, zScale), muzzle.column3 };
    valid = finite(result.column0) && finite(result.column1) && finite(result.column2);
    return valid ? result : P2GroinkMuzzle{};
}

P2GroinkAim P2GroinkPolicy::aim(const P2GroinkVec3& muzzlePosition,
                                 const P2GroinkVec3& targetPosition,
                                 float searchDistance, float attackRadius,
                                 float delta, float angle)
{
    P2GroinkAim result;
    if (!finite(muzzlePosition) || !finite(targetPosition) || !finite(searchDistance)
        || !finite(attackRadius) || !finite(delta) || !finite(angle)
        || searchDistance <= 0.0f || attackRadius < 0.0f
        || std::fabs(delta - kSourceDelta) > 0.000001f) return result;

    const float dx = muzzlePosition.x - targetPosition.x;
    const float dz = muzzlePosition.z - targetPosition.z;
    float distance = std::sqrt(dx * dx + dz * dz) - 50.0f;
    if (distance < 1.0f) distance = 1.0f;

    float value = 250.0f;
    const float searchLimit = searchDistance / 2.0f;
    if (searchLimit > 0.0f && distance < searchLimit) {
        const float ratio = distance / searchLimit;
        value = value * ratio + (1.0f - ratio);
        if (distance < attackRadius) distance *= 0.1f;
    }
    const float b = (value / delta) / 20.0f;
    const float horizontal = (0.45f * distance) / (b / 20.0f) / delta;
    const float speed = std::sqrt(horizontal * horizontal + b * b);
    // JMAAtan2Radian is atan2(y, x): the source supplies (horizontal, b).
    // The equation and argument order match its 1024-entry LUT; std::atan2
    // intentionally supplies a host numerical approximation, not that LUT.
    const float targetAngle = 1.5707963267948966192f - std::atan2(horizontal, b);
    const float error = angDist(angle, targetAngle);
    const float absoluteError = std::fabs(error);
    angle = absoluteError > 0.1f ? angle - 0.1f * (error / absoluteError) : angle - error;

    result.valid = finite(distance) && finite(value) && finite(b) && finite(horizontal)
        && finite(angle) && finite(speed) && finite(targetAngle);
    result.locked = result.valid && absoluteError < 0.01f;
    result.angle = wrap(angle);
    result.targetAngle = wrap(targetAngle);
    result.shellSpeed = speed;
    return result;
}

bool P2GroinkPolicy::emit(const P2GroinkMuzzle& muzzle, float shellSpeed,
                          const P2GroinkVec3& spreadUnit)
{
    if (mShell.active || !finite(muzzle.column0) || !finite(muzzle.column3)
        || !finite(shellSpeed) || shellSpeed < 0.0f || !finite(spreadUnit)
        || spreadUnit.x < 0.0f || spreadUnit.x > 1.0f || spreadUnit.y < 0.0f
        || spreadUnit.y > 1.0f || spreadUnit.z < 0.0f || spreadUnit.z > 1.0f) return false;

    P2GroinkVec3 direction = muzzle.column0;
    if (!normalise(direction)) return false;
    const P2GroinkVec3 position = add(muzzle.column3, scale(direction, 25.0f));
    if (!finite(position)) return false;
    direction.x += 0.2f * spreadUnit.x - 0.1f;
    direction.y += 0.2f * spreadUnit.y - 0.1f;
    direction.z += 0.2f * spreadUnit.z - 0.1f;
    if (!normalise(direction)) return false;
    const P2GroinkVec3 velocity = scale(direction, shellSpeed);
    if (!finite(velocity)) return false;
    mShell = { true, true, position, velocity };
    return true;
}

bool P2GroinkPolicy::update(const P2GroinkVec3& ownerPosition, float delta,
                            P2GroinkTraceFn trace, void* traceContext)
{
    if (!mShell.active) return false;
    const P2GroinkVec3 sourcePosition = mShell.position;
    auto terminal = [&](P2GroinkTerminalReason reason) {
        mLastTerminalStep = { reason != P2GroinkTerminalReason::Invalid, reason,
            { sourcePosition.x, sourcePosition.y - 10.0f, sourcePosition.z },
            { mShell.position.x, mShell.position.y - 10.0f, mShell.position.z } };
        recycle();
        return true;
    };
    if (!finite(ownerPosition) || !finite(delta) || std::fabs(delta - kSourceDelta) > 0.000001f
        || !finite(mShell.position) || !finite(mShell.velocity)) {
        return terminal(P2GroinkTerminalReason::Invalid);
    }
    P2GroinkTraceResult traced;
    bool collided = false;
    P2GroinkTerminalReason collisionReason = P2GroinkTerminalReason::None;
    if (trace && trace(traceContext, mShell.position, mShell.velocity, delta, kShellRadius, traced)) {
        if (!finite(traced.position) || !finite(traced.velocity)) return terminal(P2GroinkTerminalReason::Invalid);
        mShell.position = traced.position;
        mShell.velocity = traced.velocity;
        collided = traced.floor || traced.wall;
        if (collided) {
            if (!traced.hasGroundY || !finite(traced.groundY)) return terminal(P2GroinkTerminalReason::Invalid);
            if (mShell.position.y - traced.groundY < 20.0f) mShell.position.y = traced.groundY + 10.0f;
            collisionReason = traced.floor ? P2GroinkTerminalReason::Floor : P2GroinkTerminalReason::Wall;
        }
    } else {
        mShell.position = add(mShell.position, scale(mShell.velocity, delta));
    }
    mShell.velocity.y -= 20.0f;
    if (!finite(mShell.position) || !finite(mShell.velocity)) return terminal(P2GroinkTerminalReason::Invalid);
    if (collided) return terminal(collisionReason);
    if (std::fabs(ownerPosition.x - mShell.position.x) > 1000.0f
        || std::fabs(ownerPosition.y - mShell.position.y) > 1000.0f
        || std::fabs(ownerPosition.z - mShell.position.z) > 1000.0f) {
        return terminal(P2GroinkTerminalReason::OutOfRange);
    }
    return false;
}
