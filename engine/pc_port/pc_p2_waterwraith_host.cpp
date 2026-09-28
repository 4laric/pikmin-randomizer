#include "pc_p2_waterwraith_host.h"

#include <cmath>

namespace {
constexpr int kFreezeHoldTicks = 30; // one second of land/freeze before moveRestart
} // namespace

void p2_waterwraith_host_reset(P2WaterwraithHostSeam& seam)
{
    seam = P2WaterwraithHostSeam();
}

bool p2_waterwraith_host_setup(P2WaterwraithHostSeam& seam, float properRotationSpeed)
{
    p2_waterwraith_host_reset(seam);
    seam.rig = P2WaterwraithRig(properRotationSpeed);
    if (!seam.rig.birth()) {
        return false;
    }
    seam.x      = 0.0f;
    seam.y      = 0.0f;
    seam.z      = 0.0f;
    seam.facing = 0.0f;
    seam.active = true;
    // Initial push places the roller in Land.
    seam.rig.push({ seam.x, seam.y, seam.z }, { 0.0f, 0.0f, 0.0f }, seam.facing, 1.0f);
    return true;
}

void p2_waterwraith_host_tick(P2WaterwraithHostSeam& seam, float delta)
{
    if (!seam.active || !std::isfinite(delta) || delta <= 0.0f) {
        return;
    }
    seam.x += seam.speed * delta;
    const P2WaterwraithVec3 position{ seam.x, seam.y, seam.z };
    const P2WaterwraithVec3 velocity{ seam.speed, 0.0f, 0.0f };
    seam.rig.push(position, velocity, seam.facing, 1.0f);
    if (seam.ticks == 0) {
        seam.rig.landFloorContact(); // first contact: flick then freeze
    } else if (seam.ticks == static_cast<std::uint64_t>(kFreezeHoldTicks)) {
        seam.rig.moveRestart(); // wraith resumes: freeze -> move (roll begins)
    }
    ++seam.ticks;
}
