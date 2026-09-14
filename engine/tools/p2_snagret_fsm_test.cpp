#include "pc_p2_snagret_fsm.h"

#include <cassert>
#include <cstdio>

// Standalone lifecycle fixture for the lane-owned Snagret source policy.
// Engine-free: spatial queries, animation keys and interactions are scripted.
// Source: docs/PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md (US GPVE01 rev 0).

namespace {
using S = P2SnagretState;
using Species = P2SnagretSpecies;
using Box = P2SnagretPeckBox;

P2SnagretFsmInput baseInput()
{
    P2SnagretFsmInput in;
    in.health = 1000.0f;
    return in;
}

P2SnagretFsmOutput run(P2SnagretFsm& fsm, P2SnagretFsmInput in, int ticks)
{
    P2SnagretFsmOutput out;
    for (int i = 0; i < ticks; ++i) fsm.update(in, out);
    return out;
}
}

int main()
{
    // Peck boxes: source forward x lateral extents for both species.
    {
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 40.0f, 0.0f) == Box::Near);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 100.0f, 0.0f) == Box::Normal);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 200.0f, 0.0f) == Box::Far);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 100.0f, 80.0f) == Box::Right);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 100.0f, -80.0f) == Box::Left);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 300.0f, 0.0f) == Box::None);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeCrow, 100.0f, 40.0f) == Box::None);
        assert(P2SnagretFsm::strikeForward(Species::SnakeCrow, Box::Normal) == 120.0f);
        assert(P2SnagretFsm::strikeForward(Species::SnakeCrow, Box::Far) == 190.0f);

        assert(P2SnagretFsm::selectPeckBox(Species::SnakeWhole, 100.0f, 0.0f) == Box::Near);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeWhole, 150.0f, 0.0f) == Box::Normal);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeWhole, 220.0f, 0.0f) == Box::Far);
        assert(P2SnagretFsm::selectPeckBox(Species::SnakeWhole, 120.0f, 80.0f) == Box::Right);
        assert(P2SnagretFsm::strikeForward(Species::SnakeWhole, Box::Far) == 220.0f);
    }

    // SnakeCrow burrow cycle: buried for at least fp12 2.5 s, then a target in
    // territory surfaces 120 units away as appear1 (roll < fp01 0.6) or appear2.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        P2SnagretFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Stay && out.bitterImmune);

        in.targetInTerritory = true; // too early: below the buried minimum
        fsm.update(in, out);
        assert(fsm.state() == S::Stay);
        P2SnagretFsmOutput appearOut;
        bool appeared = false;
        for (int i = 0; i < 100 && !appeared; ++i) {
            fsm.update(in, appearOut);
            if (fsm.state() == S::Appear1) appeared = true;
        }
        assert(appeared); // roll 0 -> fast appear1
        assert(appearOut.surfaced);
        assert(!appearOut.bitterImmune); // bitter immunity only while buried

        in.targetInTerritory = false;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
    }
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        in.roll = 0.9f; // >= fp01 -> slow appear2
        P2SnagretFsmOutput out = run(fsm, in, 76);
        in.targetInTerritory = true;
        out = run(fsm, in, 1);
        assert(fsm.state() == S::Appear2);
    }

    // Attack peck / re-peck, then release. Captains are never swallowed in the
    // host, so the policy only emits peck intents.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        in.targetInTerritory = true;
        P2SnagretFsmOutput out = run(fsm, in, 76); // Appear1
        in.animEnd = true;
        fsm.update(in, out); // Wait
        assert(fsm.state() == S::Wait);
        in.animEnd = false;
        in.targetInPeckBox = true;
        in.targetForward = 100.0f; in.targetLateral = 0.0f;
        fsm.update(in, out);
        assert(fsm.state() == S::Attack);
        assert(out.peckBox == Box::Normal && out.strikeForward == 120.0f);

        in.attackKey4 = true; in.mouthSlotFree = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Attack); // free mouth slot re-pecks
        assert(out.peckBox == Box::Normal);
        in.mouthSlotFree = false;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
        in.attackKey4 = false;
    }

    // Latched head Pikmin forces Struggle, which lasts 1.5 s and returns to Wait.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        in.targetInTerritory = true;
        P2SnagretFsmOutput out = run(fsm, in, 76); // Appear1
        in.targetInTerritory = false; in.animEnd = true;
        fsm.update(in, out); // Wait
        in.animEnd = false;
        in.latchedPikmin = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Struggle);
        fsm.update(in, out); // Struggle body runs on the tick after entry
        assert(out.struggle);
        in.latchedPikmin = false;
        run(fsm, in, 46);
        assert(fsm.state() == S::Wait);
    }

    // Stuck-Pikmin shake threshold dives; the dive key 2 flicks and returns to Stay.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        in.targetInTerritory = true;
        P2SnagretFsmOutput out = run(fsm, in, 76);
        in.targetInTerritory = false; in.animEnd = true;
        fsm.update(in, out); // Wait
        assert(fsm.state() == S::Wait);
        in.animEnd = false;
        in.stuckPikmin = true; in.shakeThreshold = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Disappear && out.diveFlick);
        in.stuckPikmin = false; in.shakeThreshold = false; in.animEnd = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Stay);
    }

    // SnakeCrow never walks; an aligned target outside a peck box keeps it waiting.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        in.targetInTerritory = true;
        run(fsm, in, 76);
        in.animEnd = true;
        run(fsm, in, 1);
        in.animEnd = false;
        run(fsm, in, 60);
        assert(fsm.state() == S::Wait); // SnakeCrow has no Walk state
    }

    // SnakeWhole foot-assisted pursuit: align before hopping, Home when the
    // target leaves the territory.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeWhole));
        P2SnagretFsmInput in = baseInput();
        in.targetInTerritory = true;
        P2SnagretFsmOutput out = run(fsm, in, 16); // buriedMin 0.5 s
        assert(fsm.state() == S::Appear1);
        in.animEnd = true;
        fsm.update(in, out); // Wait
        in.animEnd = false;
        fsm.update(in, out); // not facing: pivot in place
        assert(fsm.state() == S::Wait);
        in.facingTargetWithin30 = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Walk);
        in.runKey2 = true;
        fsm.update(in, out);
        assert(out.hopRequested && !out.hopHome);
        in.runKey2 = false;
        in.targetInTerritory = false;
        fsm.update(in, out);
        assert(fsm.state() == S::Home);
        in.runKey2 = true;
        fsm.update(in, out);
        assert(out.hopRequested && out.hopHome);
        in.runKey2 = false;
        in.targetInHome = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Wait);
    }

    // Death: held treasure drops from the beak, a carriable corpse remains, and
    // death is terminal.
    {
        P2SnagretFsm fsm;
        fsm.reset(p2SnagretParmsFor(Species::SnakeCrow));
        P2SnagretFsmInput in = baseInput();
        in.holdingTreasure = true;
        in.killed = true;
        P2SnagretFsmOutput out;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Dead);
        assert(out.dropTreasure && out.leaveCorpse && !out.bitterImmune);
        in.killed = false; in.holdingTreasure = false;
        run(fsm, in, 60);
        assert(fsm.state() == S::Dead);
    }

    std::puts("PASS SNAGRET_FSM");
    return 0;
}
