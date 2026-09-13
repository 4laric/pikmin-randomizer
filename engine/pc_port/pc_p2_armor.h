#pragma once
class BTeki;
class Creature;
class Piki;

// Family-owned ground-invertebrate source behavior: Cloaking Burrow-nit (Armor,
// EnemyID 15) on the batch-2 Chappy placement vehicle (#165/#407).
// Bridge-eating states are source-backed N/A for the arena (no ItemBridge);
// every hook is a no-op for unregistered actors.
void pc_p2_armor_setup();
void pc_p2_armor_reset();
void pc_p2_armor_forget(BTeki*);
void pc_p2_armor_forget_piki(Piki*);
void pc_p2_armor_update(BTeki*);
float pc_p2_armor_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_armor_clip(const BTeki*, const char*& name, float& phase);
