#pragma once
// Pikmin 2 lane-22 fixed-hazard sidecar runtime (#170, child #447).
//
// Opt-in, actor-local Hiba (20, fire geyser), GasHiba (21, gas pipe) and
// ElecHiba (22, electrical wire) behavior. Gated on p2-hiba-native.txt: absent
// file means inert, malformed file fails closed. Elemental stimulus is applied
// through the existing Pikmin receiver (InteractFire here) with colour immunity
// decided by pc_p2_hiba_policy.h; generic damage/physics and lane-20 blast
// primitives are untouched.
void pc_p2_hiba_setup();
void pc_p2_hiba_reset();
void pc_p2_hiba_update();
unsigned long pc_p2_hiba_behavior_tick();
bool pc_p2_hiba_gates_ready();
void pc_p2_hiba_kill_all();
int pc_p2_hiba_activated();
int pc_p2_hiba_emitted();
bool pc_p2_hiba_hit_seen();
bool pc_p2_hiba_immune_seen();
