// Lane 10 emitter/attack-volume acceptance table (#170/#408).
//
// Pins that the emitter target decision is the receiver decision: an emitter
// must reject exactly the species `InteractDenki`/`InteractGas` reject, so a
// family emitter cannot disagree with the lane-10 receiver about immunity.
// Header-only, following tools/test_p2_hazard_reaction.cpp.
#include "pc_p2_hazard_emitter.h"

#include <cassert>
#include <cstdio>

int main() {
    // Electric (InteractDenki): source rejects only Yellow and Bulbmin.
    assert(!p2_emitter_accepts(P2SpeciesYellow, P2HazardElectric, false));
    assert(!p2_emitter_accepts(P2SpeciesBulbmin, P2HazardElectric, false));
    assert(p2_emitter_accepts(P2SpeciesBlue, P2HazardElectric, false));
    assert(p2_emitter_accepts(P2SpeciesRed, P2HazardElectric, false));
    assert(p2_emitter_accepts(P2SpeciesPurple, P2HazardElectric, false));
    assert(p2_emitter_accepts(P2SpeciesWhite, P2HazardElectric, false));
    // The gas gate is irrelevant to the electric element.
    assert(!p2_emitter_accepts(P2SpeciesYellow, P2HazardElectric, true));

    // Gas (InteractGas): source rejects White and Bulbmin, and a gas-invincible
    // Piki is rejected before the species gate.
    assert(!p2_emitter_accepts(P2SpeciesWhite, P2HazardGas, false));
    assert(!p2_emitter_accepts(P2SpeciesBulbmin, P2HazardGas, false));
    assert(p2_emitter_accepts(P2SpeciesRed, P2HazardGas, false));
    assert(p2_emitter_accepts(P2SpeciesYellow, P2HazardGas, false));
    assert(!p2_emitter_accepts(P2SpeciesRed, P2HazardGas, true));

    // An unmapped species id falls through to the reaction exactly as the
    // receiver does (only a valid immune capability rejects), so the emitter
    // and receiver stay in lockstep. See test_p2_hazard_reaction.cpp.
    assert(p2_emitter_accepts(99, P2HazardElectric, false));

    std::puts("PASS P2_HAZARD_EMITTER");
    return 0;
}
