#pragma once
#include <string>
class Graphics;
void pc_p2_cave_setup();
void pc_p2_cave_tick();
void pc_p2_cave_request();
bool pc_p2_cave_checkpoint(bool confirm);
// Refuse premature exit; successful checkpoint exits the process with code42.
bool pc_p2_cave_exit_after_checkpoint();
int pc_p2_cave_floor();
bool pc_p2_cave_is_beasts();
std::string pc_p2_cave_boundary_token();
std::string pc_p2_cave_receipt_prefix();
// Optional world marker. Draw after world actors, before the HUD (uses the view matrix).
void pc_p2_cave_draw_transition(Graphics& gfx);
// Future hole/geyser actor interactions use the same guarded handoff as F6.
bool pc_p2_cave_interact(float x, float y, float z);
// True only for a pinned surface route; this does not make a surface a cave floor.
bool pc_p2_cave_surface_route_active();
// Narrow, asset-validated ordinary surface checkpoint context; never a global
// species switch. Invalidated by scene generation/profile change or completion.
bool pc_p2_cave_route_species_requested(int species);
// Runtime-only WFG body context after entry restoration and scene final setup.
bool pc_p2_cave_body_profile_context(unsigned long long seed,const std::string& cave,
    int floor,const std::string& boundaryToken);
