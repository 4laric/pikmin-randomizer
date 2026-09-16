#pragma once
class BTeki;
class Creature;

// Family-owned ground-invertebrate source behavior: Mitite (TamagoMushi,
// EnemyID 68) on the batch-2 Chappy placement vehicle (#165/#407).
//
// The module runs the singleton Walk/Turn/Appear/Hide/Wait/Dead FSM, the
// collision Astonish receiver and the honey reward for every registered actor.
// When the arena stages more than one TamagoMushi generator, the
// smallest-generator actor is the group leader (P2_TAMAGO_LEADER) and the rest
// are followers (P2_TAMAGO_GROUP) that emerge near the leader, follow it within
// the bounded swarm leash and share the Astonish receiver. This is a bounded
// approximation of the manager-owned tamagoMushiMgr.cpp::createGroup birth
// (10 surface / 30 cave); group mode additionally births `count` follower Teki
// via pc_p2_tamago_birth_group (P1-derived, see below).
// Every hook is a no-op for unregistered actors.
void pc_p2_tamago_setup();
void pc_p2_tamago_reset();
void pc_p2_tamago_forget(BTeki*);
void pc_p2_tamago_update(BTeki*);
float pc_p2_tamago_param_f(const BTeki*, int idx, float fallback);
int pc_p2_tamago_corpse_type(const BTeki*, int fallback);
bool pc_p2_tamago_clip(const BTeki*, const char*& name, float& phase);
// Manager-driven group birth (#165): births `count` Mitite Teki actors from the
// registered host (source tamagoMushiMgr::createGroup), exactly once per host,
// and links them as follower. P1-derived: born actors are Chappy-vehicle Teki
// (no per-actor generator), documented + logged P2_TAMAGO_BIRTH/BIRTH_ONCE.
void pc_p2_tamago_birth_group(BTeki* host, int count);
// Registration observability for the group-birth lifecycle fixture.
unsigned long pc_p2_tamago_count();
bool pc_p2_tamago_registered(BTeki*);
// Once-per-frame drain of deferred born-follower kills (queued by the forget
// group branch; hooked after tekiMgr->update() in gameCoreSection.cpp).
void pc_p2_tamago_tick();
