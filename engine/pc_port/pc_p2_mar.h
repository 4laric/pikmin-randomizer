#pragma once
class BTeki;
class Creature;

// Family-owned flying source behavior: Puffy Blowhog (Mar, EnemyID 29) on the
// batch-3 P1 Puffy Blowhog placement vehicle (#375/#166). Implements a bounded
// source MarState.cpp slice (Wait/Move/Chase/Attack/Dead); the P1 engine has no
// InteractWind, so the source wind attack is resolved as an InteractFlick blow.
// Every hook is a no-op for unregistered actors.
void pc_p2_mar_setup();
void pc_p2_mar_reset();
void pc_p2_mar_forget(BTeki*);
void pc_p2_mar_update(BTeki*);
float pc_p2_mar_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_mar_clip(const BTeki*, const char*& name, float& phase);
