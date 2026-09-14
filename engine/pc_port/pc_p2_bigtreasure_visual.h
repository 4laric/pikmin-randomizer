#pragma once

#include "pc_p2_bigtreasure_motion.h"
#include "pc_p2_retail_player.h"

class Graphics;
class Shape;
struct Matrix4f;

// Lane-owned BigTreasure visual bank: baked sampled poses from the
// restricted converter plus authored key-event playback through the
// vendored retail player (#246). Opt-in per #186: the caller gates on the
// room-preview experiment; setup parses an explicit P2_BIGTREASURE_VISUAL_1
// profile (fail-closed) and loads every staged pose/pellet .mod.
//
// Deliberate limits (recorded, not worked around):
// - Baked static poses with approximate materials; no skeletal playback.
// - Captured pellets attach at bind-pose otakara_* joint transforms; they
//   do not track animated joints (baking flattens skeletal motion).
// - loozy (King of Bugs) uses a shape matrix type the restricted converter
//   rejects; it stays a debug marker (no fabricated model).

struct P2BigTreasureVisualEvent {
    char clip[40];
    int frame;
    int type; // authored key type; 1000 = implicit clip completion
};

// Parses the profile, loads pose shapes, pellet shapes and the event table.
// Any malformed content fails closed with nothing retained.
bool pc_p2_bigtreasure_visual_setup(const char* profilePath);
void pc_p2_bigtreasure_visual_reset();
bool pc_p2_bigtreasure_visual_ready();

// Starts a clip through the retail event player. Returns false for unknown
// clips or when the bank is not ready.
bool pc_p2_bigtreasure_visual_clip(const char* name);

// Advances the active clip by source frames (1.0 per 30 Hz source tick).
// Dispatched key events (including the implicit type-1000 completion) are
// appended to the bounded log; returns events dispatched this call, or -1
// on invalid input.
int pc_p2_bigtreasure_visual_update(float sourceFrames);

const P2BigTreasureVisualEvent* pc_p2_bigtreasure_visual_events(int* count);
const char* pc_p2_bigtreasure_visual_active_clip();
int pc_p2_bigtreasure_visual_pose_index();
bool pc_p2_bigtreasure_visual_completed();
int pc_p2_bigtreasure_visual_pellet_count();  // converted pellets drawn
int pc_p2_bigtreasure_visual_debug_count();   // debug-marker pellets (loozy)

// Draws the active boss pose and every converted pellet at its bind-pose
// capture transform under `ownerWorld`.
void pc_p2_bigtreasure_visual_draw(Graphics& gfx, const Matrix4f& ownerWorld);
