#include "pc_p2_species.h"
#include "pc_p2_purple.h"
#include "Piki.h"
#include "PikiHeadItem.h"

namespace {
// P2 sequel species are mutually exclusive; a doubly-flagged Piki is invalid.
int p2_species_conflicts(bool purple, bool white, bool bulbmin) {
    return int(purple) + int(white) + int(bulbmin);
}
}

int pc_p2_species(const Piki* piki) {
    if (!piki
        || p2_species_conflicts(piki->mP2Purple, piki->mP2White, piki->mP2Bulbmin) > 1)
        return -1;
    if (piki->mP2Bulbmin) return P2SpeciesBulbmin;
    if (piki->mP2White) return P2SpeciesWhite;
    if (piki->mP2Purple) return P2SpeciesPurple;
    return piki->mColor >= Blue && piki->mColor <= Yellow ? piki->mColor : -1;
}

int pc_p2_species(const PikiHeadItem* sprout) {
    if (!sprout
        || p2_species_conflicts(sprout->mP2Purple, sprout->mP2White, sprout->mP2Bulbmin) > 1)
        return -1;
    if (sprout->mP2Bulbmin) return P2SpeciesBulbmin;
    if (sprout->mP2White) return P2SpeciesWhite;
    if (sprout->mP2Purple) return P2SpeciesPurple;
    return sprout->mSeedColor >= Blue && sprout->mSeedColor <= Yellow ? sprout->mSeedColor : -1;
}

bool pc_p2_set_species(Piki* piki, int species) {
    if (!piki || species < P2SpeciesBlue || species > P2SpeciesBulbmin) return false;
    piki->initColor(species <= P2SpeciesYellow ? species : Red);
    piki->mP2Purple = species == P2SpeciesPurple;
    piki->mP2White = species == P2SpeciesWhite;
    piki->mP2Bulbmin = species == P2SpeciesBulbmin;
    return true;
}

bool pc_p2_set_species(PikiHeadItem* sprout, int species) {
    if (!sprout || species < P2SpeciesBlue || species > P2SpeciesBulbmin) return false;
    sprout->setColor(species <= P2SpeciesYellow ? species : Red);
    sprout->mP2Purple = species == P2SpeciesPurple;
    sprout->mP2White = species == P2SpeciesWhite;
    sprout->mP2Bulbmin = species == P2SpeciesBulbmin;
    return true;
}

bool pc_p2_has_red_immunity(const Piki* piki) {
    return pc_p2_species(piki) == P2SpeciesRed;
}

bool pc_p2_is_bulbmin(const Piki* piki) {
    return piki && piki->mP2Bulbmin;
}

void pc_p2_make_bulbmin(Piki* piki) {
    if (!piki) return;
    piki->mP2Purple = false;
    piki->mP2White = false;
    piki->mP2Bulbmin = true;
    // Identity/colour only. The source piki_kochappy model binding and the
    // Mother Bulbmin birth/whistle lifecycle land with the LeafChappy actor
    // (see docs/PIKMIN2_BULBMIN_CONTRACT.md).
    piki->mCurrentColour = piki->mDefaultColour = piki->mStartBlendColour
        = piki->mTargetBlendColour = Colour(120, 180, 90, 255);
}
