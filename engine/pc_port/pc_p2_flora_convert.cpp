// Native M1/M2 conversion + scenery execution with observed markers (#697).
//
// Compiled into the guarded fixture via include (same accepted pattern as
// the integrated boot fixtures): no CMake target exists for this module yet,
// and registering one needs #186 review. The header stays engine-free; this
// TU only adds <cstdio> marker emission around the policy calls.
#include <cstdio>

#include "pc_p2_flora_convert.h"

namespace {

const char *speciesName(p2flora::Species species)
{
    switch (species) {
    case p2flora::Pelplant: return "Pelplant";
    case p2flora::BluePom: return "BluePom";
    case p2flora::RedPom: return "RedPom";
    case p2flora::YellowPom: return "YellowPom";
    case p2flora::BlackPom: return "BlackPom";
    case p2flora::WhitePom: return "WhitePom";
    case p2flora::RandPom: return "RandPom";
    default: return "Unknown";
    }
}

int checkConvert(p2flora::Species species, int swallowed, bool ownColour,
                 bool wantOk, int wantSprouts, int wantSlots, bool wantRefund)
{
    p2flora::ConvertResult got = p2flora::convertSwallow(
        {species, swallowed, ownColour});
    const bool pass = got.ok == wantOk && got.sprouts == wantSprouts
        && got.slotsUsed == wantSlots && got.refund == wantRefund;
    std::printf("P2_FLORA_CONVERT species=%s swallowed=%d own=%d ok=%d "
                "sprouts=%d slots=%d refund=%d pass=%d\n",
                speciesName(species), swallowed, int(ownColour), int(got.ok),
                got.sprouts, got.slotsUsed, int(got.refund), int(pass));
    return pass ? 0 : 1;
}

} // namespace

// M1 suite: Pelplant sizes, every bud, queen multiplier, own-colour refund,
// over-budget and unknown-species rejection. Returns failure count.
int p2_flora_convert_suite()
{
    int failures = 0;
    failures += checkConvert(p2flora::Pelplant, 1, false, true, 1, 0, false);
    failures += checkConvert(p2flora::Pelplant, 5, false, true, 5, 0, false);
    failures += checkConvert(p2flora::Pelplant, 10, false, true, 10, 0, false);
    failures += checkConvert(p2flora::Pelplant, 20, false, true, 20, 0, false);
    failures += checkConvert(p2flora::Pelplant, 7, false, false, 0, 0, false);
    const p2flora::Species buds[] = {
        p2flora::BluePom, p2flora::RedPom, p2flora::YellowPom,
        p2flora::BlackPom, p2flora::WhitePom,
    };
    for (unsigned i = 0; i < sizeof(buds) / sizeof(buds[0]); ++i) {
        failures += checkConvert(buds[i], 3, false, true, 3, 3, false);
        failures += checkConvert(buds[i], 2, true, true, 2, 2, true);
        failures += checkConvert(buds[i], 6, false, false, 0, 0, false);
    }
    failures += checkConvert(p2flora::RandPom, 1, false, true, 9, 0, false);
    failures += checkConvert(p2flora::RandPom, 1, true, true, 9, 0, false);
    failures += checkConvert(p2flora::RandPom, 2, false, false, 0, 0, false);
    failures += checkConvert(p2flora::SpeciesCount, 1, false, false, 0, 0, false);
    failures += checkConvert(p2flora::BluePom, -1, false, false, 0, 0, false);
    p2flora::Converter limited(p2flora::RedPom);
    p2flora::ConvertResult first = limited.shot(3, false);
    p2flora::ConvertResult second = limited.shot(3, false);
    const bool budget = first.ok && !second.ok && limited.shotsLeftForTest() == 2;
    std::printf("P2_FLORA_CONVERT budget first=%d second_ok=%d left=%d pass=%d\n",
                int(first.ok), int(second.ok), limited.shotsLeftForTest(),
                int(budget));
    failures += budget ? 0 : 1;
    p2flora::Converter refund(p2flora::YellowPom);
    p2flora::ConvertResult paid = refund.shot(2, true);
    const bool refunded = paid.ok && paid.refund
        && refund.shotsLeftForTest() == 4;
    std::printf("P2_FLORA_CONVERT refund ok=%d left=%d pass=%d\n",
                int(paid.ok), refund.shotsLeftForTest(), int(refunded));
    failures += refunded ? 0 : 1;
    std::printf("P2_FLORA_CONVERT_DONE failures=%d\n", failures);
    std::fflush(stdout);
    return failures;
}

// M2 suite: prop registration, lookup, duplicate/slot/full/unknown
// rejection. Returns failure count.
int p2_flora_scenery_suite()
{
    int failures = 0;
    p2flora::SceneryRegistry registry;
    const char *props[] = {"Clover", "Tanpopo", "HikariKinoko", "Ooinu_s",
                           "Ooinu_l", "Wakame_s", "Wakame_l", "Pelplant"};
    for (int i = 0; i < 8; ++i) {
        const int slot = registry.registerProp(props[i], i);
        const bool pass = slot == i && registry.findProp(props[i]) == i;
        std::printf("P2_FLORA_SCENERY register identity=%s slot=%d pass=%d\n",
                    props[i], slot, int(pass));
        failures += pass ? 0 : 1;
    }
    const bool dupIdentity = registry.registerProp("Clover", 7) < 0;
    const bool dupSlot = registry.registerProp("Extra", 0) < 0;
    const bool full = registry.registerProp("Ninth", 8) < 0;
    const bool unknown = registry.findProp("Missing") < 0
        && registry.registerProp(nullptr, 0) < 0
        && registry.registerProp("", 0) < 0
        && registry.registerProp("Extra", -1) < 0;
    std::printf("P2_FLORA_SCENERY rejects dup_identity=%d dup_slot=%d "
                "full=%d unknown=%d\n",
                int(dupIdentity), int(dupSlot), int(full), int(unknown));
    failures += (dupIdentity && dupSlot && full && unknown) ? 0 : 1;
    std::printf("P2_FLORA_SCENERY_DONE failures=%d count=%d\n", failures,
                registry.count());
    std::fflush(stdout);
    return failures;
}
