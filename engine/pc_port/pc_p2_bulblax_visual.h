#pragma once
#include <cstdint>
class Graphics;
// Sampled display only: no Teki, collision, AI, damage, cargo or rewards.
void pc_p2_bulblax_visual_setup();
void pc_p2_bulblax_visual_reset();
void pc_p2_bulblax_visual_draw(Graphics&);
// Caller supplies active simulation seconds; draw never advances retail players.
void pc_p2_bulblax_visual_update(float seconds);
bool pc_p2_bulblax_visual_frame(std::uint32_t displayId, float& frame);
bool pc_p2_bulblax_visual_seek(std::uint32_t displayId, float frame);

namespace p2pose { struct Pose; }
// Diagnostic copy of the last rendered private geometry; false when disabled/reset.
bool pc_p2_bulblax_visual_geometry(std::uint32_t id, p2pose::Pose& out);
