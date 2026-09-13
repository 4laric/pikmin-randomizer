#pragma once

class Piki;
struct PikiHeadItem;

enum P2PikminSpecies {
    P2SpeciesBlue = 0,
    P2SpeciesRed = 1,
    P2SpeciesYellow = 2,
    P2SpeciesPurple = 3,
    P2SpeciesWhite = 4,
};

int pc_p2_species(const Piki* piki);
int pc_p2_species(const PikiHeadItem* sprout);
bool pc_p2_set_species(Piki* piki, int species);
bool pc_p2_set_species(PikiHeadItem* sprout, int species);
bool pc_p2_has_red_immunity(const Piki* piki);

