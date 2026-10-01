#pragma once
#include "pc_p2_species.h"

// P2 species hazard capability matrix, lane 11 of
// docs/PIKMIN2_IMPLEMENTATION_FANOUT.md. This is the enemy-facing capability
// definition lane 10 (receivers) consumes: which hazards each Pikmin species
// rejects at its `actPiki` receiver, plus the species-only attack capabilities
// (Purple impact, White poison).
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0,
// src/plugProjectKandoU/interactPiki.cpp):
//   InteractDenki::actPiki   :334, reject unless Yellow or Bulbmin      (:347)
//   InteractFire::actPiki    :445, reject unless Red or Bulbmin         (:453)
//   InteractBubble::actPiki  :503, reject unless Blue or Bulbmin        (:511)
//   InteractGas::actPiki     :531, reject unless White or Bulbmin       (:543)
// Purple has no elemental immunity; its damage is the impact attack (#393).
// A source-backed N/A is recorded rather than borrowing a similarly named
// P1 field.

enum P2HazardKind {
    P2HazardFire = 0,
    P2HazardWater = 1, // InteractBubble
    P2HazardElectric = 2, // InteractDenki
    P2HazardGas = 3, // InteractGas
    P2HazardCount = 4,
};

struct P2SpeciesCapability {
    int species;
    bool immune[P2HazardCount];
    bool poisonAttack; // poisoning a predator that swallows it (White only)
    bool impactAttack; // hipdrop/earthquake on landing (Purple only)
    bool valid;
};

inline P2SpeciesCapability p2_species_capability(int species) {
    P2SpeciesCapability c{};
    c.species = species;
    c.valid = true;
    switch (species) {
    case P2SpeciesBlue:
        c.immune[P2HazardWater] = true;
        break;
    case P2SpeciesRed:
        c.immune[P2HazardFire] = true;
        break;
    case P2SpeciesYellow:
        c.immune[P2HazardElectric] = true;
        break;
    case P2SpeciesPurple:
        c.impactAttack = true;
        break;
    case P2SpeciesWhite:
        c.immune[P2HazardGas] = true;
        c.poisonAttack = true;
        break;
    case P2SpeciesBulbmin:
        for (int h = 0; h < P2HazardCount; ++h) c.immune[h] = true;
        break;
    default:
        c.valid = false;
        break;
    }
    return c;
}

inline bool p2_species_immune(int species, int hazard) {
    if (hazard < 0 || hazard >= P2HazardCount) return false;
    P2SpeciesCapability c = p2_species_capability(species);
    return c.valid && c.immune[hazard];
}
