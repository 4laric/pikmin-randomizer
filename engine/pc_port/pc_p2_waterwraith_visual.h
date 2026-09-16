#pragma once

class Graphics;
class Shape;
struct Matrix4f;

// Lane-owned Waterwraith/Tyre visual bank: baked sampled poses from the
// restricted converter (#175/#443), staged by
// experimental/pikmin2_waterwraith_stage.py. Two species share one
// P2_WATERWRAITH_VISUAL_1 profile. Opt-in per #186: the caller gates on the
// room-preview experiment; setup parses the profile fail-closed and loads
// every staged pose .mod. Deliberate limits (recorded, not worked around):
// - Baked static poses with approximate materials; no skeletal playback.
// - No retail event table/player: this is a display slice, not source AI.
// - BlackMan and Tyre are drawn as independent sampled-pose actors; species
//   ownership/phases stay in pc_p2_waterwraith (policy) and the native actor.
//
// Profile grammar:
//   P2_WATERWRAITH_VISUAL_1
//   species <name> <enemyId>
//   clip <species> <clip> <poseCount> <duration> <frame...>
// Pose files: courses/pikmin2room/ww_<species>_<clip>_%02d.mod

bool pc_p2_waterwraith_visual_setup(const char* profilePath);
void pc_p2_waterwraith_visual_reset();
bool pc_p2_waterwraith_visual_ready();
int pc_p2_waterwraith_visual_species_count();
int pc_p2_waterwraith_visual_clip_count();
bool pc_p2_waterwraith_visual_has_clip(const char* species, const char* clip);

// Starts a clip for one species. Returns false for unknown species/clip or an
// unready bank. `looping` repeats the clip at its duration.
bool pc_p2_waterwraith_visual_play(const char* species, const char* clip, bool looping);

// Advances every active clip by one source frame (30 Hz). Returns the number
// of active species, or -1 when the bank is not ready.
int pc_p2_waterwraith_visual_update();

// Current discrete pose index for a species' active clip, or -1.
int pc_p2_waterwraith_visual_pose_index(const char* species);

// True when every active non-looping clip has reached its duration.
bool pc_p2_waterwraith_visual_completed();

// Draws every active species' current pose under `ownerWorld`, offset along X
// by 80 units per species index. Returns the number of species drawn.
int pc_p2_waterwraith_visual_draw(Graphics& gfx, const Matrix4f& ownerWorld);

// Draws one species' current pose at an explicit world transform. Returns 1
// when drawn, 0 when the species/clip is inactive or unknown.
int pc_p2_waterwraith_visual_draw_species(Graphics& gfx, const char* species,
                                          const Matrix4f& world);
