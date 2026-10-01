#pragma once
class BTeki;
class Creature;
class Plane;
class Graphics;

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
// TEST-ONLY autoplay read-only probe (#897 bot roll evade): the registered
// Crawbster's FSM state name, whether it is rolling (StateAttack ball roll),
// whether the Turn stickable window is open (damage admitted), and the roll
// drive velocity (XZ). Returns false (outputs untouched) for any other actor.
// No logging, no mutation.
bool pc_p2_dangomushi_probe(const BTeki*, const char** state, bool* rolling, bool* stickable,
                            float* driveX, float* driveZ);

// Damage admission for a registered Crawbster (#174/#376). Returns true while
// the actor must reject attack/bomb damage: the source body is invulnerable
// everywhere except the Turn LOOP_START..key-3 stickable window, when
// EB_Invulnerable clears (DangoMushiState.cpp:530). Always false for an
// unregistered actor, so the shared hook stays a no-op for P1 controls.
bool pc_p2_dangomushi_invulnerable(const BTeki*);
// P2 FSM owns movement/targeting/attacks every tick for registered DangoMushi
// (frog pattern): BTeki::doAI returns early so the Swallow host strategy
// never runs. Damage still reaches mHealth via the update-phase
// mStoredDamage -> makeDamaged() drain; death finalizes via pcEscapeNow().
bool pc_p2_dangomushi_suppress_ai(const BTeki*);
// Source Obj::wallCallback (#897): BTeki::wallCallback forwards the wall
// plane; a rolling registered Crawbster that hits it at speed > 100 and
// dot(vel, n) < -0.5 crashes into StateTurn. No-op for any other actor.
void pc_p2_dangomushi_wall(BTeki*, const Plane&);
// Draws the live rain Rocks/Egg (createCrashEnemy children) with the P1
// Iwagon boulder stand-in mesh. No-op when no Crawbster rain is alive.
void pc_p2_dangomushi_draw_rain(Graphics&);
// Frustum-cull radius override for a Crawbster corpse pellet (#897): the
// Swallow host's TPF_CorpseSize (10) made the whole 200-unit body pop out
// while its carriers and counter were still on screen. Returns 0 otherwise.
float pc_p2_dangomushi_cull_radius(Creature* creature);
