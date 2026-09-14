#include "pc_p2_species_policy.h"
#include <cassert>
#include <cstdio>

// Lane 10 electric/gas receiver test (#170/#408). The new P2 receivers route
// immunity through the lane-11 matrix exactly like the existing Fire/Bubble
// receivers:
//   InteractDenki::actPiki -> p2_species_immune(..., P2HazardElectric)
//   InteractGas::actPiki   -> p2_species_immune(..., P2HazardGas)
// A true `*_immune` result is the receiver returning false (rejecting the
// stimulus); false means it applies the shock/gas reaction.
// Source basis (native/pikmin2-research/src/plugProjectKandoU/interactPiki.cpp):
//   InteractDenki::actPiki :334 rejects unless Yellow or Bulbmin    (:347)
//   InteractGas::actPiki   :531 rejects unless White or Bulbmin     (:543)
// This is an engine-double test: it pins the receiver decision table without
// linking the engine (the receiver itself is compiled by the pikmin_pc build).
static bool denki_immune(int species) { return p2_species_immune(species, P2HazardElectric); }
static bool gas_immune(int species) { return p2_species_immune(species, P2HazardGas); }

int main() {
    // Electric: only Yellow and Bulbmin are immune (receiver returns false);
    // every other species is accepted.
    assert(denki_immune(P2SpeciesYellow));
    assert(denki_immune(P2SpeciesBulbmin));
    assert(!denki_immune(P2SpeciesRed));
    assert(!denki_immune(P2SpeciesBlue));
    assert(!denki_immune(P2SpeciesPurple));
    assert(!denki_immune(P2SpeciesWhite));

    // Gas: only White and Bulbmin are immune.
    assert(gas_immune(P2SpeciesWhite));
    assert(gas_immune(P2SpeciesBulbmin));
    assert(!gas_immune(P2SpeciesRed));
    assert(!gas_immune(P2SpeciesBlue));
    assert(!gas_immune(P2SpeciesYellow));
    assert(!gas_immune(P2SpeciesPurple));

    // Full table keyed by P2PikminSpecies order (Blue, Red, Yellow, Purple,
    // White, Bulbmin): the immune sets must not leak to other species.
    static const bool electricImmune[] = { false, false, true, false, false, true };
    static const bool gasImmune[]      = { false, false, false, false, true, true };
    for (int s = P2SpeciesBlue; s <= P2SpeciesBulbmin; ++s) {
        assert(denki_immune(s) == electricImmune[s]);
        assert(gas_immune(s) == gasImmune[s]);
    }

    // Unknown species are never treated as immune, so the receiver accepts.
    assert(!denki_immune(-1));
    assert(!denki_immune(99));
    assert(!gas_immune(-1));
    assert(!gas_immune(99));

    std::puts("PASS P2_ELEMENTAL_RECEIVERS");
    return 0;
}
