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
