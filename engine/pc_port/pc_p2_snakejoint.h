#pragma once
class BTeki;
class Creature;

// Shared-base snagret source behavior for the batch-3 Chappy placement vehicle:
// Burrowing Snagret (SnakeCrow, EnemyID 34) and Pileated Snagret (SnakeWhole,
// EnemyID 70) (#174/#376/#407). Both species share the source
// `Game::SnakeJointMgr` spine and register their own per-species FSM in
// SnakeCrowState.cpp / SnakeWholeState.cpp; this single module implements the
// bounded shared FSM for both, dispatched by source id 34 / 70.
//   Stay (burrow) -> Appear1/Appear2 (emerge) -> Wait/Walk/Home ->
//   Attack (one directional bite capture) -> Eat (one swallow kill) ->
//   Struggle/Flick -> Disappear (burrow) -> Stay, plus Dead.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms and
// banked event frames from experimental/pikmin2_snagret_assets.py (GPVE01 rev
// 0). Neither snagret has a Pikmin 1 counterpart; the P1 Chappy
// (TEKI_Chappy) is a placement vehicle only. Every hook is a no-op for
// unregistered actors.
void pc_p2_snakejoint_setup();
void pc_p2_snakejoint_reset();
void pc_p2_snakejoint_forget(BTeki*);
void pc_p2_snakejoint_update(BTeki*);
float pc_p2_snakejoint_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_snakejoint_clip(const BTeki*, const char*& name, float& phase);
// Source SnakeCrow/SnakeWhole damage gate: EB_Invulnerable is set only by
// StateStay::init and cleared only by StateStay::cleanup
// (SnakeCrowState.cpp:110/213, SnakeWholeState.cpp:113/217), so the head is
// damageable in every emerged state and invulnerable while buried (Stay).
// Returns true while a registered snagret must reject an attack/bomb (state is
// Stay); false otherwise and for unregistered actors, so the shared hook stays a
// no-op for P1 controls. Mirrors pc_p2_dangomushi_invulnerable.
bool pc_p2_snakejoint_invulnerable(const BTeki*);
// Engine-free damage-gate predicate shared by pc_p2_snakejoint_invulnerable and
// the focused gate test (tools/test_p2_snakejoint_gate.cpp). The
// InteractAttack/InteractBomb hook rejects damage exactly when the actor is a
// registered snagret buried in Stay; emerged snagrets and unregistered actors
// admit damage so the hook stays a no-op for P1 controls. Mirrors
// P2DangoMushiHazardPolicy::attackRejected.
inline bool pc_p2_snakejoint_attack_rejected(bool registered, bool buriedStay) {
    return registered && buriedStay;
}
