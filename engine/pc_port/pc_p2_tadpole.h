#pragma once
class BTeki;
class Creature;

// Family-owned aquatic source behavior for the batch-3 host: Tadpole (Wogpole,
// EnemyID 27) on the P1 TEKI_Otama (25) placement vehicle (#167/#374/#407).
// Implements the source TadpoleState.cpp six-state FSM (Dead 0, Wait 1, Move 2,
// Amaze 3, Escape 4, Leap 5) with the source Wait->Move wander, the Amaze->Escape
// panic response and the dry-land vertical Leap. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// ATTACKS / RECEIVERS ARE SOURCE-BACKED N/A: Tadpole's retail general block has
// fp24=0 (zero attack) and Tadpole.h declares no damage receiver; it is harmless
// to Pikmin. The source StateAmaze calls flickNearbyPikmin with the inherited
// shake parms, but that is a non-damaging panic shake, not an attack, and is
// deliberately omitted here (no InteractFlick/InteractAttack is raised).
//
// Water-only assumptions (recorded, not retail-faithful): the P1 host exposes no
// water box, so Tadpole's source gate "Wait/Move/Escape -> Leap when mWaterBox is
// absent" (TadpoleState.cpp:101,165,264) would fire every frame. This port keeps
// the source order but defers the dry-land leap to the end of each state's source
// animation/timer so Wait and Move stay observable in the dry private arena; the
// leap itself is the source dry fallback (createLeapEffect, Tadpole.cpp:168).
// Turn rate and the vertical hop impulse are P1-host approximations.
//
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
void pc_p2_tadpole_setup();
void pc_p2_tadpole_reset();
void pc_p2_tadpole_forget(BTeki*);
void pc_p2_tadpole_update(BTeki*);
float pc_p2_tadpole_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_tadpole_clip(const BTeki*, const char*& name, float& phase);
