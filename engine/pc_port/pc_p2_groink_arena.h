#pragma once

#include "pc_p2_groink.h"

class Graphics;

// Loads one stationary, host-driven Groink arena from P2_GROINK_ARENA_1.
// The profile contains the fixed groink_attack.mod name, retail aim parameters,
// owner/target positions, and an authored 3x4 muzzle matrix. There is no actor,
// AI, damage receiver, MapMgr, sound, or effect integration in this module.
bool pc_p2_groink_arena_setup(const char* profilePath);
void pc_p2_groink_arena_reset();

// Processes exactly one source 30 Hz update. A non-null trace callback is
// required: it receives the radius-10 shell trace and owns map collision. The
// explicit fireEvent4 can emit the one policy shell only once the source aim
// calculation is locked. Returns false if the arena is unavailable, input is
// invalid, or no trace callback was supplied.
bool pc_p2_groink_arena_update(float sourceDelta, bool fireEvent4,
                               P2GroinkTraceFn trace, void* context);

// Draws the baked frame-25 attack model at its stationary owner transform and
// a simple debug sphere for an active policy shell.
void pc_p2_groink_arena_draw(Graphics& gfx);
