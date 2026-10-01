#pragma once
// Purple poison cloud at the head of a gassed Pikmin (pc_p2_gas_cloud_policy.h).
class Piki;

// PikiPanicState::init (gas flavour): start the cloud.
void pc_p2_gas_cloud_begin(Piki* piki);
// PikiPanicState::exec: puff at the head while the state runs.
void pc_p2_gas_cloud_update(Piki* piki);
// PikiPanicState::cleanup (cured or left) and Piki::doKill (death): stop every
// generator this Pikmin owns and log START/STOP. `death` selects the reason.
void pc_p2_gas_cloud_end(Piki* piki, bool death);
// Stage teardown (pc_p2_reset_all_teki): stop every remaining cloud.
void pc_p2_gas_cloud_reset();
