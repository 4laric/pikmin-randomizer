#pragma once
#include <cstdint>
#include "pc_p2_demon_drop_policy.h"
class Navi; class NaviState; class Vector3f;
NaviState* pc_demon_drop_state_create();
// Caller must revoke capture ownership first. Dry static floor prototype only.
bool pc_demon_drop_begin(Navi*,std::uint64_t generation,float damage,float speed);
void pc_demon_drop_post_physics(Navi*);
void pc_demon_drop_reset(Navi*);
P2DemonDropPhase pc_demon_drop_phase(Navi*);

void pc_demon_drop_before_transition(Navi*, int nextState);
void pc_demon_drop_scene_exit(); // Before exitStage nulls manager; no physics/state transitions.
