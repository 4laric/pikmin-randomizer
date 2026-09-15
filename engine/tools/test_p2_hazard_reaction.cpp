#include "pc_p2_hazard_reaction.h"
#include <cassert>
#include <cstdio>

// Lane 10 reaction-routing test (#170/#408). The electric receiver must route
// every non-immune species to the DenkiDying state and the gas receiver every
// non-immune, non-gas-invincible species to the Panic state. Immune species and
// gas-invincible Piki must be rejected (None), so the receivers keep the
// immunity gate intact and leave existing behavior untouched.
//
// Source basis (native/pikmin2-research, src/plugProjectKandoU/interactPiki.cpp):
//   InteractDenki::actPiki :334 -> PIKISTATE_DenkiDying           (:347-349)
//   InteractGas::actPiki   :531 -> gasInvicible gate (:533),
//                            PIKISTATE_Panic PIKIPANIC_Gas        (:542-552)
// This is an engine-double test: the receivers themselves are compiled and
// linked by the pikmin_pc build.
int main() {
    // Electric: only Yellow and Bulbmin are immune; every other species is
    // routed to DenkiDying (electric death).
    assert(p2_hazard_reaction(P2SpeciesYellow, P2HazardElectric, false) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesBulbmin, P2HazardElectric, false) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesRed, P2HazardElectric, false) == P2HazardReactionDenkiDying);
    assert(p2_hazard_reaction(P2SpeciesBlue, P2HazardElectric, false) == P2HazardReactionDenkiDying);
    assert(p2_hazard_reaction(P2SpeciesPurple, P2HazardElectric, false) == P2HazardReactionDenkiDying);
    assert(p2_hazard_reaction(P2SpeciesWhite, P2HazardElectric, false) == P2HazardReactionDenkiDying);

    // Gas: only White and Bulbmin are immune; every other species panics.
    assert(p2_hazard_reaction(P2SpeciesWhite, P2HazardGas, false) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesBulbmin, P2HazardGas, false) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesRed, P2HazardGas, false) == P2HazardReactionGasPanic);
    assert(p2_hazard_reaction(P2SpeciesBlue, P2HazardGas, false) == P2HazardReactionGasPanic);
    assert(p2_hazard_reaction(P2SpeciesYellow, P2HazardGas, false) == P2HazardReactionGasPanic);
    assert(p2_hazard_reaction(P2SpeciesPurple, P2HazardGas, false) == P2HazardReactionGasPanic);

    // The gas-invincibility gate suppresses only the gas reaction, and only for
    // a species that would otherwise panic. It never affects electricity.
    assert(p2_hazard_reaction(P2SpeciesRed, P2HazardGas, true) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesWhite, P2HazardGas, true) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesBulbmin, P2HazardGas, true) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesRed, P2HazardElectric, true) == P2HazardReactionDenkiDying);

    // Fire and water keep their existing receivers and never select a new
    // reaction through this helper.
    assert(p2_hazard_reaction(P2SpeciesRed, P2HazardFire, false) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesBlue, P2HazardWater, false) == P2HazardReactionNone);

    // Unknown species are not immune, so they follow the non-immune path; an
    // out-of-range hazard never selects a reaction.
    assert(p2_hazard_reaction(99, P2HazardElectric, false) == P2HazardReactionDenkiDying);
    assert(p2_hazard_reaction(99, P2HazardGas, false) == P2HazardReactionGasPanic);
    assert(p2_hazard_reaction(P2SpeciesRed, -1, false) == P2HazardReactionNone);
    assert(p2_hazard_reaction(P2SpeciesRed, P2HazardCount, false) == P2HazardReactionNone);

    std::puts("PASS P2_HAZARD_REACTION");
    return 0;
}
