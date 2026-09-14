// Standalone engine-free fixture for the Waterwraith/Tyre actor phase machine
// (pc_port/pc_p2_waterwraith_actor.h/.cpp), lane 31 (#443 / parent #175).
// Drives the real policy against host-fed triggers and the real rig, covering
// phase transitions, host-driven route locomotion, the full roller cycle, the
// damage gate (Purple-only, frozen/dismounted only) and teardown. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_waterwraith_actor_test.cpp pc_port/pc_p2_waterwraith_actor.cpp pc_port/pc_p2_waterwraith.cpp -o output/p2_waterwraith_actor_test.exe

#include "pc_p2_waterwraith_actor.h"

#include <cassert>
#include <cmath>
#include <cstdio>

namespace {

constexpr float kDt = 1.0f / 30.0f;

P2WaterwraithActor makeActor(P2BlackManPhase start = P2BM_Walk)
{
    P2WaterwraithActorParms parms;
    parms.startPhase = start;
    return P2WaterwraithActor(parms);
}

void step(P2WaterwraithActor& actor, const P2WaterwraithActorInput& in,
          P2WaterwraithActorOutput* out = nullptr)
{
    P2WaterwraithActorOutput local;
    actor.tick(in, out ? *out : local, kDt);
}

void testResetAndLifetime()
{
    P2WaterwraithActor actor;
    assert(actor.alive());
    assert(actor.phase() == P2BM_Fall); // source onInit starts Fall off y_01
    assert(actor.rig().alive() && actor.rig().attachedToOwner());
    assert(actor.rig().tyrePhase() == P2TYRE_Land);
    assert(std::fabs(actor.bodyHealth() - actor.bodyMaxHealth()) < 1e-3f);
    assert(!actor.pinched() && !actor.zeroed());
    assert(P2WaterwraithActor::phaseName(P2BM_Walk) != nullptr);
    assert(actor.phaseName() != nullptr);
    assert(!actor.reachedRouteEnd());
    std::puts("PASS actor_lifetime");
}

void testFallRecoverWalk()
{
    P2WaterwraithActor actor = makeActor(P2BM_Fall);
    P2WaterwraithActorInput in;
    P2WaterwraithActorOutput out;
    in.isFallEnd = true;
    step(actor, in, &out);
    assert(actor.phase() == P2BM_Recover);
    assert(out.entered && out.endFallConstraint && out.startRecoverMotion);

    in                = P2WaterwraithActorInput{};
    in.animEnd        = true;
    step(actor, in, &out);
    assert(actor.phase() == P2BM_Walk);
    assert(out.moveRestartRequested);
    std::puts("PASS actor_fall_recover_walk");
}

void testBendAndRecover()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    P2WaterwraithActorInput in;
    P2WaterwraithActorOutput out;
    in.isTyreFreeze = true;
    step(actor, in, &out);
    assert(actor.phase() == P2BM_Bend);
    assert(out.collisionStOn && out.startBendMotion);

    in         = P2WaterwraithActorInput{};
    in.animEnd = true;
    step(actor, in, &out);
    assert(actor.phase() == P2BM_Recover); // roller alive: lift back up
    assert(out.collisionStOff);
    std::puts("PASS actor_bend_recover");
}

void testFlickReturnsToPostState()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    P2WaterwraithActorInput in;
    in.isStartFlick = true;
    step(actor, in);
    assert(actor.phase() == P2BM_Flick);

    in         = P2WaterwraithActorInput{};
    in.animEnd = true;
    step(actor, in);
    assert(actor.phase() == P2BM_Walk); // postFlickState was Walk
    std::puts("PASS actor_flick_poststate");
}

void testRollerlessFreezeStun()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    actor.rig().dismount(); // rollerless wraith
    P2WaterwraithActorInput in;
    in.rollerlessQuake = true;
    step(actor, in);
    assert(actor.phase() == P2BM_Freeze);

    in         = P2WaterwraithActorInput{};
    in.animEnd = true;
    step(actor, in);
    assert(actor.phase() == P2BM_Walk);
    std::puts("PASS actor_rollerless_freeze");
}

void testTiredWindDown()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    P2WaterwraithActorInput in;
    in.tired = true;
    step(actor, in);
    assert(actor.phase() == P2BM_Tired);

    in         = P2WaterwraithActorInput{};
    in.animEnd = true;
    step(actor, in);
    assert(actor.phase() == P2BM_Walk);
    std::puts("PASS actor_tired");
}

void testDeadReleasesTreasureThenKills()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    actor.rig().dismount();
    bool dead = false;
    assert(p2_waterwraith_actor_apply_damage(actor, actor.bodyMaxHealth(), true, &dead)
           == P2WWDMG_Body);
    assert(dead && actor.bodyZeroed());

    P2WaterwraithActorInput in;
    P2WaterwraithActorOutput out;
    step(actor, in, &out);
    assert(actor.phase() == P2BM_Dead);
    assert(out.startDeadMotion);

    in                   = P2WaterwraithActorInput{};
    in.keyEvent5         = true;
    step(actor, in, &out);
    assert(out.releaseTreasure);

    in                  = P2WaterwraithActorInput{};
    in.animEnd          = true;
    step(actor, in, &out);
    assert(out.killRequested && !actor.alive());

    // Dead actor ignores further input and damage.
    in            = P2WaterwraithActorInput{};
    in.animEnd    = true;
    step(actor, in, &out);
    assert(!out.killRequested);
    assert(p2_waterwraith_actor_apply_damage(actor, 100.0f, true, &dead) == P2WWDMG_Ignored);
    std::puts("PASS actor_dead");
}

void testRouteLocomotion()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    const P2WaterwraithWaypoint route[] = {
        P2WaterwraithWaypoint{ P2WaterwraithVec3{ 500.0f, 0.0f, 0.0f } },
        P2WaterwraithWaypoint{ P2WaterwraithVec3{ 500.0f, 0.0f, 200.0f } },
    };
    assert(actor.setRoute(route, 2) == 2);
    assert(!actor.reachedRouteEnd());
    assert(actor.nextWaypoint().x == 500.0f);

    P2WaterwraithActorInput in;
    for (int i = 0; i < 40; ++i) {
        step(actor, in);
    }
    // Facing turns toward +X (source forward = (sin, cos) => pi/2).
    assert(actor.facing() > 1.0f);
    assert(actor.position().x > 0.0f);
    assert(actor.waypointIndex() == 0); // goal radius 50 not yet reached

    int ticks = 0;
    while (!actor.reachedRouteEnd() && ticks < 1200) {
        step(actor, in);
        ++ticks;
    }
    assert(actor.reachedRouteEnd());
    assert(actor.waypointIndex() == 2);
    assert(actor.position().x > 400.0f);
    assert(actor.position().z > 100.0f);
    assert(actor.rig().travelledDistance() > 0.0f);

    actor.clearRoute();
    assert(actor.waypointCount() == 0 && !actor.reachedRouteEnd());
    assert(actor.nextWaypoint().x == actor.position().x);
    std::puts("PASS actor_route");
}

void testTwoStepTimer()
{
    P2WaterwraithActorParms parms;
    parms.startPhase       = P2BM_Walk;
    parms.twoStepTimerTicks = 5;
    P2WaterwraithActor actor(parms);
    P2WaterwraithActorInput in;
    for (int i = 0; i < 5; ++i) {
        step(actor, in);
    }
    assert(!actor.twoStepActive());
    assert(std::fabs(actor.currentSpeed() - parms.walkSpeed) < 1e-3f);
    step(actor, in); // sixth tick crosses ip01
    assert(actor.twoStepActive());
    assert(std::fabs(actor.currentSpeed() - parms.travelSpeed) < 1e-3f);
    std::puts("PASS actor_two_step");
}

void testRollerFullCycle()
{
    P2WaterwraithActor actor = makeActor(P2BM_Fall);
    P2WaterwraithActorInput in;
    P2WaterwraithActorOutput out;
    assert(actor.rig().tyrePhase() == P2TYRE_Land);

    in.landFloorContact = true;
    step(actor, in, &out);
    assert(actor.rig().tyrePhase() == P2TYRE_Freeze); // land -> freeze

    in           = P2WaterwraithActorInput{};
    in.isFallEnd = true;
    step(actor, in, &out);
    assert(actor.phase() == P2BM_Recover);

    in         = P2WaterwraithActorInput{};
    in.animEnd = true;
    step(actor, in, &out); // Recover end calls rig.moveRestart
    assert(actor.phase() == P2BM_Walk);
    assert(actor.rig().tyrePhase() == P2TYRE_Move); // freeze -> move

    in             = P2WaterwraithActorInput{};
    in.quakeFreeze = true;
    step(actor, in, &out);
    assert(actor.rig().tyrePhase() == P2TYRE_Freeze); // move -> quake freeze

    // Zero the roller while it is attached; death must stay gated on dismount.
    bool dead = true;
    assert(p2_waterwraith_actor_apply_damage(actor, P2WaterwraithRig::kTyreMaxHealth, true, &dead)
           == P2WWDMG_Roller);
    assert(actor.rig().tyreHealth() == 0.0f && actor.rollerZeroed());
    assert(!dead);
    assert(!actor.rig().beginDead()); // no dismount yet

    in            = P2WaterwraithActorInput{};
    in.isTyreDead = true;
    step(actor, in, &out); // dismount + Escape
    assert(actor.phase() == P2BM_Escape);
    assert(!actor.rig().attachedToOwner() && actor.rig().ownerInvulnerableSet());
    assert(out.dismountRequested);

    in                = P2WaterwraithActorInput{};
    in.tyreDeathStart = true;
    step(actor, in, &out); // dismounted + zero HP => tyre_getoff allowed
    assert(out.tyreDeathStarted);
    assert(actor.rig().tyrePhase() == P2TYRE_Dead);

    in                  = P2WaterwraithActorInput{};
    in.tyreDeadAnimEnd  = true;
    step(actor, in, &out);
    assert(out.tyreRemoved && !actor.rig().alive());
    std::puts("PASS actor_roller_cycle");
}

void testDamageGating()
{
    // Riding Land: ignored.
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    bool dead                = true;
    assert(p2_waterwraith_actor_apply_damage(actor, 100.0f, true, &dead) == P2WWDMG_Ignored);
    assert(!dead && actor.rig().tyreHealth() == P2WaterwraithRig::kTyreMaxHealth);

    // Non-Purple while frozen: ignored structurally.
    actor.rig().landFloorContact();
    assert(p2_waterwraith_actor_apply_damage(actor, 100.0f, false, &dead) == P2WWDMG_Ignored);
    assert(actor.rig().tyreHealth() == P2WaterwraithRig::kTyreMaxHealth);

    // Purple while frozen: routed to the roller; pinch tracks the drop.
    assert(p2_waterwraith_actor_apply_damage(actor, 1400.0f, true, &dead) == P2WWDMG_Roller);
    assert(std::fabs(actor.rig().tyreHealth() - 400.0f) < 1e-3f);
    assert(actor.rollerPinched() && !actor.rollerZeroed());

    // Riding Move: ignored again.
    actor.rig().moveRestart();
    assert(p2_waterwraith_actor_apply_damage(actor, 100.0f, true, &dead) == P2WWDMG_Ignored);

    // Dismounted: routed to the wraith body.
    actor.rig().dismount();
    assert(p2_waterwraith_actor_apply_damage(actor, 1200.0f, true, &dead) == P2WWDMG_Body);
    assert(std::fabs(actor.bodyHealth() - 300.0f) < 1e-3f);
    assert(actor.bodyPinched() && !actor.bodyZeroed() && !dead);
    assert(p2_waterwraith_actor_apply_damage(actor, 300.0f, true, &dead) == P2WWDMG_Body);
    assert(dead && actor.bodyZeroed());
    std::puts("PASS actor_damage_gate");
}

void testTeardown()
{
    P2WaterwraithActor actor = makeActor(P2BM_Walk);
    actor.rig().landFloorContact();
    bool dead = false;
    assert(p2_waterwraith_actor_apply_damage(actor, P2WaterwraithRig::kTyreMaxHealth, true, &dead));
    assert(actor.rig().tyreHealth() == 0.0f);
    actor.rig().dismount();
    assert(actor.rig().beginDead() && actor.rig().finishDead());
    assert(!actor.rig().alive());

    // reset() tears down and re-births a fresh child.
    actor.reset();
    assert(actor.alive() && actor.rig().alive() && actor.rig().attachedToOwner());
    assert(actor.rig().tyrePhase() == P2TYRE_Land);
    assert(actor.phase() == P2BM_Fall);
    std::puts("PASS actor_teardown");
}

} // namespace

int main()
{
    testResetAndLifetime();
    testFallRecoverWalk();
    testBendAndRecover();
    testFlickReturnsToPostState();
    testRollerlessFreezeStun();
    testTiredWindDown();
    testDeadReleasesTreasureThenKills();
    testRouteLocomotion();
    testTwoStepTimer();
    testRollerFullCycle();
    testDamageGating();
    testTeardown();
    std::puts("PASS WATERWRAITH_ACTOR");
    return 0;
}
