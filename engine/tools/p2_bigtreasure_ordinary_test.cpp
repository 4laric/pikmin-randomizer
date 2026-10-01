// Standalone engine-free fixture for the BigTreasure ordinary-update drive
// (pc_port/pc_p2_bigtreasure_ordinary.h/.cpp), issue #246. Proves that the
// 12-state policy is stepped from the ordinary update with an
// isAttackLimitTime() input derived from the lane's attack pacer, that a
// natural hit posted through the lane ingress drives the knock-off phase
// transition, and that the hit queue is bounded and fail-closed. Build
// (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_ordinary_test.cpp pc_port/pc_p2_bigtreasure_ordinary.cpp pc_port/pc_p2_bigtreasure_fsmhost.cpp pc_port/pc_p2_bigtreasure_host.cpp pc_port/pc_p2_bigtreasure_fsm.cpp pc_port/pc_p2_bigtreasure.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o <private-output>/p2_bigtreasure_ordinary_test.exe

#include "pc_p2_bigtreasure_ordinary.h"

#include <cassert>
#include <cstdio>
#include <fstream>
#include <limits>

namespace {
const char* kProfilePath = "p2_bigtreasure_ordinary_test_profile.txt";

void writeProfile(const char* body)
{
    std::ofstream out(kProfilePath, std::ios::binary | std::ios::trunc);
    out << body;
}

struct Rig {
    P2BigTreasureHostSeam seam;
    P2BigTreasureOrdinary ord;
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
        ord.reset(parms);
    }

    void tick(const P2BigTreasureOrdinaryFacts& facts) { ord.tick(seam, facts, out); }
};

P2BigTreasureOrdinaryFacts facts(bool targetInBox, bool finishIK)
{
    P2BigTreasureOrdinaryFacts f;
    f.hasTarget = true;
    f.targetInBox = targetInBox;
    f.finishIKMotion = finishIK;
    return f;
}

// Stays -> Land -> ItemWalk, then waits on the pacer-derived attack gate
// (4 + 2 * liveWeapons seconds of in-box time) to reach PreAttack -> Attack and
// start the first (elec) pool.
void advanceToAttack(Rig& rig)
{
    P2BigTreasureOrdinaryFacts f;
    f.hasTarget = true;
    int guard = 0;
    while (rig.ord.phase() != P2BT_Land && guard++ < 400) {
        rig.tick(f);
    }
    assert(rig.ord.phase() == P2BT_Land);

    f = P2BigTreasureOrdinaryFacts{};
    f.hasTarget = true;
    f.animEnd = true;
    rig.tick(f);
    assert(rig.ord.phase() == P2BT_ItemWalk);

    f = facts(/*targetInBox=*/true, /*finishIK=*/true);
    guard = 0;
    while (rig.ord.phase() != P2BT_PreAttack && guard++ < 2000) {
        rig.tick(f);
    }
    assert(rig.ord.phase() == P2BT_PreAttack);
    assert(rig.ord.chosenWeapon() == P2BTWEAPON_Elec); // threshold 0 picks elec

    f = P2BigTreasureOrdinaryFacts{};
    f.animEnd = true;
    rig.tick(f);
    assert(rig.ord.phase() == P2BT_Attack);

    f = P2BigTreasureOrdinaryFacts{};
    f.keyEvent2 = true;
    rig.tick(f);
    assert(rig.out.fsm.startAttack);
    assert(rig.seam.director.pools.isStarted(P2BTWEAPON_Elec));
    assert(rig.seam.attacksStarted == 1);
}

void testPacerDrivenAttack()
{
    Rig rig;
    advanceToAttack(rig);
    std::puts("PASS ordinary_pacer_attack");
}

void testNaturalHitKnockoff()
{
    Rig rig;
    advanceToAttack(rig);

    assert(rig.ord.postHit({P2BTWEAPON_Elec, P2BigTreasureOwnership::kWeaponMaxHealth, false}));
    P2BigTreasureOrdinaryFacts f;
    rig.tick(f);

    assert(rig.out.damageResult == P2BTDMG_Weapon);
    assert(rig.out.knockedOff == 1);
    assert(rig.seam.ownership.weaponCount() == 3);
    assert(!rig.seam.ownership.isWeaponAttached(P2BTWEAPON_Elec));
    // Same-tick re-pick from the remaining band (fire next).
    assert(rig.ord.phase() == P2BT_PreAttack);
    assert(rig.ord.chosenWeapon() == P2BTWEAPON_Fire);
    std::puts("PASS ordinary_natural_knockoff");
}

void testHitQueueBoundsAndValidation()
{
    Rig rig;
    const float nan = std::numeric_limits<float>::quiet_NaN();
    assert(!rig.ord.postHit({0, 0.0f, false}));
    assert(!rig.ord.postHit({0, -5.0f, false}));
    assert(!rig.ord.postHit({0, nan, false}));
    assert(!rig.ord.postHit({-2, 10.0f, false}));
    assert(!rig.ord.postHit({P2BTWEAPON_Count, 10.0f, false}));

    for (int i = 0; i < P2BigTreasureOrdinary::kHitQueueCapacity; ++i) {
        assert(rig.ord.postHit({P2BTWEAPON_Elec, 1.0f, false}));
    }
    assert(rig.ord.pendingHits() == P2BigTreasureOrdinary::kHitQueueCapacity);
    assert(!rig.ord.postHit({P2BTWEAPON_Elec, 1.0f, false})); // full: dropped

    P2BigTreasureOrdinaryFacts f;
    P2BigTreasureFsmHostOutput out;
    rig.ord.tick(rig.seam, f, out);
    assert(rig.ord.pendingHits() == P2BigTreasureOrdinary::kHitQueueCapacity - 1);
    std::puts("PASS ordinary_hit_queue");
}

void testBodyExposureAndKill()
{
    Rig rig;
    advanceToAttack(rig);

    P2BigTreasureOrdinaryFacts f;
    for (int weapon = 0; weapon < P2BTWEAPON_Count; ++weapon) {
        assert(rig.ord.postHit({weapon, P2BigTreasureOwnership::kWeaponMaxHealth, false}));
        rig.tick(f);
        assert(rig.out.damageResult == P2BTDMG_Weapon);
    }
    assert(rig.seam.ownership.weaponCount() == 0);
    assert(rig.seam.ownership.isBodyExposed());

    assert(rig.ord.postHit({-1, 250.0f, false}));
    rig.tick(f);
    assert(rig.out.damageResult == P2BTDMG_Body);
    assert(rig.out.liveWeapons == 0);

    f.killed = true;
    rig.tick(f);
    assert(rig.ord.phase() == P2BT_Dead);
    std::puts("PASS ordinary_body_and_kill");
}

void testInactiveSeamNoOp()
{
    P2BigTreasureHostSeam seam;
    P2BigTreasureOrdinary ord;
    P2BigTreasureFsmParms parms;
    ord.reset(parms);
    P2BigTreasureOrdinaryFacts f;
    P2BigTreasureFsmHostOutput out;
    assert(ord.postHit({0, 100.0f, false}));
    ord.tick(seam, f, out);
    assert(out.damageResult == P2BTDMG_Ignored);
    assert(out.knockedOff == 0);
    assert(ord.phase() == P2BT_Stay);
    assert(ord.pendingHits() == 1); // seam inactive: hit not consumed
    std::puts("PASS ordinary_inactive");
}
} // namespace

int main()
{
    testPacerDrivenAttack();
    testNaturalHitKnockoff();
    testHitQueueBoundsAndValidation();
    testBodyExposureAndKill();
    testInactiveSeamNoOp();
    std::remove(kProfilePath);
    std::puts("PASS BIGTREASURE_ORDINARY");
    return 0;
}
