// Lane 45 (#483): engine-facing API for the real cave-unit geometry and the real
// electric-gate actor. The parser/validation/markers stay in
// pc_p2_cave_geometry.h (engine-free); this header declares the glue implemented
// in pc_p2_cave_geometry.cpp.
#pragma once

#include "pc_p2_cave_geometry.h"

class Graphics;

// True when a P2_CAVE_GEOMETRY_1 plan was loaded this run.
bool pc_p2_cave_geometry_active();

// Opt-in: reads PIKMIN_CAVE_GEOMETRY (path) or ./p2-cave-geometry.txt. No-op and
// no output when neither exists, so a normal run is unchanged.
void pc_p2_cave_geometry_setup();
void pc_p2_cave_geometry_shutdown();

// Live gate-actor update (electric field, yellow opens). No-op when inactive.
void pc_p2_cave_geometry_tick();

// Real unit/gate geometry overlay. Caller owns the camera/projection setup.
void pc_p2_cave_geometry_draw(Graphics& gfx);

// True when a real model is loaded for this node id; the proxy drawer skips it so
// a node is drawn exactly once (real model, never the proxy square as well).
bool pc_p2_cave_geometry_handles(const std::string& id);

const P2CaveGeometryPlan* pc_p2_cave_geometry_plan();
