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
// (10 surface / 30 cave); no new P1 Teki actors are born here.
// Every hook is a no-op for unregistered actors.
void pc_p2_tamago_setup();
void pc_p2_tamago_reset();
void pc_p2_tamago_forget(BTeki*);
void pc_p2_tamago_update(BTeki*);
float pc_p2_tamago_param_f(const BTeki*, int idx, float fallback);
int pc_p2_tamago_corpse_type(const BTeki*, int fallback);
bool pc_p2_tamago_clip(const BTeki*, const char*& name, float& phase);
