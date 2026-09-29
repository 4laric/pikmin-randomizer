#pragma once
#include <istream>
#include <string>
#include <vector>

// Data-driven campaign proxy table (#871). Engine-free, header-only so the
// standalone test needs only pc_port. File format:
//
//   P2_PROXY_CAMPAIGN_1 <count>
//   <source_id> <Species> <host_teki_type>
//   ...
namespace p2proxy {
struct Row {
    unsigned source;
    std::string species;
    int host;
};
struct Table {
    std::vector<Row> rows;
    bool valid = false;
    std::string error;
};

inline bool validSpecies(const std::string& species) {
    if (species.empty() || species.size() > 32) return false;
    const char first = species[0];
    if (!((first >= 'A' && first <= 'Z') || (first >= 'a' && first <= 'z'))) return false;
    for (std::string::size_type i = 1; i < species.size(); ++i) {
        const char c = species[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
                || c == '_'))
            return false;
    }
    return true;
}

// Pikmin 1 teki types a proxy row may name as its host. Everything else is
// refused: the placeholder types (26-29, 34) crash on birth, TEKI_P2Demon (35)
// is a lane-30 spawn identity, and the rest (spawners, plants, clam parts, egg,
// Progg, geyser) are not free-standing enemies. Mirrors the root allowlist in
// randomizer/p2_proxy/__init__.py.
inline bool safeHost(int host) {
    switch (host) {
    case 0: case 2: case 3: case 4: case 6: case 8: case 9: case 11: case 15: case 16:
    case 17: case 18: case 19: case 20: case 24: case 25: case 30: case 31: case 32: case 33:
        return true;
    default: return false;
    }
}

inline Table parse(std::istream& in, bool (*bindable)(unsigned), int tekiTypeCount) {
    Table table;
    const auto fail = [&table](const std::string& message) {
        table.valid = false;
        table.error = message;
        table.rows.clear();
        return table;
    };
    std::string header;
    long long countValue = 0;
    if (!(in >> header >> countValue)) return fail("bad header");
    if (header != "P2_PROXY_CAMPAIGN_1") return fail("bad header token");
    if (countValue < 1 || countValue > 64) return fail("bad count");
    const int count = int(countValue);
    std::vector<Row> rows;
    for (int i = 0; i < count; ++i) {
        long long sourceValue = 0;
        long long hostValue = 0;
        std::string species;
        if (!(in >> sourceValue >> species >> hostValue)) return fail("fewer rows than count");
        if (sourceValue < 0 || sourceValue > 4294967295LL) return fail("bad source id");
        const unsigned source = unsigned(sourceValue);
        if (bindable == nullptr || !bindable(source)) return fail("source not bindable");
        if (!validSpecies(species)) return fail("bad species");
        if (hostValue < 0 || hostValue >= (long long)tekiTypeCount) return fail("bad host type");
        if (!safeHost(int(hostValue))) return fail("unsafe host type");
        for (const Row& existing : rows) {
            if (existing.source == source) return fail("duplicate source");
            if (existing.species == species) return fail("duplicate species");
        }
        Row row;
        row.source = source;
        row.species = species;
        row.host = int(hostValue);
        rows.push_back(row);
    }
    std::string trailing;
    if (in >> trailing) return fail("trailing data");
    table.rows = rows;
    table.valid = true;
    table.error.clear();
    return table;
}

inline const Row* bySource(const Table& table, unsigned source) {
    for (std::vector<Row>::size_type i = 0; i < table.rows.size(); ++i)
        if (table.rows[i].source == source) return &table.rows[i];
    return nullptr;
}

inline const Row* bySpecies(const Table& table, const std::string& species) {
    for (std::vector<Row>::size_type i = 0; i < table.rows.size(); ++i)
        if (table.rows[i].species == species) return &table.rows[i];
    return nullptr;
}

// Drop rows whose source has a static host (#871 D2). Engine-free: the caller
// supplies the static predicate (the loader passes p2campaign::hasStaticHost)
// so this header never includes engine policy. Preserves valid/error; an
// empty result stays valid so the rest of the table is unaffected.
inline Table withoutStaticSources(const Table& table, bool (*isStatic)(unsigned)) {
    if (!table.valid || isStatic == nullptr) return table;
    Table out;
    out.valid = true;
    for (std::vector<Row>::size_type i = 0; i < table.rows.size(); ++i)
        if (!isStatic(table.rows[i].source)) out.rows.push_back(table.rows[i]);
    return out;
}
}  // namespace p2proxy
