#pragma once

// Lane 30 (#242) ordinary spawned Sarai manager.
//
// Binds the private P2SaraiHost to the one teki actor the lane's arena spawns
// (the generated slot), so the Sarai runs its source captor behaviour against
// the live captain while the spawned actor stays the damage/lifetime anchor:
// real engine health, natural Pikmin damage, an engine corpse on death and the
// Pod delivery receipt. Default-off; only PIKMIN_SARAI_ORDINARY=1 selects it.
class BTeki;
class Graphics;
class Matrix4f;
class PelletView;

void pc_p2_sarai_manager_setup();
// Generated-placement bridge (lane 03/04): bind the P2 source-23 actor the
// randomizer spawned at `seedTargetUid` to a fresh Sarai host. Unlike setup()
// this does not read a fixed generator config; it claims the assigned actor.
bool pc_p2_sarai_manager_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned seedTargetUid);
void pc_p2_sarai_manager_reset();
void pc_p2_sarai_manager_forget(BTeki* actor);
void pc_p2_sarai_manager_update_actor(BTeki* actor);
bool pc_p2_sarai_manager_draw_actor(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse);
// Ordinary corpse receipt (lane 30, #242). Resolves the delivered dead-body
// PelletView of a bound Sarai anchor back to its generator so the Pod reward
// path can credit corpse:sarai:<generator>. Returns false for any body not
// owned by a bound Sarai.
bool pc_p2_sarai_receipt(PelletView* view, unsigned& generator);
int pc_p2_sarai_manager_bound_count();
