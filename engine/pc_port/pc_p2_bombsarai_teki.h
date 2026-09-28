#pragma once

class BTeki;
class PelletView;

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
