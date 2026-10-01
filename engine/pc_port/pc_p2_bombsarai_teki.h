#pragma once

class BTeki;
class PelletView;
class Graphics;
class Matrix4f;

// ---------------------------------------------------------------------------
// #244 OWN campaign port (pc_p2_bombsarai_own_teki.cpp). In a bridge
// (campaign) session every actor whose seed source is 58 rides a TEKI_Napkid
// vehicle driven by the engine-free source machine (pc_p2_bombsarai_own.cpp);
// the Napkid strategy is suppressed. The room-preview fixture below is not
// used in a campaign.
bool pc_p2_bombsarai_own_setup();          // false outside bridge mode
bool pc_p2_bombsarai_own_tick(BTeki*);     // true when `t` is OWN-bound (handled)
void pc_p2_bombsarai_own_forget(BTeki*);
void pc_p2_bombsarai_own_reset();
bool pc_p2_bombsarai_own_is_bound(const BTeki*);
// BTeki::doAI: the bound carrier's P1 Napkid strategy never runs while alive.
bool pc_p2_bombsarai_teki_suppress_ai(const BTeki*);
// Teki float-parameter hook: source life (fp00) and regeneration (fp31).
float pc_p2_bombsarai_teki_param_f(const BTeki*, int idx, float fallback);
// BTeki draw hook: the staged P2 BombSarai pose bank, chosen by the machine's
// clip and frame; false (host model draws) when unbound or unstaged.
bool pc_p2_bombsarai_teki_draw(BTeki*, Graphics&, const Matrix4f& view, bool corpse = false);
// GameCoreSection: the Bomb payloads (they outlive their carrier) tick on the
// source clock and draw with the staged Bomb model.
void pc_p2_bombsarai_teki_update_bombs();
void pc_p2_bombsarai_teki_draw_bombs(Graphics&);
// GameCoreSection::draw1D (2D pass): each burning bomb's life-gauge wheel (#1027).
void pc_p2_bombsarai_teki_draw_bomb_gauges(Graphics&);

// Generated Careening Dirigibug (BombSarai, EnemyID 58) carrier binding (#244).
//
// The engine exposes only P1 Teki types; like Kurage -> TEKI_Frog and
// Fuefuki -> TEKI_Napkid, this module binds a generated P1 vehicle through a
// sidecar (`p2-bombsarai-teki.txt`, one row) and drives it as the BombSarai
// carrier: the lane-owned 13-state FSM advances from the vehicle's live
// position (mSRT.t), the hover policy drives its vertical height, the shared
// bomb pool births/throw payloads from the capture joint, and detonations
// route the source Bomb's InteractBomb to live Navi/Pikmin/Teki receivers
// (the same engine receiver BombOtakara consumes). Death (health drained by
// ordinary Pikmin) revokes the binding and resolves the corpse Pod receipt.

// GameCoreSection::finalSetup binding entry (inert without the sidecar).
void pc_p2_bombsarai_teki_setup();
// BTeki::update per-actor tick.
void pc_p2_bombsarai_teki_tick(BTeki*);
// Death-funnel / slot-reuse forget, and stage-boundary reset.
void pc_p2_bombsarai_teki_forget(BTeki*);
void pc_p2_bombsarai_teki_reset();

// Corpse receipt resolution for pc_p2_preview_deliver: returns true and fills
// generator when `view` is the bound carrier's corpse pellet view.
bool pc_p2_bombsarai_receipt(PelletView* view, unsigned& generator);

// Read-only probes for the runtime fixture.
bool pc_p2_bombsarai_teki_is_bound(const BTeki*);
int pc_p2_bombsarai_teki_throw_count();
int pc_p2_bombsarai_teki_blast_count();
bool pc_p2_bombsarai_teki_carrier_dead();
// Cleanup/re-entry probes (#244): live binding and retained-corpse counts, and
// a reset/re-entry rehearsal that runs the same teardown (pc_p2_reset_all_teki)
// and finalSetup (pc_p2_bombsarai_teki_setup) entry points on the live scene.
int pc_p2_bombsarai_teki_bound_count();
int pc_p2_bombsarai_teki_corpse_count();
bool pc_p2_bombsarai_teki_reentry(int& boundBefore, int& boundAfter, int& corpseAfter);
