#pragma once
class BTeki; class Graphics; struct Matrix4f;
// Family-owned Long Legs (#312, parent #173) native registration for the
// installed bind-pose meshes. Optional, additive, opt-in via the Pikipelago
// room preview. Ordinary P1 actors and unconfigured families are untouched.
void pc_p2_long_legs_setup();
void pc_p2_long_legs_reset();
void pc_p2_long_legs_forget(BTeki*);
bool pc_p2_long_legs_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
