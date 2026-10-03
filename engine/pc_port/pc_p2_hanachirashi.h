#pragma once
class BTeki;
class Creature;

// Family-owned flying source behavior: Withering Blowhog (Hanachirashi,
// EnemyID 55) on the batch-3 P1 Puffy Blowhog placement vehicle (#375/#166/#407).
// Implements a bounded source HanachirashiState.cpp slice (Wait/Move/Chase/
// Attack/Laugh/Dead). The P1 engine has no InteractWind / InteractHanaChirashi,
// so the source withering wind is resolved as a single InteractFlick blow at the
// source attack KEYEVENT_2 frame; Purple bud/flower receivers are stripped to
// Leaf instead of being blown. Every hook is a no-op for unregistered actors.
void pc_p2_hanachirashi_setup();
void pc_p2_hanachirashi_reset();
void pc_p2_hanachirashi_forget(BTeki*);
void pc_p2_hanachirashi_update(BTeki*);
float pc_p2_hanachirashi_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_hanachirashi_clip(const BTeki*, const char*& name, float& phase);

#include <string>
bool pc_p2_hanachirashi_original_resources(unsigned,std::string&);
bool pc_p2_hanachirashi_original_birth(BTeki*,unsigned,unsigned,unsigned,std::string&);
bool pc_p2_hanachirashi_original_registry(BTeki*,unsigned,std::string&);
bool pc_p2_hanachirashi_suppress_ai(const BTeki*);
