#include "pc_p2_species.h"
#include "pc_p2_purple.h"
#include "Piki.h"
#include "PikiHeadItem.h"

int pc_p2_species(const Piki* piki) {
    if (!piki || (piki->mP2Purple && piki->mP2White)) return -1;
    if (piki->mP2White) return P2SpeciesWhite;
    if (piki->mP2Purple) return P2SpeciesPurple;
    return piki->mColor >= Blue && piki->mColor <= Yellow ? piki->mColor : -1;
}

int pc_p2_species(const PikiHeadItem* sprout) {
    if (!sprout || (sprout->mP2Purple && sprout->mP2White)) return -1;
    if (sprout->mP2White) return P2SpeciesWhite;
    if (sprout->mP2Purple) return P2SpeciesPurple;
    return sprout->mSeedColor >= Blue && sprout->mSeedColor <= Yellow ? sprout->mSeedColor : -1;
}

bool pc_p2_set_species(Piki* piki, int species) {
    if (!piki || species < P2SpeciesBlue || species > P2SpeciesWhite) return false;
    piki->initColor(species <= P2SpeciesYellow ? species : Red);
    piki->mP2Purple = species == P2SpeciesPurple;
    piki->mP2White = species == P2SpeciesWhite;
    return true;
}

bool pc_p2_set_species(PikiHeadItem* sprout, int species) {
    if (!sprout || species < P2SpeciesBlue || species > P2SpeciesWhite) return false;
    sprout->setColor(species <= P2SpeciesYellow ? species : Red);
    sprout->mP2Purple = species == P2SpeciesPurple;
    sprout->mP2White = species == P2SpeciesWhite;
    return true;
}

bool pc_p2_has_red_immunity(const Piki* piki) {
    return pc_p2_species(piki) == P2SpeciesRed;
}

