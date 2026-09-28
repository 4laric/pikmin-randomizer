#pragma once
class BTeki;
class Graphics;
class Matrix4f;
// Empress Bulblax (Queen, enemy 30) bound to a generated ordinary Teki
// host, so free-Pikmin attacks reach it through the engine (InteractAttack ->
// actTeki -> host health) and it drops a normal carcass on death. The sidecar
// owns only the Queen visual, the source stuck/shake-off thresholds and the
// corpse observation; host health/damage/carcass remain the engine's.
// Missing/invalid config fails closed (no binding).
void pc_p2_queen_teki_setup();
void pc_p2_queen_teki_tick(BTeki*);
void pc_p2_queen_teki_forget(BTeki*);
void pc_p2_queen_teki_reset();
bool pc_p2_queen_teki_is_bound(const BTeki*);
bool pc_p2_queen_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Read-only lifecycle probes for the native runtime fixture.
bool pc_p2_queen_teki_dead_key_seen();
unsigned long pc_p2_queen_teki_behavior_tick();
int pc_p2_queen_teki_attached_count(const BTeki*);
// Parameter-override seam (chained in include/teki.h BTeki::getParameterF): for
// a bound host, report the Empress's health as TPF_Life and zero life recovery
// so the per-frame life-recovery clamp keeps the host at 5000 until real damage
// is dealt. Unbound hosts fall through unchanged.
float pc_p2_queen_teki_param_f(const BTeki*, int idx, float fallback);
// Pod corpse receipt (family-local, the preview Pod's corpse branch): maps a
// delivered carcass PelletView back to its bound host generator.
class PelletView;
bool pc_p2_queen_teki_receipt(PelletView*, unsigned& generator);
// Pod title name: "Empress Bulblax" for a bound queen host, else nullptr.
const char* pc_p2_queen_teki_name(PelletView*);
