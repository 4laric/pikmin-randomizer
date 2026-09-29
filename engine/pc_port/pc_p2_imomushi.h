#pragma once
class BTeki;
class Creature;

// Family-owned ground-invertebrate source behavior: Ravenous Whiskerpillar
// (Imomushi, EnemyID 65) on the batch-2 Chappy placement vehicle (#165/#407).
// Every hook is a no-op for unregistered actors.
void pc_p2_imomushi_setup();
void pc_p2_imomushi_reset();
void pc_p2_imomushi_forget(BTeki*);
void pc_p2_imomushi_update(BTeki*);
bool pc_p2_imomushi_suppress_ai(const BTeki*);
// Engine-free suppression predicate shared by pc_p2_imomushi_suppress_ai
// and the focused gate test. The P2 FSM drives movement every tick for a
// registered whiskerpillar, so the P1 Chappy host strategy (BTeki::doAI)
// must not run for it; unregistered actors are unaffected.
// Mirrors pc_p2_frog_suppress_ai.
inline bool pc_p2_imomushi_suppressed(bool registered) {
    return registered;
}
float pc_p2_imomushi_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_imomushi_clip(const BTeki*, const char*& name, float& phase);
bool pc_p2_imomushi_receipt(class PelletView*, unsigned&);
int pc_p2_imomushi_bound_count();
