#include "pc_p2_species_schema.h"
#include <cassert>
#include <cstdio>

// Lane 11 policy test: the versioned species/compartment schema must match the
// cave wire numbering (v1 already carried Purple), reject unknown versions and
// new species in old readers, and conserve totals.
int main() {
    assert(p2_schema_valid(P2SpeciesSchemaPurple));
    assert(p2_schema_valid(P2SpeciesSchemaWhite));
    assert(p2_schema_valid(P2SpeciesSchemaBulbmin));
    assert(!p2_schema_valid(0) && !p2_schema_valid(4) && !p2_schema_valid(-1));

    assert(p2_schema_max_species(P2SpeciesSchemaPurple) == P2SpeciesPurple);
    assert(p2_schema_max_species(P2SpeciesSchemaWhite) == P2SpeciesWhite);
    assert(p2_schema_max_species(P2SpeciesSchemaBulbmin) == P2SpeciesBulbmin);
    assert(p2_schema_max_species(99) == -1);

    // Minimum version that can carry each species (used by the cave writer).
    assert(p2_schema_required_for_species(P2SpeciesBlue) == 1);
    assert(p2_schema_required_for_species(P2SpeciesPurple) == 1);
    assert(p2_schema_required_for_species(P2SpeciesWhite) == 2);
    assert(p2_schema_required_for_species(P2SpeciesBulbmin) == 3);
    assert(p2_schema_required_for_species(99) == -1);

    // Each version admits only its own species and older ones.
    assert(p2_schema_supports(P2SpeciesSchemaPurple, P2SpeciesPurple));
    assert(!p2_schema_supports(P2SpeciesSchemaPurple, P2SpeciesWhite));
    assert(!p2_schema_supports(P2SpeciesSchemaPurple, P2SpeciesBulbmin));
    assert(p2_schema_supports(P2SpeciesSchemaWhite, P2SpeciesWhite));
    assert(!p2_schema_supports(P2SpeciesSchemaWhite, P2SpeciesBulbmin));
    assert(p2_schema_supports(P2SpeciesSchemaBulbmin, P2SpeciesBulbmin));
    assert(!p2_schema_supports(99, P2SpeciesBlue));

    // Old readers keep working and reject a newer species explicitly.
    P2SpeciesCounts v1;
    v1.count[P2SpeciesBlue] = 7;
    v1.count[P2SpeciesPurple] = 3;
    assert(p2_schema_validate(P2SpeciesSchemaPurple, v1));
    assert(p2_schema_total(v1) == 10);

    P2SpeciesCounts withWhite = v1;
    withWhite.count[P2SpeciesWhite] = 1;
    assert(!p2_schema_validate(P2SpeciesSchemaPurple, withWhite)); // v1 cannot carry White
    assert(p2_schema_validate(P2SpeciesSchemaWhite, withWhite));

    P2SpeciesCounts withBulbmin = withWhite;
    withBulbmin.count[P2SpeciesBulbmin] = 2;
    assert(!p2_schema_validate(P2SpeciesSchemaWhite, withBulbmin)); // v2 cannot carry Bulbmin
    assert(p2_schema_validate(P2SpeciesSchemaBulbmin, withBulbmin));
    assert(p2_schema_total(withBulbmin) == 13);

    // Negative counts and unknown versions are always rejected.
    P2SpeciesCounts bad = withBulbmin;
    bad.count[P2SpeciesWhite] = -1;
    assert(!p2_schema_validate(P2SpeciesSchemaBulbmin, bad));
    assert(!p2_schema_validate(0, withBulbmin));

    std::puts("PASS P2_SPECIES_SCHEMA");
    return 0;
}
