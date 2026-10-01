#include "pc_p2_groink.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace {
bool near(float actual, float expected, float epsilon = 0.0001f)
{
    return std::fabs(actual - expected) <= epsilon;
}
struct Trace {
    int calls = 0;
    float radius = 0.0f;
    bool floor = false;
    bool wall = false;
};
bool trace(void* opaque, const P2GroinkVec3& position, const P2GroinkVec3& velocity,
           float delta, float radius, P2GroinkTraceResult& result)
{
    Trace& state = *static_cast<Trace*>(opaque);
    ++state.calls; state.radius = radius;
    result.position = { position.x + velocity.x * delta, position.y + velocity.y * delta,
                        position.z + velocity.z * delta };
    result.velocity = velocity;
    result.floor = state.floor;
    result.wall = state.wall;
    result.groundY = 7.0f;
    result.hasGroundY = true;
    return true;
}
}

int main()
{
    const P2GroinkVec3 muzzle{ 0.0f, 100.0f, 0.0f };
    const P2GroinkVec3 target{ 0.0f, 100.0f, 250.0f };
    const auto aim = P2GroinkPolicy::aim(muzzle, target, 400.0f, 70.0f,
                                         P2GroinkPolicy::kSourceDelta, 0.0f);
    assert(aim.valid && aim.shellSpeed > 0.0f && std::isfinite(aim.targetAngle));
    assert(near(aim.shellSpeed, 401.69765f) && near(aim.targetAngle, 1.2041587f));
    const auto nearAim = P2GroinkPolicy::aim(muzzle, { 0.0f, 100.0f, 150.0f }, 400.0f, 70.0f,
                                             P2GroinkPolicy::kSourceDelta, 0.0f);
    assert(nearAim.valid && near(nearAim.shellSpeed, 236.66255f) && near(nearAim.targetAngle, 0.9197273f));
    const auto locked = P2GroinkPolicy::aim(muzzle, target, 400.0f, 70.0f,
                                            P2GroinkPolicy::kSourceDelta, aim.targetAngle);
    assert(locked.valid && locked.locked && near(locked.angle, locked.targetAngle));
    // `angDist` chooses the shortest wrap direction at the seam.
    const auto seam = P2GroinkPolicy::aim(muzzle, target, 400.0f, 70.0f,
                                          P2GroinkPolicy::kSourceDelta, 6.27f);
    assert(seam.valid && seam.angle >= 0.0f && seam.angle < 6.28319f);
    assert(!P2GroinkPolicy::aim(muzzle, target, 400.0f, 70.0f, 1.0f / 60.0f, 0.0f).valid);
    assert(!P2GroinkPolicy::aim({ std::numeric_limits<float>::quiet_NaN(), 0, 0 }, target,
                                 400, 70, P2GroinkPolicy::kSourceDelta, 0).valid);
    assert(!P2GroinkPolicy::aim(muzzle, target, 0, 70, P2GroinkPolicy::kSourceDelta, 0).valid);

    P2GroinkPolicy policy;
    const P2GroinkMuzzle joint{ { 2.0f, 0.0f, 0.0f }, { 0.0f, 3.0f, 0.0f },
                                 { 0.0f, 0.0f, 4.0f }, { 10.0f, 20.0f, 30.0f } };
    bool rotatedValid = false;
    const auto rotated = p2_groink_rotate_vertical(joint, 1.57079632679f, rotatedValid);
    assert(rotatedValid && near(rotated.column0.y, 2.0f) && near(rotated.column1.x, -3.0f)
           && near(rotated.column2.z, 4.0f) && near(rotated.column3.x, 10.0f));
    assert(policy.emit(joint, 90.0f, { 0.5f, 0.5f, 0.5f }));
    assert(near(policy.shell().position.x, 35.0f) && near(policy.shell().position.y, 20.0f));
    assert(near(policy.shell().velocity.x, 90.0f));
    assert(!policy.emit(joint, 90.0f, { 0.5f, 0.5f, 0.5f })); // one-shell policy
    Trace state;
    assert(!policy.update({ 0, 0, 0 }, P2GroinkPolicy::kSourceDelta, trace, &state));
    assert(state.calls == 1 && near(state.radius, 10.0f));
    assert(near(policy.shell().velocity.y, -20.0f)); // source update decrement, not delta-scaled
    state.floor = true;
    assert(policy.update({ 0, 0, 0 }, P2GroinkPolicy::kSourceDelta, trace, &state));
    assert(!policy.shell().active);
    assert(policy.lastTerminalStep().reason == P2GroinkTerminalReason::Floor
           && near(policy.lastTerminalStep().end.y, 7.0f));

    P2GroinkPolicy exactRange;
    assert(exactRange.emit(joint, 90.0f, { 0.5f, 0.5f, 0.5f }));
    assert(!exactRange.update({ -962.0f, 0, 0 }, P2GroinkPolicy::kSourceDelta, nullptr, nullptr));
    assert(exactRange.shell().active); // (35 + 3) - -962 is exactly 1000.
    P2GroinkPolicy overRange;
    assert(overRange.emit(joint, 90.0f, { 0.5f, 0.5f, 0.5f }));
    assert(overRange.update({ -962.01f, 0, 0 }, P2GroinkPolicy::kSourceDelta, nullptr, nullptr));
    assert(overRange.lastTerminalStep().reason == P2GroinkTerminalReason::OutOfRange);
    P2GroinkPolicy wall;
    assert(wall.emit(joint, 90.0f, { 0.5f, 0.5f, 0.5f }));
    state.floor = false; state.wall = true;
    assert(wall.update({ 0, 0, 0 }, P2GroinkPolicy::kSourceDelta, trace, &state));
    assert(wall.lastTerminalStep().reason == P2GroinkTerminalReason::Wall);
    const P2GroinkShell before = policy.shell();
    assert(!policy.emit(joint, 90.0f, { 1.1f, 0.5f, 0.5f }));
    assert(policy.shell().active == before.active && near(policy.shell().position.x, before.position.x));
    P2GroinkPolicy overflow;
    auto hugeBasis = joint;
    hugeBasis.column0.x = std::numeric_limits<float>::max();
    assert(!overflow.emit(hugeBasis, 90.0f, { 0.5f, 0.5f, 0.5f }));
    assert(!overflow.emit(joint, std::numeric_limits<float>::infinity(), { 0.5f, 0.5f, 0.5f }));
    assert(overflow.emit(joint, 90.0f, { 0.5f, 0.5f, 0.5f }));
    assert(overflow.update({}, 1.0f / 60.0f, nullptr, nullptr));
    assert(!overflow.lastTerminalStep().valid);
    assert(overflow.lastTerminalStep().reason == P2GroinkTerminalReason::Invalid);
    return 0;
}
