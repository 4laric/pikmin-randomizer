#pragma once
class BTeki; class Graphics; struct Matrix4f;
// Family-owned batch-2 P2 visual registration (#346, #349, #350, #352, #353).
// Optional, additive, opt-in via the Pikipelago room preview. Ordinary P1
// actors and unconfigured families are untouched.
void pc_p2_batch2_setup();
// Re-entry path (#397): rebind present arena actors after a legitimate family
// death without requiring every configured actor to still exist. Ordinary
// startup keeps the strict pc_p2_batch2_setup() contract.
void pc_p2_batch2_rebind();
void pc_p2_batch2_reset();
void pc_p2_batch2_forget(BTeki*);
bool pc_p2_batch2_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Runtime evidence helper: true once any live or corpse pose has been drawn.
bool pc_p2_batch2_any_drawn();
// Fixture observability (#397): read-only registration count / membership.
unsigned long pc_p2_batch2_count();
bool pc_p2_batch2_registered(BTeki*);
