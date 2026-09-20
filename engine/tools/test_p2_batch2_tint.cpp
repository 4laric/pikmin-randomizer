// Standalone probe for the batch-2 per-species material tint (#207).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_batch2_tint.cpp -o p2_batch2_tint.exe
//
// The batch-2 converter bakes every dweevil species from the shared-base model
// (FireOtakara) and drops the retail per-species `change_texture`, so all four
// Otakara .mod banks are byte-identical. The draw path multiplies a per-species
// tint over the shared material list at draw time. This probe pins the species
// -> tint selection: expected RGB literals are the mean opaque texel of each
// retail change_texture .bti (see output/reduced/rd-p2-material-tint/colour.md),
// hard-coded here so an accidental table edit fails the test.
#include "../pc_port/pc_p2_batch2.h"

#include <cstdio>
#include <string>

namespace {

int failures = 0;

bool check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
    return ok;
}

bool checkTint(const char* species, unsigned char r, unsigned char g, unsigned char b) {
    p2batch2tint::Tint tint{0, 0, 0};
    char what[128];
    std::snprintf(what, sizeof(what), "species %s selected", species);
    if (!check(p2batch2tint::tintForSpecies(species, tint), what)) return false;
    std::snprintf(what, sizeof(what), "species %s rgb %u,%u,%u", species, tint.r, tint.g, tint.b);
    return check(tint.r == r && tint.g == g && tint.b == b, what);
}

void testFourOtakara() {
    // Retail change_texture means: Fire=otakara_red, Water=otakara_blue,
    // Gas=otakara_purple, Elec=otakara_yellow (dweevils.json change_texture).
    checkTint("FireOtakara", 206, 72, 69);
    checkTint("WaterOtakara", 74, 118, 201);
    checkTint("GasOtakara", 189, 67, 209);
    checkTint("ElecOtakara", 201, 187, 75);
}

void testTintsAreDistinctHues() {
    p2batch2tint::Tint fire{0, 0, 0}, water{0, 0, 0}, gas{0, 0, 0}, elec{0, 0, 0};
    check(p2batch2tint::tintForSpecies("FireOtakara", fire), "fire tint");
    check(p2batch2tint::tintForSpecies("WaterOtakara", water), "water tint");
    check(p2batch2tint::tintForSpecies("GasOtakara", gas), "gas tint");
    check(p2batch2tint::tintForSpecies("ElecOtakara", elec), "elec tint");
    // Each species' dominant channel differs, so no two dweevils render alike:
    // Fire is red-dominant, Water blue-dominant, Gas red+blue (purple), Elec red+green (yellow).
    check(fire.r > fire.g && fire.r > fire.b, "fire red-dominant");
    check(water.b > water.r && water.b > water.g, "water blue-dominant");
    check(gas.r > gas.g && gas.b > gas.g, "gas purple (red+blue over green)");
    check(elec.r > elec.b && elec.g > elec.b, "elec yellow (red+green over blue)");
}

void testKeyRouting() {
    p2batch2tint::Tint tint{0, 0, 0};
    check(p2batch2tint::tintForKey("dweevil|FireOtakara", tint) && tint.r == 206, "key dweevil|FireOtakara");
    check(p2batch2tint::tintForKey("dweevil|WaterOtakara", tint) && tint.b == 201, "key dweevil|WaterOtakara");
    check(p2batch2tint::tintForKey("dweevil|GasOtakara", tint) && tint.b == 209, "key dweevil|GasOtakara");
    check(p2batch2tint::tintForKey("dweevil|ElecOtakara", tint) && tint.g == 187, "key dweevil|ElecOtakara");
    // Non-Otakara keys leave materials untouched: single-species banks
    // (Sokkuri), the neutral Bomb body, other families and malformed keys.
    check(!p2batch2tint::tintForKey("ground|Sokkuri", tint), "no tint ground|Sokkuri");
    check(!p2batch2tint::tintForKey("dweevil|BombOtakara", tint), "no tint dweevil|BombOtakara");
    check(!p2batch2tint::tintForKey("flora|Hana", tint), "no tint flora|Hana");
    check(!p2batch2tint::tintForKey("cannon|Kabuto", tint), "no tint cannon|Kabuto");
    check(!p2batch2tint::tintForKey("waterwraith|Tyre", tint), "no tint waterwraith|Tyre");
    check(!p2batch2tint::tintForKey("FireOtakara", tint), "no tint missing family");
    check(!p2batch2tint::tintForKey("", tint), "no tint empty key");
    check(!p2batch2tint::tintForKey("dweevil|Unknown", tint), "no tint unknown species");
    p2batch2tint::Tint untouched{7, 7, 7};
    tint = untouched;
    check(!p2batch2tint::tintForSpecies("BombOtakara", tint), "unknown species rejected");
    check(tint.r == 7 && tint.g == 7 && tint.b == 7, "rejected lookup leaves output untouched");
}

}  // namespace

int main() {
    testFourOtakara();
    testTintsAreDistinctHues();
    testKeyRouting();
    if (failures == 0) {
        std::printf("PASS p2_batch2_tint\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_batch2_tint: %d failures\n", failures);
    return 1;
}
