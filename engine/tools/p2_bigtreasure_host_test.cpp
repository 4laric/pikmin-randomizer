// Standalone engine-free fixture for the BigTreasure host seam glue
// (pc_port/pc_p2_bigtreasure_host.h/.cpp), issue #246. Exercises profile
// parse validation, install lifetime (5 captured pellets + elec discharge
// invariant), fixed-placement attack entry and the deterministic defeat
// teardown ordering. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_host_test.cpp pc_port/pc_p2_bigtreasure_host.cpp pc_port/pc_p2_bigtreasure.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o <private-output>/p2_bigtreasure_host_test.exe

#include "pc_p2_bigtreasure_host.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <fstream>

namespace {
constexpr float kDt = 1.0f / 30.0f;

void writeProfile(const char* path, const char* body)
{
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    out << body;
}

const char* kProfilePath = "p2_bigtreasure_host_test_profile.txt";

void testParseValid()
{
    writeProfile(kProfilePath,
                 "P2_BIGTREASURE_HOST_1\n"
                 "placement 0 0 0 1.5\n"
                 "target 0 0 200\n"
                 "timer 1.25\n"
                 "discharge 12\n");
    P2BigTreasureHostPlacement placement;
    assert(p2_bigtreasure_host_parse(kProfilePath, placement));
    assert(placement.owner.x == 0.0f && placement.ownerYaw == 1.5f);
    assert(placement.target.z == 200.0f);
    assert(placement.initialTimer == 1.25f);
    assert(placement.maxDischarge == 12);
    std::puts("PASS parse_valid");
}

void testParseRejected()
{
    P2BigTreasureHostPlacement placement;
    assert(!p2_bigtreasure_host_parse(nullptr, placement));
    assert(!p2_bigtreasure_host_parse("", placement));
    assert(!p2_bigtreasure_host_parse("p2_bigtreasure_host_missing.txt", placement));

    writeProfile(kProfilePath, "P2_GROINK_ARENA_1\nplacement 0 0 0 0\ntarget 0 0 1\ntimer 0\ndischarge 1\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // wrong magic

    writeProfile(kProfilePath, "P2_BIGTREASURE_HOST_1\nplacement 0 0 0 0 9\ntarget 0 0 1\ntimer 0\ndischarge 1\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // trailing field

    writeProfile(kProfilePath, "P2_BIGTREASURE_HOST_1\nplacement 0 nan 0 0\ntarget 0 0 1\ntimer 0\ndischarge 1\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // NaN coordinate

    writeProfile(kProfilePath, "P2_BIGTREASURE_HOST_1\nplacement 0 0 0 0\ntarget 0 0 100001\ntimer 0\ndischarge 1\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // out of range

    writeProfile(kProfilePath, "P2_BIGTREASURE_HOST_1\nplacement 0 0 0 0\ntarget 0 0 1\ntimer 2.5\ndischarge 1\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // timer above randWeightFloat(2)

    writeProfile(kProfilePath, "P2_BIGTREASURE_HOST_1\nplacement 0 0 0 0\ntarget 0 0 1\ntimer 0\ndischarge 17\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // breaks 1+max<=17 invariant

    writeProfile(kProfilePath, "P2_BIGTREASURE_HOST_1\nplacement 0 0 0 0\ntarget 0 0 1\ntimer 0\n");
    assert(!p2_bigtreasure_host_parse(kProfilePath, placement)); // truncated
    std::puts("PASS parse_rejected");
}

void testSetupInstallsLoadout()
{
    writeProfile(kProfilePath,
                 "P2_BIGTREASURE_HOST_1\n"
                 "placement 10 0 -20 0.0\n"
                 "target 10 0 180\n"
                 "timer 0.5\n"
                 "discharge 16\n");
    P2BigTreasureHostSeam seam;
    assert(p2_bigtreasure_host_setup(kProfilePath, seam));
    assert(seam.active);
    assert(seam.ownership.weaponCount() == 4);
    assert(seam.ownership.louieAttached());
    for (int weapon = 0; weapon < P2BTWEAPON_Count; ++weapon) {
        assert(seam.ownership.weaponHealth(weapon) == P2BigTreasureOwnership::kWeaponMaxHealth);
    }
    assert(seam.director.pools.capacity(P2BTWEAPON_Elec) == 17);
    assert(seam.placement.owner.x == 10.0f && seam.placement.owner.z == -20.0f);

    // Reinstall tears the previous loadout down first (no leaked captures).
    assert(p2_bigtreasure_host_setup(kProfilePath, seam));
    assert(seam.active && seam.ownership.weaponCount() == 4);
    assert(seam.ticks == 0 && seam.attacksStarted == 0);
    std::puts("PASS setup_loadout");
}

void testSetupRejectsBadProfile()
{
    P2BigTreasureHostSeam seam;
    writeProfile(kProfilePath, "junk\n");
    assert(!p2_bigtreasure_host_setup(kProfilePath, seam));
    assert(!seam.active);
    assert(seam.ownership.weaponCount() == 0 && !seam.ownership.louieAttached());
    std::puts("PASS setup_rejected");
}

void testTickEntryFixedPlacement()
{
    writeProfile(kProfilePath,
                 "P2_BIGTREASURE_HOST_1\n"
                 "placement 0 0 0 0\n"
                 "target 100 0 100\n" // inside the 225-unit XZ box
                 "timer 0\n"
                 "discharge 8\n");
    P2BigTreasureHostSeam seam;
    assert(p2_bigtreasure_host_setup(kProfilePath, seam));

    // Inactive seam rejects ticks.
    P2BigTreasureHostSeam inactive;
    assert(p2_bigtreasure_host_tick_entry(inactive, kDt, false, 0.5f) == -1);
    assert(p2_bigtreasure_host_tick_entry(seam, 0.0f, false, 0.5f) == -1); // bad delta

    // Threshold 4 + 2*4 = 12 s, strict: no attack at or below the boundary.
    int started = -1;
    for (int i = 0; i < 12 * 30 && started < 0; ++i) {
        started = p2_bigtreasure_host_tick_entry(seam, kDt, false, 0.0f);
    }
    assert(started == -1);
    started = p2_bigtreasure_host_tick_entry(seam, kDt, false, 0.0f);
    assert(started == P2BTWEAPON_Elec); // threshold 0 picks the first band
    assert(seam.attacksStarted == 1);
    // One attack at a time: while started, no second controller begins.
    assert(p2_bigtreasure_host_tick_entry(seam, kDt, false, 0.0f) == -1);

    // Target outside the box never allows an attack.
    writeProfile(kProfilePath,
                 "P2_BIGTREASURE_HOST_1\n"
                 "placement 0 0 0 0\n"
                 "target 0 0 500\n"
                 "timer 0\n"
                 "discharge 8\n");
    P2BigTreasureHostSeam farSeam;
    assert(p2_bigtreasure_host_setup(kProfilePath, farSeam));
    for (int i = 0; i < 20 * 30; ++i) {
        assert(p2_bigtreasure_host_tick_entry(farSeam, kDt, false, 0.0f) == -1);
    }
    std::puts("PASS tick_entry");
}

void testDefeatOrderingAndLifetime()
{
    writeProfile(kProfilePath,
                 "P2_BIGTREASURE_HOST_1\n"
                 "placement 0 0 0 0\n"
                 "target 0 0 100\n"
                 "timer 0\n"
                 "discharge 4\n");
    P2BigTreasureHostSeam seam;
    assert(p2_bigtreasure_host_setup(kProfilePath, seam));

    // Start an attack and put nodes in flight so pool teardown is observable.
    int started = -1;
    for (int i = 0; i < 13 * 30 && started < 0; ++i) {
        started = p2_bigtreasure_host_tick_entry(seam, kDt, false, 0.0f);
    }
    assert(started >= 0);
    assert(seam.director.pools.isStarted(started));
    assert(seam.director.pools.emit(started));
    assert(seam.director.pools.inFlight(started) == 1);

    P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1] = {};
    const std::size_t events = p2_bigtreasure_host_defeat(seam, drops, P2BTWEAPON_Count + 1);
    // 4 weapon pellets + Louie released, in capture order with Louie last.
    assert(events == 5);
    int weaponMask = 0;
    for (std::size_t i = 0; i < 4; ++i) {
        assert(!drops[i].isLouie && drops[i].weapon >= 0 && drops[i].weapon < P2BTWEAPON_Count);
        assert(drops[i].velocity.y == P2BigTreasureOwnership::kKnockOffPopY);
        weaponMask |= 1 << drops[i].weapon;
    }
    assert(weaponMask == 0xF);
    assert(drops[4].isLouie && drops[4].weapon == -1);
    assert(drops[4].velocity.y == P2BigTreasureOwnership::kLouiePopY);

    // Pools drained, captures cleared, seam inactive, repeat defeat is 0.
    for (int element = 0; element < P2BTWEAPON_Count; ++element) {
        assert(seam.director.pools.inFlight(element) == 0);
        assert(!seam.director.pools.isStarted(element));
    }
    assert(seam.ownership.weaponCount() == 0 && !seam.ownership.louieAttached());
    assert(!seam.active);
    assert(p2_bigtreasure_host_defeat(seam, drops, P2BTWEAPON_Count + 1) == 0);

    // Truncated output buffer caps writes but the release is total.
    assert(p2_bigtreasure_host_setup(kProfilePath, seam));
    const std::size_t partial = p2_bigtreasure_host_defeat(seam, drops, 2);
    assert(partial == 5);
    assert(seam.ownership.weaponCount() == 0 && !seam.ownership.louieAttached());

    // Reset on an active seam performs the same teardown without leaks.
    assert(p2_bigtreasure_host_setup(kProfilePath, seam));
    p2_bigtreasure_host_reset(seam);
    assert(!seam.active && seam.ownership.weaponCount() == 0);
    assert(seam.ticks == 0 && seam.attacksStarted == 0);
    p2_bigtreasure_host_reset(seam); // safe no-op
    std::puts("PASS defeat_lifetime");
}
} // namespace

int main()
{
    testParseValid();
    testParseRejected();
    testSetupInstallsLoadout();
    testSetupRejectsBadProfile();
    testTickEntryFixedPlacement();
    testDefeatOrderingAndLifetime();
    std::remove(kProfilePath);
    std::puts("PASS BIGTREASURE_HOST");
    return 0;
}
