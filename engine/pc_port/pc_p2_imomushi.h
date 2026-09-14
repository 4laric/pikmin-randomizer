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
float pc_p2_imomushi_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_imomushi_clip(const BTeki*, const char*& name, float& phase);
