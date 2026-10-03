#include "pc_p2_original_throw.h"
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_species.h"
int pc_p2_original_rgb_throw_species(const Piki* piki) {
    OriginalPikiBody body;
    if(!pc_p2_original_piki_body_query(piki,body) || body.state.wild
        || body.state.species>P2SpeciesYellow || pc_p2_species(piki)!=body.state.species) return -1;
    return body.state.species;
}
