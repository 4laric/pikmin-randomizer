// Lane 11 cave-checkpoint wire gate (#131/#112).
//
// Pins the exact encode/decode the engine uses in pc_lane/pc_p2_cave.cpp:
// schema-3 (Bulbmin) round trip, old-reader rejection of a newer species,
// unknown-version rejection, token/floor/health/trailing validation, and the
// transfer schema bump. Engine-free; follows tools/test_p2_species_schema.cpp.
#include "pc_p2_cave_transfer.h"

#include <cassert>
#include <cstdio>
#include <string>

namespace {
std::string token() { return std::string(32, 'a'); }

std::string entryText(const std::string& version, const std::vector<P2CaveSurvivor>& squad,
                      const std::string& tok, int floor, float health) {
    std::string text = version + "\n" + tok + "\n" + std::to_string(floor) + " "
        + std::to_string(health) + " " + std::to_string(squad.size()) + "\n";
    for (const auto& s : squad) text += std::to_string(s.species) + " " + std::to_string(s.maturity) + "\n";
    return text;
}
}  // namespace

int main() {
    const std::string tok = token();
    // v1 already carried Purple; v2 adds White; v3 adds Bulbmin.
    const std::vector<P2CaveSurvivor> base = {{0, 0}, {1, 1}, {3, 2}};
    const std::vector<P2CaveSurvivor> withWhite = {{0, 0}, {4, 2}};
    const std::vector<P2CaveSurvivor> withBulbmin = {{0, 0}, {1, 2}, {4, 1}, {5, 0}};

    P2CaveEntry out;
    std::string error;

    // 1. v1 parses and preserves species/maturity.
    assert(p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_1", base, tok, 1, 0.625f), out, error));
    assert(out.schema == P2SpeciesSchemaPurple && out.floor == 1 && out.squad.size() == 3);
    assert(out.squad[2].species == 3 && out.squad[1].maturity == 1);
    assert(out.token == tok);

    // 2. v2 parses White.
    assert(p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_2", withWhite, tok, 2, 1.0f), out, error));
    assert(out.schema == P2SpeciesSchemaWhite && out.squad[1].species == 4);

    // 3. v3 parses Bulbmin.
    assert(p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_3", withBulbmin, tok, 1, 0.5f), out, error));
    assert(out.schema == P2SpeciesSchemaBulbmin && out.squad[3].species == 5);

    // 4. Old readers reject a newer species explicitly ("Pikmin", not "header").
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_2", withBulbmin, tok, 1, 0.5f), out, error));
    assert(error == "Pikmin");
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_1", withWhite, tok, 1, 0.5f), out, error));
    assert(error == "Pikmin");

    // 5. Unknown version / bad token / bad floor / bad health / bad maturity.
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_4", base, tok, 1, 0.5f), out, error));
    assert(error == "header");
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_1", base, std::string(32, 'g'), 1, 0.5f), out, error));
    assert(error == "header");
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_1", base, tok, 3, 0.5f), out, error));
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_1", base, tok, 1, 1.5f), out, error));
    assert(!p2_cave_parse_entry(entryText("P2_CAVE_ENTRY_3", {{0, 3}}, tok, 1, 0.5f), out, error));
    assert(error == "Pikmin");

    // 6. Trailing data is rejected.
    std::string trailing = entryText("P2_CAVE_ENTRY_1", base, tok, 1, 0.5f);
    trailing += "0 0\n";
    assert(!p2_cave_parse_entry(trailing, out, error) && error == "trailing data");

    // 7. Transfer schema is bumped to the newest species and never downgraded.
    assert(p2_cave_transfer_schema(P2SpeciesSchemaPurple, base) == 1);
    assert(p2_cave_transfer_schema(P2SpeciesSchemaPurple, withWhite) == 2);
    assert(p2_cave_transfer_schema(P2SpeciesSchemaWhite, withBulbmin) == 3);
    assert(p2_cave_transfer_schema(P2SpeciesSchemaBulbmin, base) == 3);

    // 8. Write -> read round trip preserves the schema and every survivor.
    P2CaveEntry written;
    written.schema = P2SpeciesSchemaPurple;
    written.token = tok;
    written.floor = 1;
    written.health = 0.625f;
    written.squad = withBulbmin;
    const std::string transfer = p2_cave_format_transfer(written);
    assert(transfer.rfind("P2_CAVE_TRANSFER_3\n", 0) == 0);
    P2CaveEntry reread;
    assert(p2_cave_parse_transfer(transfer, reread, error));
    assert(reread.schema == P2SpeciesSchemaBulbmin && reread.squad.size() == withBulbmin.size());
    for (size_t i = 0; i < withBulbmin.size(); ++i) {
        assert(reread.squad[i].species == withBulbmin[i].species);
        assert(reread.squad[i].maturity == withBulbmin[i].maturity);
    }

    std::puts("PASS P2_CAVE_TRANSFER");
    return 0;
}
