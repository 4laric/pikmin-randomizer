#pragma once
struct BTeki; struct Graphics; struct Matrix4f; struct PelletView;
void pc_p2_mamuta_setup();
void pc_p2_mamuta_reset();
void pc_p2_mamuta_forget(BTeki*);
bool pc_p2_mamuta_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
bool pc_p2_mamuta_is_bound(BTeki*);
// Family corpse receipt for the preview Pod: resolves a Mamuta carcass pellet
// (the bound actor's own PelletView) to its generator so the Pod can credit it.
// Returns false for any pellet not owned by a bound Mamuta.
bool pc_p2_mamuta_receipt(PelletView*, unsigned& generator);
