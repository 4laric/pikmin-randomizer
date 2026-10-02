#pragma once

// Netplay sim-visibility policy for M2a view-independent culling (issue #879).
//
// In deterministic mode (pc_netplay_deterministic()) no simulation decision
// may depend on the local camera frustum, the window aspect or the camera
// distance. Drawing may still depend on them. Every refresh site whose
// visibility/aspect/LOD result feeds sim state (AI-culling flags, plant AI
// resets, DualCreature dynamics mode, ViewPiki LOD) routes that result
// through one of the helpers below, so non-deterministic mode keeps the
// frustum result exactly.
//
// Engine-free TU (only pc_netplay_det.h): safe to include from game headers
// such as Creature.h and to link into host tests.

bool pc_netplay_sim_visible(bool frustumResult);
// Deterministic-mode sim visibility: always true (always visible / never
// culled). Pass-through of frustumResult when the switch is off.

float pc_netplay_sim_aspect(float liveAspect);
// Session-fixed sim aspect: 16:9 in deterministic mode, so no
// sim-affecting frustum build reads the window size. Pass-through otherwise.

float pc_netplay_sim_lod_distance(float liveDistance);
// Deterministic-mode camera distance for sim-affecting LOD: 0 (near/full
// LOD, head look and pose always update). Pass-through otherwise.
