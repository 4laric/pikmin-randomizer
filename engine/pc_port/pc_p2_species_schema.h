#pragma once
#include "pc_p2_species.h"

// Versioned species / compartment schema for P2 cave checkpoints and ship
// storage, lane 11 (#131/#395). Coordinate the exact wire schema with #131 and
// the seed/manifest bridge (#132) before either endpoint changes.
//
// The numbering matches the existing cave wire format (`pc_p2_cave.cpp`
// `P2_CAVE_ENTRY_1/2`, `P2_CAVE_TRANSFER_n`); schema 1 already carried Purple.
//
//   v1: Blue, Red, Yellow, Purple
//   v2: + White
//   v3: + Bulbmin
//
// Requirement (#395): retain old schema behavior and reject unsupported or new
// species explicitly in old readers, so Bulbmin needs schema 3 rather than
// widening schema 2 (which would let an old reader silently reinterpret an ID).
//
// Invariants enforced by the policy test:
//   1. An unknown version is rejected, never treated as the latest.
//   2. A reader rejects a nonzero count of a species newer than its version.
//   3. Negative counts are rejected.
//   4. Total population is the exact sum of its compartments.

enum P2SpeciesSchema {
    P2SpeciesSchemaPurple = 1,   // Blue, Red, Yellow, Purple
    P2SpeciesSchemaWhite = 2,    // + White
    P2SpeciesSchemaBulbmin = 3,  // + Bulbmin
    P2SpeciesSchemaLatest = P2SpeciesSchemaBulbmin,
};

// Highest species id a reader of `version` may legally see, or -1 if the
// version itself is unknown.
inline int p2_schema_max_species(int version) {
    switch (version) {
    case P2SpeciesSchemaPurple: return P2SpeciesPurple;
    case P2SpeciesSchemaWhite: return P2SpeciesWhite;
    case P2SpeciesSchemaBulbmin: return P2SpeciesBulbmin;
    default: return -1;
    }
}

// Minimum schema version that can carry `species`; -1 if the species is
// unknown.
inline int p2_schema_required_for_species(int species) {
    switch (species) {
    case P2SpeciesBlue:
    case P2SpeciesRed:
    case P2SpeciesYellow:
    case P2SpeciesPurple: return P2SpeciesSchemaPurple;
    case P2SpeciesWhite: return P2SpeciesSchemaWhite;
    case P2SpeciesBulbmin: return P2SpeciesSchemaBulbmin;
    default: return -1;
    }
}

inline bool p2_schema_valid(int version) {
    return p2_schema_max_species(version) >= 0;
}

inline bool p2_schema_supports(int version, int species) {
    const int max = p2_schema_max_species(version);
    return max >= 0 && species >= P2SpeciesBlue && species <= max;
}

// Fixed per-species compartment counts (ship storage, field squad, transient
// occupants). Index by P2PikminSpecies.
struct P2SpeciesCounts {
    int count[P2SpeciesBulbmin + 1] = {};
};

inline int p2_schema_total(const P2SpeciesCounts& c) {
    int total = 0;
    for (int s = 0; s <= P2SpeciesBulbmin; ++s) total += c.count[s];
    return total;
}

// Reject an unknown version, a negative count, or a nonzero count of a species
// newer than the version. A version-2 payload carrying Bulbmin is invalid; a
// version-3 reader accepts everything.
inline bool p2_schema_validate(int version, const P2SpeciesCounts& c) {
    const int max = p2_schema_max_species(version);
    if (max < 0) return false;
    for (int s = 0; s <= P2SpeciesBulbmin; ++s) {
        if (c.count[s] < 0) return false;
        if (s > max && c.count[s] != 0) return false;
    }
    return true;
}
