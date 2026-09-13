#pragma once
class BTeki; class Graphics; struct Matrix4f;
// Family-owned batch-2 P2 visual registration (#346, #349, #350, #352, #353).
// Optional, additive, opt-in via the Pikipelago room preview. Ordinary P1
// actors and unconfigured families are untouched.
void pc_p2_batch2_setup();
void pc_p2_batch2_reset();
void pc_p2_batch2_forget(BTeki*);
bool pc_p2_batch2_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
