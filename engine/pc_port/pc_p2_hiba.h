#pragma once
// Pikmin 2 lane-22 fixed-hazard sidecar runtime (#170, child #447).
//
// Opt-in, actor-local Hiba (20, fire geyser), GasHiba (21, gas pipe) and
// ElecHiba (22, electrical wire) behavior. Gated on p2-hiba-native.txt: absent
// file means inert, malformed file fails closed. Each hazard's elemental
// stimulus is applied through the real Pikmin receivers this engine owns --
// InteractFire (Hiba), InteractGas (GasHiba -> PIKISTATE_Panic),
// InteractDenki (ElecHiba -> PIKISTATE_DenkiDying) -- with immunity decided by
// the lane-10 emitter contract (p2_emitter_accepts -> lane-11
// p2_species_immune), never by a P1 colour table. Generic damage/physics and
// lane-20 blast primitives are untouched.
//
// Cross-lane note: this is lane 22's fixed-hazard module; lane 10 (receivers)
// added the p2_emitter_accepts routing so the emitter and the
// InteractFire/InteractGas/InteractDenki receivers cannot disagree about
// immunity.
void pc_p2_hiba_setup();
void pc_p2_hiba_reset();
void pc_p2_hiba_update();
void pc_p2_hiba_lethal_check();
unsigned long pc_p2_hiba_behavior_tick();
bool pc_p2_hiba_gates_ready();
void pc_p2_hiba_kill_all();
int pc_p2_hiba_activated();
int pc_p2_hiba_emitted();
bool pc_p2_hiba_hit_seen();
bool pc_p2_hiba_immune_seen();
bool pc_p2_hiba_gas_hit_seen();
bool pc_p2_hiba_gas_immune_seen();
bool pc_p2_hiba_denki_hit_seen();
bool pc_p2_hiba_denki_immune_seen();
bool pc_p2_hiba_gas_lethal();
bool pc_p2_hiba_denki_lethal();
