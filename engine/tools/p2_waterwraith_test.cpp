// Standalone engine-free fixture for the Waterwraith/Tyre dependent-roller
// ownership and vulnerability policy (pc_port/pc_p2_waterwraith.h/.cpp),
// lane 31 (#175 / #443). Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_waterwraith_test.cpp pc_port/pc_p2_waterwraith.cpp -o <private-output>/p2_waterwraith_test.exe

#include "pc_p2_waterwraith.h"

#include <cassert>
#include <cmath>
#include <cstdio>

namespace {

void testBirthAndLifetime()
{
    P2WaterwraithRig rig;
    assert(!rig.alive());
    assert(rig.birth());
    assert(rig.alive() && rig.attachedToOwner());
    assert(rig.tyrePhase() == P2TYRE_Land);
    assert(rig.tyreHealth() == P2WaterwraithRig::kTyreMaxHealth);
    assert(!rig.ownerInvulnerableSet());
    assert(!rig.birth()); // at most one child
    std::puts("PASS waterwraith_birth");
}

void testStateTransitions()
{
    P2WaterwraithRig rig;
    assert(rig.birth());

    assert(rig.landFloorContact()); // Land -> Freeze
    assert(rig.tyrePhase() == P2TYRE_Freeze);
    assert(!rig.landFloorContact()); // not in Land any more
    assert(rig.moveRestart());        // Freeze -> Move
    assert(rig.tyrePhase() == P2TYRE_Move);
    assert(!rig.moveRestart());       // not frozen
    assert(rig.quakeFreeze());        // Move -> Freeze
    assert(rig.tyrePhase() == P2TYRE_Freeze);
    assert(!rig.quakeFreeze());       // not moving
    std::puts("PASS waterwraith_states");
}

void testCollisionSticky()
{
    P2WaterwraithRig rig;
    assert(rig.birth());
    assert(!rig.collisionSticky()); // Land
    rig.landFloorContact();
    assert(rig.collisionSticky());  // Freeze
    rig.moveRestart();
    assert(!rig.collisionSticky()); // Move
    std::puts("PASS waterwraith_sticky");
}

void testVulnerabilityGate()
{
    P2WaterwraithRig rig;
    assert(rig.birth());
    assert(!rig.damageable());                       // Land: riding, not damageable
    bool dead = true;
    assert(!rig.applyDamage(100.0f, &dead));         // ignored
    assert(!dead && rig.tyreHealth() == P2WaterwraithRig::kTyreMaxHealth);

    rig.landFloorContact();
    assert(rig.damageable());                        // Freeze: stickable
    assert(rig.applyDamage(300.0f, &dead));
    assert(rig.tyreHealth() == P2WaterwraithRig::kTyreMaxHealth - 300.0f);

    // Zero HP without the dismounted flag does not kill (source death gate).
    assert(rig.applyDamage(P2WaterwraithRig::kTyreMaxHealth, &dead));
    assert(rig.tyreHealth() == 0.0f);
    assert(!dead);
    assert(!rig.beginDead());
    std::puts("PASS waterwraith_vulnerability");
}

void testDismountAndDeath()
{
    P2WaterwraithRig rig;
    assert(rig.birth());
    rig.landFloorContact();
    rig.moveRestart();
    assert(rig.tyrePhase() == P2TYRE_Move);

    rig.dismount();
    assert(!rig.attachedToOwner());
    assert(rig.ownerInvulnerableSet());
    assert(rig.tyrePhase() == P2TYRE_Freeze); // dismount freezes the roller
    assert(rig.damageable());

    bool dead = false;
    assert(rig.applyDamage(P2WaterwraithRig::kTyreMaxHealth, &dead));
    assert(dead); // zero HP + dismounted => death allowed
    assert(rig.beginDead());
    assert(rig.tyrePhase() == P2TYRE_Dead);
    assert(!rig.collisionSticky());
    assert(rig.finishDead());
    assert(!rig.alive() && !rig.attachedToOwner());
    assert(!rig.finishDead()); // already removed
    assert(!rig.damageable());
    std::puts("PASS waterwraith_death");
}

void testRollAngle()
{
    P2WaterwraithRig rig(1.0f); // fp01 = 1 for a 1:1 angle-to-distance check
    assert(rig.birth());
    rig.landFloorContact();
    rig.moveRestart();

    rig.push({ 0.0f, 0.0f, 0.0f }, { 0, 0, 0 }, 0.0f, 1.0f);
    rig.push({ P2WaterwraithRig::kRollerCircumference, 0.0f, 0.0f }, { 0, 0, 0 }, 0.0f, 1.0f);
    assert(std::fabs(rig.travelledDistance() - P2WaterwraithRig::kRollerCircumference) < 1e-2f);
    assert(std::fabs(rig.rollAngle() - 1.0f) < 1e-3f);

    // Frozen roller is a static collider: pushes no longer accumulate roll.
    rig.quakeFreeze();
    const float frozenDistance = rig.travelledDistance();
    rig.push({ P2WaterwraithRig::kRollerCircumference * 2.0f, 0.0f, 0.0f }, { 0, 0, 0 }, 0.0f, 1.0f);
    assert(rig.travelledDistance() == frozenDistance);
    std::puts("PASS waterwraith_roll");
}

void testRideRegen()
{
    P2WaterwraithRig rig;
    assert(rig.birth());
    assert(rig.rideRegen(true) == P2WaterwraithRig::kRideRegenPerTick);
    assert(rig.rideRegen(false) == 0.0f);
    rig.dismount();
    assert(rig.rideRegen(true) == 0.0f); // no regen once dismounted
    std::puts("PASS waterwraith_regen");
}

void testShadowRamp()
{
    P2WaterwraithRig rig;
    assert(rig.birth());
    assert(std::fabs(rig.tickShadow(1.0f / 30.0f) - P2WaterwraithRig::kShadowMinScale) < 1e-6f);
    rig.beginFall();
    float scale = P2WaterwraithRig::kShadowMinScale;
    for (int i = 0; i < 30; ++i) {
        scale = rig.tickShadow(1.0f / 30.0f);
    }
    assert(std::fabs(scale - P2WaterwraithRig::kShadowMaxScale) < 1e-4f);
    assert(rig.tickShadow(1.0f) == P2WaterwraithRig::kShadowMaxScale); // clamped
    std::puts("PASS waterwraith_shadow");
}
} // namespace

int main()
{
    testBirthAndLifetime();
    testStateTransitions();
    testCollisionSticky();
    testVulnerabilityGate();
    testDismountAndDeath();
    testRollAngle();
    testRideRegen();
    testShadowRamp();
    std::puts("PASS WATERWRAITH_POLICY");
    return 0;
}
