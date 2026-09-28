#pragma once

class Piki;
struct PikiHeadItem;

enum P2PikminSpecies {
    P2SpeciesBlue = 0,
    P2SpeciesRed = 1,
    P2SpeciesYellow = 2,
    P2SpeciesPurple = 3,
    P2SpeciesWhite = 4,
    P2SpeciesBulbmin = 5, // source Piki.h Bulbmin = 5; no base-color mapping
};

int pc_p2_species(const Piki* piki);
int pc_p2_species(const PikiHeadItem* sprout);
bool pc_p2_set_species(Piki* piki, int species);
bool pc_p2_set_species(PikiHeadItem* sprout, int species);
bool pc_p2_has_red_immunity(const Piki* piki);

// Bulbmin identity. Wild/recruited lifecycle and dependent ownership live in
// pc_p2_bulbmin_policy.h; this adapter only carries the species flag so the
// captain/cave/receiver layers can recognize it.
bool pc_p2_is_bulbmin(const Piki* piki);
void pc_p2_make_bulbmin(Piki* piki);
