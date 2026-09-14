#pragma once
class BTeki;
class Creature;

// Family-owned ground-invertebrate source behavior: Mitite (TamagoMushi,
// EnemyID 68) on the batch-2 Chappy placement vehicle (#165/#407).
// Every hook is a no-op for unregistered actors.
void pc_p2_tamago_setup();
void pc_p2_tamago_reset();
void pc_p2_tamago_forget(BTeki*);
void pc_p2_tamago_update(BTeki*);
float pc_p2_tamago_param_f(const BTeki*, int idx, float fallback);
int pc_p2_tamago_corpse_type(const BTeki*, int fallback);
bool pc_p2_tamago_clip(const BTeki*, const char*& name, float& phase);
