#pragma once
class BTeki;
class Creature;

// Family-owned snagret-family source behavior for the batch-3 Chappy placement
// vehicle: Segmented Crawbster (DangoMushi, EnemyID 94) (#174/#376/#407).
// Implements the standalone source DangoMushiState.cpp roller FSM:
// Stay -> Appear (fly) -> Wait -> Move -> Attack (ball roll) -> Turn (crash) ->
// Recover -> Flick (attack_2) -> Wait, plus Dead. DangoMushi is not a snagret
// and not a ChappyBase; the P1 Chappy is a placement vehicle only. Every hook
// is a no-op for unregistered actors.
void pc_p2_dangomushi_setup();
void pc_p2_dangomushi_reset();
void pc_p2_dangomushi_forget(BTeki*);
void pc_p2_dangomushi_update(BTeki*);
float pc_p2_dangomushi_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_dangomushi_clip(const BTeki*, const char*& name, float& phase);

// Damage admission for a registered Crawbster (#174/#376). Returns true while
// the actor must reject attack/bomb damage: the source body is invulnerable
// everywhere except the Turn LOOP_START..key-3 stickable window, when
// EB_Invulnerable clears (DangoMushiState.cpp:530). Always false for an
// unregistered actor, so the shared hook stays a no-op for P1 controls.
bool pc_p2_dangomushi_invulnerable(const BTeki*);
