#pragma once

// Generated-placement bridge (lane 03/04, #242/#439).
//
// When the randomizer resolves a spawned generator to a seeded P2 source
// (`ENEMY_P2` target -> source id), the actor the engine actually instantiated
// is still a P1 stand-in (`genteki.cpp` replacement is a P1 type under the P2
// bridge). This dispatcher hands that actor to the seeded identity's module so
// the module can claim it (bind its own behaviour/visual/corpse to the
// randomizer-assigned slot). Returns true when a P2 module took the actor.
class BTeki;

bool pc_p2_generated_placement_bind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId);
