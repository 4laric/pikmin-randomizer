#pragma once

#include "pc_p2_waterwraith.h"

#include <cstdint>

// Lane-owned host seam binding the Waterwraith/Tyre dependent-roller policy
// (pc_p2_waterwraith, #175) to a display fixture. A fixed-route wraith drives
// the rig, which owns the single Tyre child and derives its roll from the
// planar distance travelled. Engine-free: no actor, map, receiver or gameplay
// dependency; the host supplies the route and feed rate.
//
// Source anchors: BlackMan travel speed fp05 (retail 120), Tyre roll rate =
// distance / 44*pi scaled by fp01 (blackMan.cpp:988-995). Locomotion here is a
// host-driven straight route, not the retained-assembly walk code.

struct P2WaterwraithHostSeam {
    P2WaterwraithRig rig;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float facing = 0.0f;
    float speed = 120.0f; // fp05 retail travel speed
    std::uint64_t ticks = 0;
    bool active = false;
};

// Resets the seam to an inactive state (rig torn down).
void p2_waterwraith_host_reset(P2WaterwraithHostSeam& seam);

// Births the roller and starts the wraith moving along +X from the origin.
// `properRotationSpeed` is Tyre fp01 (retail 25.0).
bool p2_waterwraith_host_setup(P2WaterwraithHostSeam& seam, float properRotationSpeed = 25.0f);

// One 30 Hz host tick: advances the route, pushes position/velocity/facing to
// the roller, resolves the first floor contact (land -> freeze) and restarts
// movement (freeze -> move) after a short hold. Safe on an inactive seam.
void p2_waterwraith_host_tick(P2WaterwraithHostSeam& seam, float delta);
