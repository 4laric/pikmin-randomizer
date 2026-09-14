#include "pc_p2_bombsarai_fsm.h"

#include <cassert>
#include <cstdio>

// Standalone transition fixture for the lane-owned 13-state BombSarai FSM
// policy. Engine-free: all host inputs are scripted here. Source citations
// are to BombSaraiState.cpp / BombSarai.cpp at GPVE01 rev 0 (632af937).

namespace {
using S = P2BombSaraiFsmState;
using K = P2BombSaraiThrowKind;

P2BombSaraiFsmInput baseInput()
{
    P2BombSaraiFsmInput in;
    in.health = 1500.0f;          // retail general fp00
    in.heightAboveGround = 70.0f; // above fp03: height gate active
    in.flickRoll = 1.0f;          // never flick unless a test overrides
    return in;
}

// Runs n ticks with the given input, returning the last output.
P2BombSaraiFsmOutput run(P2BombSaraiFsm& fsm, P2BombSaraiFsmInput in, int ticks)
{
    P2BombSaraiFsmOutput out;
    for (int i = 0; i < ticks; ++i) fsm.update(in, out);
    return out;
}
}

int main()
{
    const P2BombSaraiFsmParms parms; // retail-disc defaults

    // Happy path: Wait --target/END--> Supply (supply on entry) --END-->
    // BombMove --target in attack XZ--> Release --KEYEVENT_2--> Release lob
    // --END--> Wait. (:178-207, :466, :477-489, :386-444, :528-543)
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        assert(fsm.state() == S::Wait); // initial state (BombSarai.cpp:50)
        P2BombSaraiFsmInput in = baseInput();
        in.targetWithinTerritory = true;
        P2BombSaraiFsmOutput out = run(fsm, in, 29);
        assert(fsm.state() == S::Wait && !out.entered);
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Supply && out.supplyRequested);
        // Supply births once: no repeat supply while the state continues.
        in.animEnd = false; in.carrying = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Supply && !out.supplyRequested);
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::BombMove);
        assert(fsm.carrySeconds() == 0.0f); // Supply cleanup reset (:495-501)
        in.animEnd = false; in.targetWithinAttackXZ = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Release);
        in.keyEvent2 = true;
        fsm.update(in, out);
        assert(out.throwRequested && out.throwKind == K::Release);
        in.keyEvent2 = false; in.carrying = false; // bomb is away
        in.targetWithinAttackXZ = false; in.targetWithinTerritory = false;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
    }

    // Wait idle: no target for > 3 s + END -> Move; Move timeout 5 s -> Wait
    // (:188-191, :318-354). Below fp03 the height gate stays closed for 5 s.
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.heightAboveGround = 10.0f; // below fp03
        P2BombSaraiFsmOutput out = run(fsm, in, 91); // > 3 s idle
        assert(fsm.state() == S::Wait);
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Move);
        in.animEnd = false;
        out = run(fsm, in, 151); // > 5 s
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Wait);
    }

    // 15 s carry cap forces Release in BombWait even with no target
    // (:242-244).
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.targetWithinTerritory = true; in.animEnd = true;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out); // -> Supply
        assert(fsm.state() == S::Supply);
        in.animEnd = false; in.carrying = true;
        fsm.update(in, out);
        // Drive straight into BombWait via a script-less path: END in Supply.
        in.animEnd = true;
        fsm.update(in, out); // -> BombMove
        assert(fsm.state() == S::BombMove);
        in.animEnd = false; in.waypointReached = true;
        fsm.update(in, out); // -> BombWait
        assert(fsm.state() == S::BombWait);
        in.waypointReached = false; in.targetWithinTerritory = true; // stay
        out = run(fsm, in, 15 * 30 + 2);
        assert(fsm.state() == S::Release);
    }

    // Bitter queue transits to Fall from BombWait, BombMove and BombFlick
    // (:268-271, :425-428, :804-807); Fall KEYEVENT_2 ejects skyward.
    for (int variant = 0; variant < 3; ++variant) {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.targetWithinTerritory = true; in.animEnd = true;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);            // Supply
        in.animEnd = false; in.carrying = true;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out);            // BombMove
        in.animEnd = false;
        if (variant == 0) {             // BombWait first
            in.waypointReached = true;
            fsm.update(in, out);
            assert(fsm.state() == S::BombWait);
        }
        if (variant == 2) {             // BombFlick via gate roll
            in.stuckPikmin = 5; in.flickRoll = 0.0f; // chance fp32 0.8 > 0
            fsm.update(in, out);
            assert(fsm.state() == S::BombFlick);
        }
        in.flickRoll = 1.0f; in.stuckPikmin = 0;
        in.bitterQueued = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Fall);
        in.bitterQueued = false;
        in.keyEvent2 = true;
        fsm.update(in, out);
        assert(out.throwRequested && out.throwKind == K::Fall);
    }

    // Purple stick forces Fall through the height gate even at full health
    // (BombSarai.cpp:322-324); below fp03 and inside 5 s the gate is closed.
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPikmin = 1; in.stuckPurple = 1;
        in.heightAboveGround = 10.0f; // gate closed
        P2BombSaraiFsmOutput out = run(fsm, in, 100); // < 5 s
        assert(fsm.state() == S::Wait);
        in.heightAboveGround = 70.0f; // gate opens
        fsm.update(in, out);
        assert(out.entered && fsm.state() == S::Fall);
    }

    // Flick probability: fp31 0.2 at 1 stuck, fp32 0.8 at 5, linear between;
    // success -> Flick/BombFlick by carriage, failure -> Fall (:326-336).
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPikmin = 1; in.flickRoll = 0.19f; // < 0.2 + 0.6/5*1 = 0.32
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Flick);
        in.keyEvent2 = true;
        fsm.update(in, out);
        assert(out.flickRequested);
        in.keyEvent2 = false; in.animEnd = true; in.stuckPikmin = 0;
        fsm.update(in, out);
        assert(fsm.state() == S::Move);
    }
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPikmin = 5; in.carrying = true; in.flickRoll = 0.79f; // < 0.8
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::BombFlick);
        in.animEnd = true; in.stuckPikmin = 0; in.flickRoll = 1.0f;
        fsm.update(in, out);
        assert(fsm.state() == S::BombMove);
    }
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPikmin = 5; in.flickRoll = 0.8f; // >= 0.8: roll fails
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Fall);
    }

    // Kill while carrying: unconditional zero-velocity drop + Dead, from any
    // state (BombSarai.cpp:57-61). Kill without a payload: Dead, no throw.
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.carrying = true; in.killed = true;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(out.throwRequested && out.throwKind == K::Death);
        assert(fsm.state() == S::Dead);
        // Dead is terminal.
        in.killed = false; in.animEnd = true; in.targetWithinTerritory = true;
        out = run(fsm, in, 60);
        assert(fsm.state() == S::Dead);
    }
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.killed = true;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(!out.throwRequested && fsm.state() == S::Dead);
    }

    // Fall finish: near floor -> Damage; dead on arrival -> Dead (:585-624).
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPurple = 1; // forced Fall
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Fall);
        in.stuckPurple = 0; in.carrying = false;
        in.heightAboveGround = 30.0f; // within 35 of floor
        fsm.update(in, out);
        assert(fsm.state() == S::Damage);
        // Damage recovers once nothing is stuck (:119-121).
        in.stuckPikmin = 0; in.heightAboveGround = 0.0f;
        fsm.update(in, out);
        assert(fsm.state() == S::TakeOff1); // full health > 50%
    }
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.health = 0.0f;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Fall); // gate: health <= 0
        in.heightAboveGround = 0.0f;
        fsm.update(in, out);
        assert(fsm.state() == S::Dead);
    }

    // TakeOff split at 50% health (:137-145, BombSarai.cpp:141-149) and the
    // retail fp40 0.8 s struggle cap; TakeOff2 flags the fast rise factor.
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPurple = 1;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out); // Fall
        in.stuckPurple = 0; in.heightAboveGround = 0.0f;
        fsm.update(in, out); // Damage
        in.stuckPikmin = 2; in.health = 600.0f; // 40% of 1500
        out = run(fsm, in, 25); // 0.8 s struggle cap at 30 Hz = 24 ticks
        assert(fsm.state() == S::TakeOff2);
        assert(out.fastTakeOff);
        in.stuckPikmin = 0; in.animEnd = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Move);
    }
    {
        P2BombSaraiFsm fsm; fsm.reset(parms);
        P2BombSaraiFsmInput in = baseInput();
        in.stuckPurple = 1;
        P2BombSaraiFsmOutput out;
        fsm.update(in, out);
        in.stuckPurple = 0; in.heightAboveGround = 0.0f;
        fsm.update(in, out);
        in.stuckPikmin = 1; in.health = 800.0f; // > 50%
        out = run(fsm, in, 25); // retail fp40 0.8 s struggle cap
        assert(fsm.state() == S::TakeOff1);
        assert(!out.fastTakeOff);
    }

    std::puts("PASS BOMBSARAI_FSM");
    return 0;
}
