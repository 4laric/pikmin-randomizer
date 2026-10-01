#pragma once
class BTeki;
class Graphics;
class Matrix4f;
class Shape;
bool pc_p2_kurage_visual_setup();
void pc_p2_kurage_visual_reset();
Shape* pc_p2_kurage_visual_wait_shape();
Shape* pc_p2_kurage_visual_attack_shape();
// Per-state converted pose by source motion base name (wait, move1, move2,
// type1, type2, flick1, flick2, dead1, dead2, attack).  Null when that pose was
// not shipped; callers fall back to the wait/attack pair.
Shape* pc_p2_kurage_visual_shape(const char* motionBase);
// Converted pose base name for a p2kurage::State value (see pc_p2_kurage_fsm.h).
const char* pc_p2_kurage_visual_motion_for_state(int state);
bool pc_p2_kurage_visual_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Greater Spotted Jellyfloat (OniKurage, 72) poses: onikurage_<motion>.mod, same
// clip set as the Kurage. Setup fails (and the host body draws) without wait/attack.
bool pc_p2_kurage_visual_setup_greater();
Shape* pc_p2_kurage_visual_shape_greater(const char* motionBase);

// #972 sampled pose bank (p2-kurage-animation.txt / p2-onikurage-animation.txt).
// Private per-actor Shape showing `clip` at `sourceFrame` (vertex lerp + 150 ms
// crossfade on a clip change); nullptr when no bank is loaded, so callers keep
// the static shapes above. PIKMIN_P2_INTERPOLATION=0 selects the nearest pose.
Shape* pc_p2_kurage_visual_pose(BTeki* actor, bool greater, const char* clip, float sourceFrame, unsigned token);
// World translation (model units, origin = actor, yaw 0, scale 1) of the `suck`
// part (Proom joint) in the pose pc_p2_kurage_visual_pose shows at that frame.
bool pc_p2_kurage_visual_proom(bool greater, const char* clip, float sourceFrame, float out[3]);
// Last source frame of a banked clip, or -1 when the clip has no bank.
float pc_p2_kurage_visual_last_frame(bool greater, const char* clip);
void pc_p2_kurage_visual_forget(BTeki* actor);
// #1065 carried-carcass pose: the private Shape in the settled (flattest
// visible) pose of `deathClip`; `lift` is the model-space Y offset that rests it
// on the ground. nullptr without a bank (callers keep the static dead mesh).
Shape* pc_p2_kurage_visual_corpse(BTeki* actor, bool greater, const char* deathClip, unsigned token, float& lift);
