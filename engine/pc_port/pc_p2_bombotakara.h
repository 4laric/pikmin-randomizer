#pragma once
// Pikmin 2 lane-22 BombOtakara payload sidecar runtime (#170, child #447).
//
// Opt-in, actor-local BombOtakara (93) payload behavior: born carrying a Bomb
// stub, chase/arm via the stimulateBomb 1.5 s force delay, detonate exactly
// once on contact/press/death. Gated on p2-bombotakara-native.txt: absent file
// means inert, malformed file fails closed. On detonation the module consumes
// the shared blast primitive (pc_p2_bombsarai_blast.h, projectiles lane #169)
// and applies the source Bomb's InteractBomb, rather than emitting a duplicate
// blast. Generic damage/physics is otherwise untouched.
void pc_p2_bombotakara_setup();
void pc_p2_bombotakara_reset();
void pc_p2_bombotakara_update();
unsigned long pc_p2_bombotakara_behavior_tick();
bool pc_p2_bombotakara_gates_ready();
void pc_p2_bombotakara_kill_all();
int pc_p2_bombotakara_carry_count();
int pc_p2_bombotakara_armed_count();
int pc_p2_bombotakara_detonated_count();
int pc_p2_bombotakara_suppressed_count();
int pc_p2_bombotakara_blast_count();

// Muse l61 (#501) natural-observation seam (additive; no shared-hook change).
//
// The integrated lane-22 Otakara runner binds the BombOtakara93 carrier actor
// by real family generator ID. Once that bind exists, the fixture observes
// (never injects) the source `otakara`-joint attachment and the shared
// lane-20 blast routing to live receivers. These entry points only log
// observation markers; they write no health/state/transport and leave the
// elemental59-62 defaults untouched.
void pc_p2_bombotakara_note_attach_natural(unsigned generator, unsigned payload);
void pc_p2_bombotakara_note_bomb_hit_natural(unsigned generator, unsigned payload,
                                             int colour, int accepted, int targetState);
