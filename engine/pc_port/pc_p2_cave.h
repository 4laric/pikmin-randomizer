#pragma once
#include <string>
class Graphics;
void pc_p2_cave_setup();
void pc_p2_cave_tick();
void pc_p2_cave_request();
bool pc_p2_cave_checkpoint(bool confirm);
int pc_p2_cave_floor();
std::string pc_p2_cave_receipt_prefix();
// Optional world marker. Draw after world actors, before the HUD (uses the view matrix).
void pc_p2_cave_draw_transition(Graphics& gfx);
// Future hole/geyser actor interactions use the same guarded handoff as F6.
bool pc_p2_cave_interact(float x, float y, float z);
