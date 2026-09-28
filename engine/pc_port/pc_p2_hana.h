#pragma once
class BTeki;
class Creature;
class Teki;

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

// Read-only buried/no-atari gate (source Hana::setUnderGround). True only for a
// registered Hana in its buried Sleep state; false for unregistered actors, so
// the shared hooks stay no-ops for every other lane.
bool pc_p2_hana_buried(const BTeki*);
// Attack receiver for the buried gate. True means the InteractAttack/InteractBomb
// must be swallowed with no damage (non-targetable/no-atari, source
// EB_Invulnerable + setAtari(false)); false for surfaced/unregistered actors.
// Emits P2_HANA_UNDERGROUND_BLOCK when it blocks.
bool pc_p2_hana_rejects_attack(Teki*);
