// Standalone engine-free fixture for the BigTreasure FSM host binding
// (pc_port/pc_p2_bigtreasure_fsmhost.h/.cpp), issue #246. Drives the real
// 12-state policy against the host seam and proves real weapon damage plus a
// natural phase transition (weapon knock-off changes the live loadout, the FSM
// re-picks, and the body only becomes damageable at zero weapons). Build
// (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_fsmhost_test.cpp pc_port/pc_p2_bigtreasure_fsmhost.cpp pc_port/pc_p2_bigtreasure_host.cpp pc_port/pc_p2_bigtreasure_fsm.cpp pc_port/pc_p2_bigtreasure.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o <private-output>/p2_bigtreasure_fsmhost_test.exe

#include "pc_p2_bigtreasure_fsmhost.h"

// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <cstdio>
#include <fstream>

namespace {
constexpr float kDt = 1.0f / 30.0f;
const char* kProfilePath = "p2_bigtreasure_fsmhost_test_profile.txt";

void writeProfile(const char* body)
{
    std::ofstream out(kProfilePath, std::ios::binary | std::ios::trunc);
    out << body;
}

struct Rig {
    P2BigTreasureHostSeam seam;
    P2BigTreasureFsmHost host;
    P2BigTreasureFsmHostOutput out;

    Rig()
    {
        writeProfile("P2_BIGTREASURE_HOST_1\n"
                     "placement 0 0 0 0\n"
                     "target 0 0 100\n"
                     "timer 0\n"
                     "discharge 8\n");
        assert(p2_bigtreasure_host_setup(kProfilePath, seam));
        P2BigTreasureFsmParms parms;
        host.reset(parms);
    }

    void tick(const P2BigTreasureFsmHostInput& in) { host.tick(seam, in, out); }
};

void advanceToAttack(Rig& rig)
{
    P2BigTreasureFsmHostInput in;
    in.hasTarget = true;
    int guard = 0;
    while (rig.host.phase() != P2BT_Land && guard++ < 400) {
        rig.tick(in);
    }
    assert(rig.host.phase() == P2BT_Land);

    in.animEnd = true;
    rig.tick(in);
    assert(rig.host.phase() == P2BT_ItemWalk);

    in = P2BigTreasureFsmHostInput{};
    in.hasTarget = true;
    in.attackLimitTime = true;
    rig.tick(in);
    assert(rig.host.phase() == P2BT_ItemWalk); // waiting for the IK finish gate

    in = P2BigTreasureFsmHostInput{};
    in.hasTarget = true;
    in.finishIKMotion = true;
    rig.tick(in);
    assert(rig.host.phase() == P2BT_PreAttack);
    assert(rig.host.chosenWeapon() == P2BTWEAPON_Elec); // threshold 0 picks elec band

    in = P2BigTreasureFsmHostInput{};
    in.animEnd = true;
    rig.tick(in);
    assert(rig.host.phase() == P2BT_Attack);

    in = P2BigTreasureFsmHostInput{};
    in.keyEvent2 = true;
    rig.tick(in);
    assert(rig.out.fsm.startAttack);
    assert(rig.seam.director.pools.isStarted(P2BTWEAPON_Elec));
    assert(rig.seam.attacksStarted == 1);
}

void testStateProgressionToAttack()
{
    Rig rig;
    advanceToAttack(rig);
    std::puts("PASS fsmhost_progression");
}

void testLandQuartersDamage()
{
    Rig rig;
    P2BigTreasureFsmHostInput in;
    in.hasTarget = true;
    int guard = 0;
    while (rig.host.phase() != P2BT_Land && guard++ < 400) {
        rig.tick(in);
    }
    assert(rig.host.phase() == P2BT_Land);

    in = P2BigTreasureFsmHostInput{};
    in.damage = 100.0f;
    in.damageWeapon = P2BTWEAPON_Elec;
    rig.tick(in);
    assert(rig.out.damageResult == P2BTDMG_Weapon);
    assert(std::fabs(rig.seam.ownership.weaponHealth(P2BTWEAPON_Elec) - 5975.0f) < 1e-3f);
    std::puts("PASS fsmhost_land_quarter");
}

void testKnockOffPhaseTransition()
{
    Rig rig;
    advanceToAttack(rig);

    // Real damage to the chosen elec weapon drains it to zero HP.
    P2BigTreasureFsmHostInput in;
    in.damage = P2BigTreasureOwnership::kWeaponMaxHealth;
    in.damageWeapon = P2BTWEAPON_Elec;
    rig.tick(in);

    assert(rig.out.damageResult == P2BTDMG_Weapon);
    assert(rig.out.knockedOff == 1);
    assert(rig.seam.ownership.weaponCount() == 3);
    assert(!rig.seam.ownership.isWeaponAttached(P2BTWEAPON_Elec));
    // The FSM observes the lost chosen weapon in the same tick and re-enters
    // PreAttack, re-picking from the remaining band (fire next).
    assert(rig.host.phase() == P2BT_PreAttack);
    assert(rig.host.chosenWeapon() == P2BTWEAPON_Fire);
    assert(rig.out.fsm.finishAttack); // Attack cleanup fired on the transition

    // A second hit that does not kill the next weapon is still routed.
    in = P2BigTreasureFsmHostInput{};
    in.damage = 1000.0f;
    in.damageWeapon = P2BTWEAPON_Fire;
    rig.tick(in);
    assert(rig.out.damageResult == P2BTDMG_Weapon);
    assert(std::fabs(rig.seam.ownership.weaponHealth(P2BTWEAPON_Fire) - 5000.0f) < 1e-3f);
    assert(rig.seam.ownership.weaponCount() == 3);
    std::puts("PASS fsmhost_knockoff_phase");
}

void testBodyDamageOnlyAtZeroWeapons()
{
    Rig rig;
    advanceToAttack(rig);

    // Armed body part (damageWeapon -1) is ignored while weapons remain.
    P2BigTreasureFsmHostInput in;
    in.damage = 500.0f;
    in.damageWeapon = -1;
    rig.tick(in);
    assert(rig.out.damageResult == P2BTDMG_Ignored);
    assert(rig.seam.ownership.weaponCount() == 4);

    // Drain every weapon; each knock-off is a phase transition.
    for (int weapon = 0; weapon < P2BTWEAPON_Count; ++weapon) {
        in = P2BigTreasureFsmHostInput{};
        in.damage = P2BigTreasureOwnership::kWeaponMaxHealth;
        in.damageWeapon = weapon;
        rig.tick(in);
        assert(rig.out.damageResult == P2BTDMG_Weapon);
        assert(rig.seam.ownership.weaponCount() == P2BTWEAPON_Count - 1 - weapon);
    }
    assert(rig.seam.ownership.isBodyExposed());
    assert(rig.host.phase() == P2BT_PreAttack || rig.host.phase() == P2BT_DropItem);

    // Body parts now route to boss HP.
    in = P2BigTreasureFsmHostInput{};
    in.damage = 250.0f;
    in.damageWeapon = -1;
    rig.tick(in);
    assert(rig.out.damageResult == P2BTDMG_Body);
    assert(rig.out.bodyExposed);
    assert(rig.out.liveWeapons == 0);
    std::puts("PASS fsmhost_body_exposure");
}

void testPinchSmokeCrossing()
{
    Rig rig;
    advanceToAttack(rig);

    P2BigTreasureFsmHostInput in;
    in.damage = 3500.0f; // 6000 -> 2500 crosses the strict 3000 boundary
    in.damageWeapon = P2BTWEAPON_Elec;
    rig.tick(in);
    assert(rig.out.damageResult == P2BTDMG_Weapon);
    assert(rig.out.pinchSmoke);
    assert(!rig.seam.ownership.isNormalAttack(P2BTWEAPON_Elec));
    std::puts("PASS fsmhost_pinch_smoke");
}

void testKillAndDeadKeys()
{
    Rig rig;
    advanceToAttack(rig);

    P2BigTreasureFsmHostInput in;
    in.killed = true;
    rig.tick(in);
    assert(rig.host.phase() == P2BT_Dead);

    in = P2BigTreasureFsmHostInput{};
    in.keyEvent100 = true;
    rig.tick(in);
    assert(rig.out.fsm.throwupItem);
    assert(rig.out.fsm.releaseLoozy);
    assert(!rig.seam.ownership.louieAttached());

    in = P2BigTreasureFsmHostInput{};
    in.animEnd = true;
    rig.tick(in);
    assert(rig.out.fsm.killRequested);
    std::puts("PASS fsmhost_kill_dead");
}

void testInactiveSeamNoOp()
{
    P2BigTreasureHostSeam seam;
    P2BigTreasureFsmHost host;
    P2BigTreasureFsmParms parms;
    host.reset(parms);
    P2BigTreasureFsmHostInput in;
    P2BigTreasureFsmHostOutput out;
    in.damage = 1000.0f;
    host.tick(seam, in, out);
    assert(out.damageResult == P2BTDMG_Ignored);
    assert(out.knockedOff == 0);
    assert(host.phase() == P2BT_Stay);
    std::puts("PASS fsmhost_inactive");
}

void testDefeatStillReleasesRest()
{
    Rig rig;
    advanceToAttack(rig);

    P2BigTreasureFsmHostInput in;
    in.damage = P2BigTreasureOwnership::kWeaponMaxHealth;
    in.damageWeapon = P2BTWEAPON_Elec;
    rig.tick(in);
    assert(rig.seam.ownership.weaponCount() == 3);

    P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1] = {};
    const std::size_t events = p2_bigtreasure_host_defeat(rig.seam, drops, P2BTWEAPON_Count + 1);
    assert(events == 4); // 3 remaining weapons + Louie
    int mask = 0;
    for (std::size_t i = 0; i < events; ++i) {
        if (!drops[i].isLouie) {
            assert(drops[i].weapon != P2BTWEAPON_Elec); // already knocked off
            mask |= 1 << drops[i].weapon;
        }
    }
    assert(mask == 0xE);
    assert(drops[events - 1].isLouie);
    std::puts("PASS fsmhost_defeat_rest");
}
} // namespace

int main()
{
    testStateProgressionToAttack();
    testLandQuartersDamage();
    testKnockOffPhaseTransition();
    testBodyDamageOnlyAtZeroWeapons();
    testPinchSmokeCrossing();
    testKillAndDeadKeys();
    testInactiveSeamNoOp();
    testDefeatStillReleasesRest();
    std::remove(kProfilePath);
    std::puts("PASS BIGTREASURE_FSMHOST");
    return 0;
}
