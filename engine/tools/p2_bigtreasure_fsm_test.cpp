#include "pc_p2_bigtreasure_fsm.h"

#include <cassert>
#include <cstdio>

// Lane-owned transition fixture for the 12-state BigTreasure FSM policy.
// Engine-free: every host input is scripted; fixtures tick at the 30 Hz
// source rate and never touch creatures/animations. Source citations point
// into src/plugProjectNishimuraU/BigTreasureState.cpp at research revision
// 632af937 (state regs :20-35).

namespace {

P2BigTreasureFsmInput tick()
{
    P2BigTreasureFsmInput in;
    in.health = 5000.0f;
    in.hasAnyWeapon = true;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = true;
    in.chosenWeapon = -1;
    return in;
}

// Run `ticks` updates with a constant input; returns the last output.
P2BigTreasureFsmOutput run(P2BigTreasureFsm& fsm, const P2BigTreasureFsmInput& in, int ticks)
{
    P2BigTreasureFsmOutput out;
    for (int i = 0; i < ticks; ++i) fsm.update(in, out);
    return out;
}

// Run until a state enters (or the tick budget runs out); returns the tick
// count, -1 on failure. The transition's output is left in `out`.
int runUntil(P2BigTreasureFsm& fsm, P2BigTreasureFsmInput in, P2BigTreasurePhase target,
             P2BigTreasureFsmOutput& out, int maxTicks = 8000)
{
    for (int i = 1; i <= maxTicks; ++i) {
        fsm.update(in, out);
        if (out.entered && fsm.state() == target) return i;
    }
    return -1;
}

// Stay -> Land via the no-demo path (timer latches 4.0 then trips).
// Leaves `out` from the Land-transition tick.
bool reachLand(P2BigTreasureFsm& fsm, P2BigTreasureFsmInput in, P2BigTreasureFsmOutput& out)
{
    in.hasTarget = true;
    in.bootDemoPlayed = false;
    fsm.update(in, out); // Stay: hasTarget -> timer = 4.0 (:163-168)
    fsm.update(in, out); // Stay: 4.03 > 4.0 -> Land (:170-174)
    return out.entered && fsm.state() == P2BT_Land;
}

} // namespace

int main()
{
    const P2BigTreasureFsmParms parms;

    // -----------------------------------------------------------------------
    // 1. Stay -> Land: no boot demo, timer jumps to 4.0 then trips (:163-174)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        in.hasTarget = true; in.bootDemoPlayed = false;
        fsm.update(in, out);
        assert(!out.entered);                     // first tick only latches the timer
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Land);
        assert(out.bitterImmuneOn);               // Stay/Land stay bitter-immune (:138)
    }

    // -----------------------------------------------------------------------
    // 2. Stay + boot demo: timer 0.01, waits ~4 s before Land (:164-166)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        in.hasTarget = true; in.bootDemoPlayed = true;
        P2BigTreasureFsmOutput out = run(fsm, in, 120); // 0.01 + 119/30 ~ 3.98 s
        assert(!out.entered);
        fsm.update(in, out);                          // 0.01 + 120/30 > 4.0
        assert(out.entered && fsm.state() == P2BT_Land);
    }

    // -----------------------------------------------------------------------
    // 3. Stay without target: idles indefinitely; latches once one arrives
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        in.hasTarget = false;
        P2BigTreasureFsmOutput out = run(fsm, in, 3000); // 100 s
        assert(out.state == P2BT_Stay && !out.entered);
        in.hasTarget = true; in.bootDemoPlayed = false;
        fsm.update(in, out);
        assert(!out.entered); // latch
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Land);
    }

    // -----------------------------------------------------------------------
    // 4. Land -> Walk: no flick, no weapons (:262-275)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Walk);
        assert(out.bitterImmuneOff && out.startProgramedIK); // Land cleanup (:287)
        assert(out.startIKMotion);                            // Walk init (:740)
    }

    // -----------------------------------------------------------------------
    // 5. Land -> ItemWalk: no flick, has weapons (:271-275)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_ItemWalk);
        assert(out.startIKMotion); // ItemWalk init (:806)
        assert(out.bitterImmuneOff);
    }

    // -----------------------------------------------------------------------
    // 6. Land -> PreAttack: flick + has weapons (:265-267)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon);              // setTreasureAttack (:483)
        assert(out.resetAttackLimitTimer);   // resetAttackLimitTimer (:477)
    }

    // -----------------------------------------------------------------------
    // 7. Land -> Flick: flick + no weapons (:268-270)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Flick);
        assert(out.bitterImmuneOff);
    }

    // -----------------------------------------------------------------------
    // 8. Land -> Dead: health <= 0 at END (:263-264)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.health = 0.0f; in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 9. Wait -> Flick (:313-323)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        // Land -> Walk -> Wait (timer 10, IK gate)
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        assert(fsm.state() == P2BT_Walk);
        in.animEnd = false;
        out = run(fsm, in, 400); // timer accrues past 10; pending Wait
        assert(fsm.state() == P2BT_Walk); // blocked on IK gate
        in.finishIKMotion = true; in.animEnd = true;
        fsm.update(in, out); // -> Wait (:773-775)
        assert(out.entered && fsm.state() == P2BT_Wait);
        // Now Wait -> Flick on the flick trigger
        in.finishIKMotion = false; in.animEnd = false; in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Flick);
    }

    // -----------------------------------------------------------------------
    // 10. Wait -> Walk on the 5 s timer (:324-327)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        in.animEnd = false;
        out = run(fsm, in, 400);
        in.finishIKMotion = true; in.animEnd = true;
        fsm.update(in, out); // -> Wait
        assert(out.entered && fsm.state() == P2BT_Wait);
        // 5 s elapses -> Walk
        in.flickTrigger = false; in.finishIKMotion = false; in.animEnd = false;
        int ticks = runUntil(fsm, in, P2BT_Walk, out);
        assert(ticks > 0);
        assert(out.startIKMotion);
    }

    // -----------------------------------------------------------------------
    // 11. Wait -> Dead on zero health (:318-320)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        in.animEnd = false;
        out = run(fsm, in, 400);
        in.finishIKMotion = true; in.animEnd = true;
        fsm.update(in, out); // -> Wait
        assert(fsm.state() == P2BT_Wait);
        in.health = 0.0f;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 12. ItemWait -> DropItem: all weapons gone (:375-378)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        assert(fsm.state() == P2BT_ItemWalk);
        in.animEnd = false;
        out = run(fsm, in, 400); // timer past 10; pending ItemWait
        in.finishIKMotion = true;
        fsm.update(in, out); // -> ItemWait (:837-840 / :850-852)
        assert(out.entered && fsm.state() == P2BT_ItemWait);
        in.finishIKMotion = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.chosenWeapon = -1;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_DropItem);
    }

    // -----------------------------------------------------------------------
    // 13. ItemWait -> PreAttack on flick / attack-limit (:380-383)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        // ItemWait via Land -> ItemWalk (timer) -> gate
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out);
        in.animEnd = false;
        out = run(fsm, in, 400);
        in.finishIKMotion = true;
        fsm.update(in, out);
        assert(fsm.state() == P2BT_ItemWait);
        in.finishIKMotion = false; in.attackLimitTime = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon);
    }

    // -----------------------------------------------------------------------
    // 14. ItemWait -> ItemWalk on the 5 s timer (:384-386)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        out = run(fsm, in, 400); // timer past 10
        in.finishIKMotion = true;
        fsm.update(in, out); // -> ItemWait
        assert(out.entered && fsm.state() == P2BT_ItemWait);
        // 5 s with no flick / attack-limit -> ItemWalk
        in.finishIKMotion = false;
        int ticks = runUntil(fsm, in, P2BT_ItemWalk, out);
        assert(ticks > 0);
        assert(out.startIKMotion);
    }

    // -----------------------------------------------------------------------
    // 15. Flick -> Walk, and Flick KEYEVENT_2 shakes off Pikmin (:440-453)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> Flick
        assert(fsm.state() == P2BT_Flick);
        in.flickTrigger = false; in.animEnd = false; in.keyEvent2 = true;
        fsm.update(in, out);
        assert(out.flickRequested); // flickStickPikmin (:440-445)
        in.keyEvent2 = false; in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Walk);
    }

    // -----------------------------------------------------------------------
    // 16. Flick -> Dead on zero health (:447-449)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> Flick
        in.flickTrigger = false; in.health = 0.0f;
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 17. PreAttack -> DropItem: all weapons gone (:497-500)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        assert(fsm.state() == P2BT_PreAttack);
        in.flickTrigger = false; in.animEnd = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_DropItem);
    }

    // -----------------------------------------------------------------------
    // 18. PreAttack -> PreAttack: chosen weapon lost mid-charge re-picks
    //     (:502-505). StateAttack reuses the choice (no re-pick, :551-564).
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        assert(fsm.state() == P2BT_PreAttack);
        // host feeds the pick
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Gas;
        fsm.update(in, out);
        assert(fsm.chosenWeapon() == P2BTWEAPON_Gas);
        // Gas falls mid-charge with other weapons alive
        in.weaponAttached[P2BTWEAPON_Gas] = false; in.chosenWeapon = -1;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon);
        // host re-picks (elec still alive)
        in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        assert(fsm.chosenWeapon() == P2BTWEAPON_Elec);
    }

    // -----------------------------------------------------------------------
    // 19. PreAttack -> Attack (END), with per-weapon finish motion (:507-533)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out); // consume pick
        assert(fsm.chosenWeapon() == P2BTWEAPON_Elec);
        in.shouldFinishMotion = true;
        fsm.update(in, out);
        assert(out.finishMotionRequested); // timer > getPreAttackTimeMax (:507-510)
        in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Attack);
        assert(fsm.chosenWeapon() == P2BTWEAPON_Elec); // choice carried over
    }

    // -----------------------------------------------------------------------
    // 20. Attack -> DropItem: all weapons gone (:573-576)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        assert(fsm.state() == P2BT_Attack);
        in.animEnd = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.chosenWeapon = -1;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_DropItem);
        assert(out.finishAttack); // Attack cleanup (:611-613)
    }

    // -----------------------------------------------------------------------
    // 21. Attack -> PreAttack: chosen weapon lost mid-attack (:578-581)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Gas;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        assert(fsm.state() == P2BT_Attack && fsm.chosenWeapon() == P2BTWEAPON_Gas);
        in.animEnd = false;
        in.weaponAttached[P2BTWEAPON_Gas] = false; in.chosenWeapon = -1;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon && out.finishAttack);
    }

    // -----------------------------------------------------------------------
    // 22. Attack -> PutItem on END (:598-600); PutItem continues using the
    //     same chosen weapon.
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        in.animEnd = false;
        fsm.update(in, out); // still Attack; no re-pick needed
        assert(fsm.state() == P2BT_Attack && fsm.chosenWeapon() == P2BTWEAPON_Elec);
        in.animEnd = true;
        fsm.update(in, out); // -> PutItem
        assert(out.entered && fsm.state() == P2BT_PutItem);
        assert(out.finishAttack && fsm.chosenWeapon() == P2BTWEAPON_Elec);
    }

    // -----------------------------------------------------------------------
    // 23. PutItem -> DropItem: all weapons gone (:642-645)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        in.animEnd = true;
        fsm.update(in, out); // -> PutItem
        assert(fsm.state() == P2BT_PutItem);
        in.animEnd = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.chosenWeapon = -1;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_DropItem);
    }

    // -----------------------------------------------------------------------
    // 24. PutItem -> ItemWalk on END without flick (:655-660)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        in.animEnd = true;
        fsm.update(in, out); // -> PutItem
        assert(fsm.state() == P2BT_PutItem);
        in.animEnd = true; in.flickTrigger = false;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_ItemWalk);
    }

    // -----------------------------------------------------------------------
    // 25. PutItem -> PreAttack on END with flick (:656-658)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        in.animEnd = true;
        fsm.update(in, out); // -> PutItem
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon);
    }

    // -----------------------------------------------------------------------
    // 26. PutItem -> PreAttack: chosen weapon lost (:647-650)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        in.flickTrigger = false; in.animEnd = false; in.chosenWeapon = P2BTWEAPON_Elec;
        fsm.update(in, out);
        in.animEnd = true;
        fsm.update(in, out); // -> Attack
        in.animEnd = true;
        fsm.update(in, out); // -> PutItem
        assert(fsm.state() == P2BT_PutItem);
        in.animEnd = false; in.weaponAttached[P2BTWEAPON_Elec] = false;
        in.chosenWeapon = -1;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon);
    }

    // -----------------------------------------------------------------------
    // 27. DropItem -> Dead on zero health (:703-705)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        // Land -> ItemWalk -> ItemWait -> DropItem (all weapons gone)
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        out = run(fsm, in, 400);
        in.finishIKMotion = true;
        fsm.update(in, out); // -> ItemWait
        in.finishIKMotion = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        fsm.update(in, out); // -> DropItem
        assert(fsm.state() == P2BT_DropItem);
        in.health = 0.0f; in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 28. DropItem -> Flick on END with flick (:706-708)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        out = run(fsm, in, 400);
        in.finishIKMotion = true;
        fsm.update(in, out); // -> ItemWait
        in.finishIKMotion = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        fsm.update(in, out); // -> DropItem
        assert(fsm.state() == P2BT_DropItem);
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Flick);
    }

    // -----------------------------------------------------------------------
    // 29. DropItem -> Walk on END without flick (:709-711)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        out = run(fsm, in, 400);
        in.finishIKMotion = true;
        fsm.update(in, out); // -> ItemWait
        in.finishIKMotion = false; in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        fsm.update(in, out); // -> DropItem
        in.animEnd = true; in.flickTrigger = false;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Walk);
        assert(out.startIKMotion);
    }

    // -----------------------------------------------------------------------
    // 30. Walk -> Dead immediately on zero health (:753-756)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        assert(fsm.state() == P2BT_Walk);
        in.animEnd = false; in.health = 0.0f;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 31. Walk -> Flick: flick sets pending, IK + END gate the exit
    //     (:758-761, :773-775)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        in.animEnd = false;
        in.flickTrigger = true;
        fsm.update(in, out);
        assert(fsm.state() == P2BT_Walk); // only deferred
        assert(out.finishIKMotionRequested);
        in.flickTrigger = false; in.finishIKMotion = true; in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Flick);
    }

    // -----------------------------------------------------------------------
    // 32. Walk -> Wait: 10 s timer + IK/END gate (:762-765, :773-775)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        in.animEnd = false;
        out = run(fsm, in, 400); // timer past 10, pending Wait
        assert(fsm.state() == P2BT_Walk); // IK gate holds
        in.finishIKMotion = true; in.animEnd = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Wait);
    }

    // -----------------------------------------------------------------------
    // 33. ItemWalk -> Dead immediately on zero health (:819-822)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        assert(fsm.state() == P2BT_ItemWalk);
        in.animEnd = false; in.health = 0.0f;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 34. ItemWalk: all weapons gone mid-walk -> anim-28->24 swap request
    //     (:824-827)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.itemWalkSwapped = false;
        fsm.update(in, out);
        assert(out.itemWalkWeaponSwap); // still armed-walk anim (28)
        assert(fsm.state() == P2BT_ItemWalk);
        // after the host swaps, the else branch runs
        in.itemWalkSwapped = true; in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.finishIKMotionRequested); // flick pending -> Flick (:828-835)
        assert(!out.itemWalkWeaponSwap);
    }

    // -----------------------------------------------------------------------
    // 35. ItemWalk -> PreAttack on flick with weapons (:828-835)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        in.flickTrigger = true;
        fsm.update(in, out);
        assert(out.finishIKMotionRequested);
        in.flickTrigger = false; in.finishIKMotion = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_PreAttack);
        assert(out.pickWeapon);
    }

    // -----------------------------------------------------------------------
    // 36. ItemWalk -> ItemWait on 10 s timer with weapons (:837-840)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        out = run(fsm, in, 400); // timer past 10, pending ItemWait
        assert(fsm.state() == P2BT_ItemWalk);
        in.finishIKMotion = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_ItemWait);
    }

    // -----------------------------------------------------------------------
    // 37. ItemWalk -> Wait on 10 s timer with no weapons (:837-844)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true;
        fsm.update(in, out); // -> ItemWalk
        in.animEnd = false;
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.itemWalkSwapped = true; // host already swapped the anim
        out = run(fsm, in, 400);   // timer past 10, pending Wait
        assert(fsm.state() == P2BT_ItemWalk);
        in.finishIKMotion = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Wait);
    }

    // -----------------------------------------------------------------------
    // 38. Dead: KEYEVENT_100 throws up + releases Loozy (:108-110)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        in.killed = true;
        P2BigTreasureFsmOutput out;
        fsm.update(in, out); // any state -> Dead
        assert(fsm.state() == P2BT_Dead);
        in.killed = false; in.keyEvent100 = true;
        fsm.update(in, out);
        assert(out.throwupItem && out.releaseLoozy);
        assert(!out.entered);
    }

    // -----------------------------------------------------------------------
    // 39. Dead: KEYEVENT_END kills (:114-116)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        in.killed = true;
        P2BigTreasureFsmOutput out;
        fsm.update(in, out);
        in.killed = false; in.keyEvent100 = false; in.animEnd = true;
        fsm.update(in, out);
        assert(out.killRequested && !out.entered);
    }

    // -----------------------------------------------------------------------
    // 40. Dead is terminal regardless of inputs
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        in.killed = true;
        P2BigTreasureFsmOutput out;
        fsm.update(in, out);
        assert(fsm.state() == P2BT_Dead);
        in.killed = false;
        in.hasTarget = true; in.flickTrigger = true; in.animEnd = true;
        in.keyEvent100 = true;
        out = run(fsm, in, 120);
        assert(fsm.state() == P2BT_Dead && !out.entered);
    }

    // -----------------------------------------------------------------------
    // 41. Kill from Walk: unconditional Dead (BigTreasure.cpp onKill)
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.hasAnyWeapon = false;
        for (int i = 0; i < P2BTWEAPON_Count; ++i) in.weaponAttached[i] = false;
        in.animEnd = true;
        fsm.update(in, out); // -> Walk
        assert(fsm.state() == P2BT_Walk);
        in.animEnd = false; in.killed = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    // -----------------------------------------------------------------------
    // 42. Kill from PreAttack (even mid-charge): unconditional Dead
    // -----------------------------------------------------------------------
    {
        P2BigTreasureFsm fsm; fsm.reset(parms);
        P2BigTreasureFsmInput in = tick();
        P2BigTreasureFsmOutput out;
        assert(reachLand(fsm, in, out));
        in.animEnd = true; in.flickTrigger = true;
        fsm.update(in, out); // -> PreAttack
        assert(fsm.state() == P2BT_PreAttack);
        in.flickTrigger = false; in.killed = true;
        fsm.update(in, out);
        assert(out.entered && fsm.state() == P2BT_Dead);
    }

    std::puts("PASS BIGTREASURE_FSM");
    return 0;
}