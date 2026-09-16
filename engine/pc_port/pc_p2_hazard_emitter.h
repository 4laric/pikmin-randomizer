#pragma once
#include "pc_p2_hazard_reaction.h"

// Lane 10 (receivers) emitter / attack-volume decision contract (#170/#408).
//
// A family emitter (the ElecBug discharge sweep, a dweevil discharge, a gas
// pipe) declares the element it delivers and asks this helper whether a
// candidate Pikmin would be affected. The helper is the *same* table the Pikmin
// receiver consults, so an emitter and its receiver cannot disagree about
// immunity. `false` means the emitter must not deliver the interaction
// (immune); `true` means the receiver will transit the named reaction state.
//
// Only the P2 electric/gas elements are routed through this table; fire and
// water emitters keep their own P1 receivers and do not use this helper.
// `gasInvincible` is the narrow `Piki::gasInvicible()` gate and is ignored for
// the electric element.
inline bool p2_emitter_accepts(int species, int hazard, bool gasInvincible) {
    return p2_hazard_reaction(species, hazard, gasInvincible) != P2HazardReactionNone;
}
