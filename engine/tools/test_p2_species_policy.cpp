#include "pc_p2_species_policy.h"
#include <cassert>
#include <cstdio>

// Lane 11 policy test: the per-species hazard receiver matrix must match the
// source `interactPiki.cpp` actPiki rejections exactly, and the species-only
// attack capabilities must not leak to other colors.
int main() {
    // Base colors: exactly one elemental immunity each.
    assert(p2_species_immune(P2SpeciesRed, P2HazardFire));
    assert(!p2_species_immune(P2SpeciesRed, P2HazardWater));
    assert(!p2_species_immune(P2SpeciesRed, P2HazardElectric));
    assert(!p2_species_immune(P2SpeciesRed, P2HazardGas));

    assert(p2_species_immune(P2SpeciesBlue, P2HazardWater));
    assert(!p2_species_immune(P2SpeciesBlue, P2HazardFire));

    assert(p2_species_immune(P2SpeciesYellow, P2HazardElectric));
    assert(!p2_species_immune(P2SpeciesYellow, P2HazardFire));

    // White: gas only, plus predator poisoning. No fire/water/electric.
    P2SpeciesCapability white = p2_species_capability(P2SpeciesWhite);
    assert(white.valid && white.poisonAttack);
    assert(white.immune[P2HazardGas]);
    assert(!white.immune[P2HazardFire] && !white.immune[P2HazardWater]
           && !white.immune[P2HazardElectric]);
    assert(!white.impactAttack);

    // Purple: no elemental immunity; impact attack only.
    P2SpeciesCapability purple = p2_species_capability(P2SpeciesPurple);
    assert(purple.valid && purple.impactAttack && !purple.poisonAttack);
    for (int h = 0; h < P2HazardCount; ++h) assert(!purple.immune[h]);

    // Bulbmin: immune to every hazard, no special attack.
    P2SpeciesCapability bulbmin = p2_species_capability(P2SpeciesBulbmin);
    assert(bulbmin.valid);
    for (int h = 0; h < P2HazardCount; ++h) assert(bulbmin.immune[h]);
    assert(!bulbmin.poisonAttack && !bulbmin.impactAttack);

    // Only White poisons and only Purple impacts.
    for (int s = 0; s <= P2SpeciesBulbmin; ++s) {
        P2SpeciesCapability c = p2_species_capability(s);
        if (s != P2SpeciesWhite) assert(!c.poisonAttack);
        if (s != P2SpeciesPurple) assert(!c.impactAttack);
    }

    // Unknown species and out-of-range hazard are rejected, never defaulted to
    // an immunity.
    assert(!p2_species_capability(99).valid);
    assert(!p2_species_immune(99, P2HazardFire));
    assert(!p2_species_immune(P2SpeciesRed, -1));
    assert(!p2_species_immune(P2SpeciesRed, P2HazardCount));

    std::puts("PASS P2_SPECIES_POLICY");
    return 0;
}
