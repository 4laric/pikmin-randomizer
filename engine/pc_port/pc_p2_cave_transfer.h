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
inline bool p2_cave_parse(const std::string& text, const char* prefix,
                          P2CaveEntry& out, std::string& error) {
    std::istringstream in(text);
    std::string version;
    int count = 0;
    if (!(in >> version >> out.token >> out.floor >> out.health >> count)) {
        error = "header";
        return false;
    }
    out.schema = p2_cave_schema_from_version(version, prefix);
    if (out.schema < 0 || !p2_cave_token_valid(out.token)
        || (out.floor != 1 && out.floor != 2) || !std::isfinite(out.health)
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
    std::string extra;
    if (in >> extra || !in.eof()) {
        error = "trailing data";
        return false;
    }
    return true;
}

inline bool p2_cave_parse_entry(const std::string& text, P2CaveEntry& out, std::string& error) {
    return p2_cave_parse(text, "P2_CAVE_ENTRY", out, error);
}

inline bool p2_cave_parse_transfer(const std::string& text, P2CaveEntry& out, std::string& error) {
    return p2_cave_parse(text, "P2_CAVE_TRANSFER", out, error);
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
