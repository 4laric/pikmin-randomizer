#pragma once
#include "pc_p2_species_schema.h"

#include <cmath>
#include <sstream>
#include <string>
#include <vector>

// P2 cave checkpoint wire format, lane 11 (#131/#112).
//
// A cave checkpoint is a token-authenticated, versioned transfer of the living
// Pikmin squad plus captain health. The entry header names the schema the reader
// must apply; the transfer header names the schema required to carry the squad.
// This header is engine-free so `tools/test_p2_cave_transfer.cpp` can pin the
// exact encode/decode the engine uses, including the lane-11 Bulbmin schema.
//
// Entry:    P2_CAVE_ENTRY_<schema> <32-hex token> <floor> <health> <count>
//           <species> <maturity>            (count lines)
// Transfer: P2_CAVE_TRANSFER_<schema> <32-hex token> <floor> <health> <count>
//           <species> <maturity>            (count lines)
//
// The two headers differ only in name/direction; both carry the squad. Schema 3
// is required to carry Bulbmin, and an old reader must reject it explicitly.

enum { P2CaveMaxSurvivors = 100 };

// Absolute floor-id ceiling for chained multi-floor payloads (issue #132).
// Covers the 9-floor P0 maximum with headroom; the supervisor enforces each
// cave's own floor count on top. Old readers never see past floor 2: a
// chained payload is trailing data to them, and an unchained floor beyond 2
// still fails the legacy range, so the bump rule is preserved on both paths.
enum { P2CaveMaxFloors = 16 };

struct P2CaveSurvivor {
    int species = -1;
    int maturity = 0;
};

struct P2CaveEntry {
    int schema = P2SpeciesSchemaPurple;
    std::string token;
    int floor = 0;
    float health = 0.0f;
    std::vector<P2CaveSurvivor> squad;
};

// One link of the per-floor revision chain (issue #132): the checkpoint
// revision written for the header floor. The ordered checkpoint sequence
// across floors is the chain; the wire carries the current link. Monotonicity
// (revision == floor-1 while active, == floor when exited) is enforced by the
// supervisor, which holds the prior checkpoint; the native parse only checks
// shape, range and header agreement.
struct P2CaveFloorChain {
    int floor = 0;
    int revision = 0;
};

inline int p2_cave_schema_from_version(const std::string& version, const char* prefix) {
    const std::string base(prefix);
    if (version == base + "_1") return P2SpeciesSchemaPurple;
    if (version == base + "_2") return P2SpeciesSchemaWhite;
    if (version == base + "_3") return P2SpeciesSchemaBulbmin;
    return -1;
}

inline bool p2_cave_token_valid(const std::string& token) {
    if (token.size() != 32) return false;
    for (char c : token) {
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    }
    return true;
}

// Parse either header. `prefix` is "P2_CAVE_ENTRY" or "P2_CAVE_TRANSFER".
// On failure `error` names the failing clause ("header", "Pikmin",
// "trailing data") exactly as the engine reports it.
//
// `maxFloor` bounds the accepted header floor and `chained` requires exactly
// one trailing identity line `P2_CAVE_CHAIN <floor> <revision>` repeating the
// header floor (1..P2CaveMaxFloors) with a non-negative revision. Legacy
// callers use maxFloor=2 without the chain line; anything chained is trailing
// data to them, and an unchained floor beyond 2 still fails the legacy range.
inline bool p2_cave_parse_ranged(const std::string& text, const char* prefix,
                                 P2CaveEntry& out, std::string& error,
                                 int maxFloor, bool chained, P2CaveFloorChain* chain) {
    std::istringstream in(text);
    std::string version;
    int count = 0;
    if (!(in >> version >> out.token >> out.floor >> out.health >> count)) {
        error = "header";
        return false;
    }
    out.schema = p2_cave_schema_from_version(version, prefix);
    if (out.schema < 0 || !p2_cave_token_valid(out.token)
        || out.floor < 1 || out.floor > maxFloor || !std::isfinite(out.health)
        || out.health <= 0 || out.health > 1 || count < 1 || count > P2CaveMaxSurvivors) {
        error = "header";
        return false;
    }
    out.squad.clear();
    for (int i = 0; i < count; ++i) {
        P2CaveSurvivor s;
        if (!(in >> s.species >> s.maturity) || !p2_schema_supports(out.schema, s.species)
            || s.maturity < 0 || s.maturity > 2) {
            error = "Pikmin";
            return false;
        }
        out.squad.push_back(s);
    }
    if (!chained) {
        std::string extra;
        if (in >> extra || !in.eof()) {
            error = "trailing data";
            return false;
        }
        return true;
    }
    std::string marker;
    int chainFloor = 0, chainRevision = -1;
    if (!(in >> marker >> chainFloor >> chainRevision) || marker != "P2_CAVE_CHAIN"
        || chainFloor != out.floor || chainRevision < 0) {
        error = "trailing data";
        return false;
    }
    std::string extra;
    if (in >> extra || !in.eof()) {
        error = "trailing data";
        return false;
    }
    if (chain) {
        chain->floor = chainFloor;
        chain->revision = chainRevision;
    }
    return true;
}

inline bool p2_cave_parse(const std::string& text, const char* prefix,
                          P2CaveEntry& out, std::string& error) {
    return p2_cave_parse_ranged(text, prefix, out, error, 2, false, nullptr);
}

inline bool p2_cave_parse_entry(const std::string& text, P2CaveEntry& out, std::string& error) {
    return p2_cave_parse(text, "P2_CAVE_ENTRY", out, error);
}

inline bool p2_cave_parse_transfer(const std::string& text, P2CaveEntry& out, std::string& error) {
    return p2_cave_parse(text, "P2_CAVE_TRANSFER", out, error);
}

// Chained multi-floor parse (issue #132): same species-schema header, floor
// 1..P2CaveMaxFloors, plus the required P2_CAVE_CHAIN identity line.
inline bool p2_cave_parse_chained(const std::string& text, const char* prefix,
                                  P2CaveEntry& out, P2CaveFloorChain& chain,
                                  std::string& error) {
    return p2_cave_parse_ranged(text, prefix, out, error, P2CaveMaxFloors, true, &chain);
}

inline bool p2_cave_parse_entry_chained(const std::string& text, P2CaveEntry& out,
                                        P2CaveFloorChain& chain, std::string& error) {
    return p2_cave_parse_chained(text, "P2_CAVE_ENTRY", out, chain, error);
}

inline bool p2_cave_parse_transfer_chained(const std::string& text, P2CaveEntry& out,
                                           P2CaveFloorChain& chain, std::string& error) {
    return p2_cave_parse_chained(text, "P2_CAVE_TRANSFER", out, chain, error);
}

// The transfer schema must be at least the entry schema and at least the schema
// required by every surviving species, so a Bulbmin is never written into a
// payload an older reader would silently accept.
inline int p2_cave_transfer_schema(int entrySchema, const std::vector<P2CaveSurvivor>& squad) {
    int writeSchema = entrySchema;
    for (const auto& s : squad) {
        const int required = p2_schema_required_for_species(s.species);
        if (required > writeSchema) writeSchema = required;
    }
    return writeSchema;
}

inline std::string p2_cave_format_transfer(const P2CaveEntry& e) {
    const int writeSchema = p2_cave_transfer_schema(e.schema, e.squad);
    std::ostringstream out;
    out.precision(9);
    out << "P2_CAVE_TRANSFER_" << writeSchema << '\n' << e.token << '\n'
        << e.floor << ' ' << e.health << ' ' << e.squad.size() << '\n';
    for (const auto& s : e.squad) out << s.species << ' ' << s.maturity << '\n';
    return out.str();
}

// Chained multi-floor format (issue #132): the base payload plus the current
// revision-chain link. Callers must pass in-range floor/revision values; the
// supervisor enforces the cave's floor count and revision monotonicity, and
// the parser above rejects anything out of range. `which` selects the ENTRY
// or TRANSFER header name.
inline std::string p2_cave_format_chained(const P2CaveEntry& e, const char* prefix, int revision) {
    const int writeSchema = p2_cave_transfer_schema(e.schema, e.squad);
    std::ostringstream out;
    out.precision(9);
    out << prefix << "_" << writeSchema << '\n' << e.token << '\n'
        << e.floor << ' ' << e.health << ' ' << e.squad.size() << '\n';
    for (const auto& s : e.squad) out << s.species << ' ' << s.maturity << '\n';
    out << "P2_CAVE_CHAIN " << e.floor << ' ' << revision << '\n';
    return out.str();
}

inline std::string p2_cave_format_chained_transfer(const P2CaveEntry& e, int revision) {
    return p2_cave_format_chained(e, "P2_CAVE_TRANSFER", revision);
}

inline std::string p2_cave_format_chained_entry(const P2CaveEntry& e, int revision) {
    return p2_cave_format_chained(e, "P2_CAVE_ENTRY", revision);
}
