#include "pc_p2_long_legs_fsm.h"

#include <cassert>
#include <cstdio>

// Standalone lifecycle fixture for the lane-owned Long Legs source policy.
// Engine-free: every IK, animation, projectile and creature effect is scripted
// here. Source citations are to docs/PIKMIN2_LONG_LEGS_AUDIT.md (US GPVE01 rev 0)
// and the Damagumo/Houdai/BigFoot state machines.

namespace {
using S = P2LongLegsState;
using Species = P2LongLegsSpecies;

P2LongLegsFsmInput baseInput()
{
    P2LongLegsFsmInput in;
    in.health = 1000.0f;
    in.ikMoveRatio = 1.0f; // resting unless a test overrides
    return in;
}

P2LongLegsFsmOutput run(P2LongLegsFsm& fsm, P2LongLegsFsmInput in, int ticks)
{
    P2LongLegsFsmOutput out;
    for (int i = 0; i < ticks; ++i) fsm.update(in, out);
    return out;
}
}

int main()
{
    // Damagumo lifecycle: Stay (dormant) --wake--> Land --END--> Wait --timer-->
    // Walk; accumulating Pikmin interrupts with Flick, ending back in Wait.
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Damagumo));
        assert(fsm.state() == S::Stay);

        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Stay && out.bitterImmune && !out.damageable);

        in.wakeTargetNearby = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Land);
        in.wakeTargetNearby = false;
        fsm.update(in, out);
        assert(out.bitterImmune && !out.damageable); // immunity holds until key 2
        in.landingKey2 = true;
        fsm.update(in, out);
        assert(out.feetFired && out.footCrush); // key 2 fires all four feet
        assert(out.damageable && !out.bitterImmune);
        in.landingKey2 = false;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
        assert(out.chosenSeconds >= 1.75f && out.chosenSeconds <= 3.5f);

        in.animEnd = false;
        in.pikminAccumulating = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Flick);
        in.pikminAccumulating = false;
        in.flickKey2 = true;
        fsm.update(in, out);
        assert(out.shake);
        in.flickKey2 = false;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
    }

    // Wait duration honours the host roll; Walk advances on its own timer.
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Damagumo));
        P2LongLegsFsmInput in = baseInput();
        in.wakeTargetNearby = true;
        P2LongLegsFsmOutput out;
        fsm.update(in, out); // Land
        in.wakeTargetNearby = false;
        in.animEnd = true;
        fsm.update(in, out); // Wait
        assert(fsm.state() == S::Wait);
        assert(out.chosenSeconds == 1.75f); // roll defaults to 0 -> waitMin
        in.animEnd = false;
        out = run(fsm, in, 53); // 1.77 s
        assert(fsm.state() == S::Walk);
        assert(fsm.stateSeconds() < 0.1f);
        out = run(fsm, in, 98); // 3.27 s -> crosses walkMin 3.25 s
        assert(fsm.state() == S::Wait);
    }

    // Foot crush: only while descending/planting with move ratio above 1, and
    // only for species with press code (Houdai never presses).
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Damagumo));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.wakeTargetNearby = true; fsm.update(in, out);
        in.wakeTargetNearby = false; in.animEnd = true; fsm.update(in, out); // Wait
        in.animEnd = false; run(fsm, in, 60); // -> Walk (roll 0 -> 3.25 s)
        assert(fsm.state() == S::Walk);
        in.footDescendingOrPlanting = false; in.ikMoveRatio = 2.0f;
        fsm.update(in, out);
        assert(!out.footCrush); // a resting foot is harmless
        in.footDescendingOrPlanting = true; in.ikMoveRatio = 1.5f;
        fsm.update(in, out);
        assert(out.footCrush);
        in.ikMoveRatio = 1.0f;
        fsm.update(in, out);
        assert(!out.footCrush); // ratio must be above 1
    }
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Houdai));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.wakeTargetNearby = true; fsm.update(in, out);
        in.wakeTargetNearby = false; in.animEnd = true; fsm.update(in, out); // Wait
        in.animEnd = false; run(fsm, in, 100); // -> Walk
        assert(fsm.state() == S::Walk);
        in.footDescendingOrPlanting = true; in.ikMoveRatio = 2.0f;
        fsm.update(in, out);
        assert(!out.footCrush); // Houdai legs never damage
    }

    // Death: held treasure drops straight down; otherwise the no-treasure child
    // burst is requested. No carcass and Death is terminal.
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Damagumo));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.holdingTreasure = true;
        in.killed = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Dead);
        assert(out.dropTreasure && out.birthChildren == 0);
        in.killed = false; in.holdingTreasure = false;
        out = run(fsm, in, 60);
        assert(fsm.state() == S::Dead && out.birthChildren == 0);
    }
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Damagumo));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.killed = true;
        fsm.update(in, out);
        assert(out.birthChildren == 25 && !out.dropTreasure); // 25 Shijimi
    }
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::BigFoot));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.killed = true;
        fsm.update(in, out);
        assert(out.birthChildren == 30); // 30 Mitites
    }

    // Houdai Shot: always entered after a Flick; one shell per attack loop while
    // the burst is on, then the off window pauses fire until it re-arms.
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Houdai));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.wakeTargetNearby = true; fsm.update(in, out); // Land
        in.wakeTargetNearby = false; in.animEnd = true; fsm.update(in, out); // Wait
        in.animEnd = false;
        in.pikminAccumulating = true; fsm.update(in, out); // Flick
        assert(fsm.state() == S::Flick);
        in.pikminAccumulating = false;
        in.animEnd = true; fsm.update(in, out); // Flick END -> Shot
        assert(out.entered && fsm.state() == S::Shot);

        in.animEnd = false;
        in.shotLoop = true;
        fsm.update(in, out);
        assert(out.fireShell); // burst on, loop boundary fires

        // Cross the 2.5 s burst-on window; while off, loop boundaries are silent.
        out = run(fsm, in, 76);
        assert(fsm.state() == S::Shot);
        out = run(fsm, in, 10); // inside the 1.0 s off window
        assert(!out.fireShell);
        out = run(fsm, in, 25); // off window elapsed, burst re-arms
        fsm.update(in, out);
        assert(out.fireShell);

        in.shotLoop = false;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
    }

    // Houdai Shot also opens from Wait when the burst cooldown reaches the
    // reused mSearchHeight (50 s), and taking damage resets that cooldown.
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::Houdai));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.wakeTargetNearby = true; fsm.update(in, out); // Land
        in.wakeTargetNearby = false; in.animEnd = true; fsm.update(in, out); // Wait
        in.animEnd = false;
        run(fsm, in, 1400); // 46.7 s < 50 s
        assert(fsm.state() != S::Shot);
        assert(fsm.shotCooldownSeconds() < 50.0f);
        in.damageTaken = true;
        fsm.update(in, out);
        assert(fsm.shotCooldownSeconds() == 0.0f);
        in.damageTaken = false;
        bool shot = false;
        for (int i = 0; i < 1800 && !shot; ++i) { // <= 60 s from the reset
            fsm.update(in, out);
            if (fsm.state() == S::Shot) shot = true;
        }
        assert(shot); // ~50 s cooldown, allowing Wait/Walk cycle slack
    }

    // BigFoot: fixed 5 s Wait, one-cycle rage set when Flick ends, post-shake
    // walk of 5 s, then rage cleared.
    {
        P2LongLegsFsm fsm;
        fsm.reset(p2LongLegsParmsFor(Species::BigFoot));
        P2LongLegsFsmInput in = baseInput();
        P2LongLegsFsmOutput out;
        in.wakeTargetNearby = true; fsm.update(in, out); // Land
        in.wakeTargetNearby = false; in.animEnd = true; fsm.update(in, out); // Wait
        assert(out.chosenSeconds == 5.0f);
        in.animEnd = false;
        in.pikminAccumulating = true; fsm.update(in, out); // Flick
        assert(fsm.state() == S::Flick);
        in.pikminAccumulating = false;
        in.animEnd = true; fsm.update(in, out); // Flick END -> Wait, rage set
        assert(fsm.enraged());
        in.animEnd = false;
        P2LongLegsFsmOutput walkOut;
        bool walked = false;
        for (int i = 0; i < 200 && !walked; ++i) { // fixed 5 s Wait
            fsm.update(in, walkOut);
            if (fsm.state() == S::Walk) walked = true;
        }
        assert(walked);
        assert(walkOut.chosenSeconds == 5.0f && walkOut.enragedWalk); // post-shake travel
        bool waited = false;
        for (int i = 0; i < 200 && !waited; ++i) { // 5 s post-shake Walk
            fsm.update(in, out);
            if (fsm.state() == S::Wait) waited = true;
        }
        assert(waited && !fsm.enraged());
    }

    std::puts("PASS LONG_LEGS_FSM");
    return 0;
}
