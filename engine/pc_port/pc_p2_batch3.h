#pragma once
class BTeki; class Graphics; struct Matrix4f;
// Family-owned batch-3 P2 visual registration (#374 aquatic, #375 flying, #376
// snagret). Optional, additive, opt-in via the Pikipelago room preview.
// Ordinary P1 actors and unconfigured families are untouched.
void pc_p2_batch3_setup();
void pc_p2_batch3_reset();
void pc_p2_batch3_forget(BTeki*);
bool pc_p2_batch3_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
