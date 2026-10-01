#pragma once
#include "pc_p2_species_policy.h"

// P2 Pikmin hazard-reaction routing, lane 10 receivers (#170/#408). This is the
// decision the electric/gas receivers make after the engine-level state/alive
// guards: immune species are rejected (None) and everything else is routed to
// the P2 reaction state that mirrors the decompilation. It is header-only so
// tools/test_p2_hazard_reaction.cpp can pin the table without linking the
// engine, following pc_p2_species_policy.h.
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0):
//   InteractDenki::actPiki :334, reject unless Yellow/Bulbmin (:347),
//                              transit PIKISTATE_DenkiDying (:348-349)
//   InteractGas::actPiki   :531, reject when gasInvicible (:533),
//                              reject unless White/Bulbmin (:543),
//                              transit PIKISTATE_Panic + PIKIPANIC_Gas (:550-552)

enum P2HazardReaction {
    P2HazardReactionNone = 0, // receiver rejects; no state change
    P2HazardReactionDenkiDying = 1, // -> PIKISTATE_DenkiDying
    P2HazardReactionGasPanic = 2, // -> PIKISTATE_Panic (gas)
};

// `gasInvincible` is the engine's narrow P2 gate (`Piki::gasInvicible()`); it
// only suppresses the gas reaction. Fire/water keep their own receivers and do
// not consult this helper (they return None here).
inline P2HazardReaction p2_hazard_reaction(int species, int hazard, bool gasInvincible) {
    if (hazard == P2HazardGas && gasInvincible) {
        return P2HazardReactionNone;
    }
    if (p2_species_immune(species, hazard)) {
        return P2HazardReactionNone;
    }
    switch (hazard) {
    case P2HazardElectric:
        return P2HazardReactionDenkiDying;
    case P2HazardGas:
        return P2HazardReactionGasPanic;
    default:
        return P2HazardReactionNone;
    }
}
