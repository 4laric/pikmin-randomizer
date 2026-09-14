#pragma once
class BTeki;
class Creature;

// Family-owned ground-invertebrate source behavior: Creeping Chrysanthemum
// (Hana, EnemyID 84) on the batch-2 Chappy placement vehicle (#165/#407).
// The reserved ChappyBase Sleep(buried)/Walk/Attack/Flick/Dead slice is
// implemented self-contained on the P1 host; every hook is a no-op for
// unregistered actors.
void pc_p2_hana_setup();
void pc_p2_hana_reset();
void pc_p2_hana_forget(BTeki*);
void pc_p2_hana_update(BTeki*);
float pc_p2_hana_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_hana_clip(const BTeki*, const char*& name, float& phase);
