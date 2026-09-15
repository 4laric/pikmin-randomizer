#pragma once
class BTeki;
class Graphics;
class Matrix4f;
// Emperor Bulblax (KingChappy, enemy 53) bound to a generated ordinary Teki
// host, so free-Pikmin attacks reach it through the engine (InteractAttack ->
// actTeki -> host health) and it drops a normal carcass on death. The sidecar
// owns only the King visual, the source stuck/Flick thresholds and the corpse
// observation; host health/damage/carcass remain the engine's. Missing/invalid
// config fails closed (no binding).
void pc_p2_king_teki_setup();
void pc_p2_king_teki_tick(BTeki*);
void pc_p2_king_teki_forget(BTeki*);
void pc_p2_king_teki_reset();
bool pc_p2_king_teki_is_bound(const BTeki*);
bool pc_p2_king_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Read-only lifecycle probes for the native runtime fixture.
bool pc_p2_king_teki_dead_key_seen();
unsigned long pc_p2_king_teki_behavior_tick();
int pc_p2_king_teki_attached_count(const BTeki*);
