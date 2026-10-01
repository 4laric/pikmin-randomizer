#pragma once

class BTeki;

// Shared Teki actor-lifetime seam (lane 07; #186 feedback "family registration
// maps are never cleared on Teki death", #397/#404).
//
// Clears every P2 family's registration-map entry for a Teki. Each family hook
// is an idempotent map erase, so this is safe for actors no family registered
// and safe to call more than once for the same actor. It is invoked from the
// death funnel (BTeki::doKill) and reused for slot reuse (TekiMgr::newTeki), so
// a stale BTeki* key can never outlive the actor, per
// docs/PIKMIN2_ENEMY_IMPORT_PIPELINE.md section 5.
//
// The family list lives only in pc_p2_teki_lifetime.cpp. Add a family there, not
// at the call sites, so the death funnel and slot reuse stay in sync.
void pc_p2_forget_teki(BTeki* actor);

// Clears every P2 family's registration/visual state at a stage boundary. Used
// from GameCoreSection::exitStage so a finished stage cannot leave a stale
// BTeki* key pointing into the about-to-be-destroyed TekiMgr. Mirrors the
// family set in TekiMgr::reset(), which the engine never reaches on this line
// (stage exit only reset the kurage families before this). Safe to call while
// the stage creatures and managers are still valid.
void pc_p2_reset_all_teki();

// Safe new-scene signal for lifecycle fixtures: called once from
// GameCoreSection::finalSetup for every loaded stage. Fixtures must not touch
// TekiMgr/P2 family state across a stage transition until this has advanced, as
// the transition frees the previous TekiMgr.
void pc_p2_scene_begin();
unsigned long pc_p2_scene_generation();
