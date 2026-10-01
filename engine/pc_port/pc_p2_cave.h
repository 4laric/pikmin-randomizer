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
