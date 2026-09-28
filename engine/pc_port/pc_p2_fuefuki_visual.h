#pragma once

class Graphics;

// Lane-owned Fuefuki visual bank (#245): baked sampled rigid poses from the
// restricted converter (docs/PIKMIN2_FUEFUKI_ASSETS.md) with clip selection
// driven by the lane FSM. Opt-in per #186: the caller gates on the room-preview
// experiment; setup parses an explicit P2_FUEFUKI_VISUAL_1 profile (fail
// closed) and loads every staged pose .mod.
//
// Deliberate limits (recorded, not worked around):
// - Baked static poses with approximate materials; no skeletal playback or
//   key-event execution (the lane FSM owns the state machine).
// - landing/landfail are not converted (singular source joint scale); the
//   profile lists only the 8 converted clips.
// - No whistle effect ring, audio or camera-facing billboard orientation.

// Parses the profile and loads every listed pose. Any malformed content or
// missing .mod fails closed with nothing retained.
bool pc_p2_fuefuki_visual_setup(const char* profilePath);
void pc_p2_fuefuki_visual_reset();
bool pc_p2_fuefuki_visual_ready();
int pc_p2_fuefuki_visual_clip_count();

// Lane FSM state -> clip name. `state` is a P2FuefukiFsmState value
// (Dead 0 .. Struggle 8); landing clips are not converted, so Land maps to
// "wait". Returns "wait" for out-of-range values.
const char* pc_p2_fuefuki_visual_clip_for_state(int state);

// World anchor for the drawn pose (host sets it from the vehicle each frame;
// initialised to the room ground origin).
void pc_p2_fuefuki_visual_set_position(float x, float y, float z);
void pc_p2_fuefuki_visual_position(float& x, float& y, float& z);

// Starts a clip by name; false for unknown clips or when not ready.
bool pc_p2_fuefuki_visual_clip(const char* name);
const char* pc_p2_fuefuki_visual_active_clip();

// Advances the active clip by source frames (1.0 per 30 Hz source tick);
// wraps within the clip duration. Returns the pose index, or -1 when idle.
int pc_p2_fuefuki_visual_update(float sourceFrames);
int pc_p2_fuefuki_visual_pose_index();

// Prints a one-time readiness/draw marker for runtime evidence.
bool pc_p2_fuefuki_visual_drew();

// Draws the active pose at the stored anchor.
void pc_p2_fuefuki_visual_draw(Graphics& gfx);
