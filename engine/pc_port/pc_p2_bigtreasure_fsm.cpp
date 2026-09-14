#include "pc_p2_bigtreasure_fsm.h"

// State semantics transcribed from the source machine
// (src/plugProjectNishimuraU/BigTreasureState.cpp at research revision
// 632af937; state registrations at :20-35). Simplifications, all documented
// and host-visible:
// - Animation timing is host-fed keyframes (animEnd / keyEvent2 inputs); the
//   policy owns no clip lengths. Per-weapon pre-attack/attack durations are
//   host-evaluated (`shouldFinishMotion`) because they come from disc parms
//   (fp10-fp13/fp20-fp23/fp31).
// - The flick and attack-limit evaluations are host-fed booleans
//   (`flickTrigger` / `attackLimitTime`): the source logic touches the flick
//   timer, cell iteration, 3x accrual and box tests that belong to the host.
// - Transitions that the source gates on KEYEVENT_END / IK finish are
//   applied immediately in the policy when their condition is met; the one
//   exception is Walk/ItemWalk, whose flick/timer exits wait for the host
//   `finishIKMotion` gate exactly as the source gates on isFinishIKMotion().

namespace {

bool validWeapon(int weapon) { return weapon >= 0 && weapon < P2BTWEAPON_Count; }

} // namespace

void P2BigTreasureFsm::reset(const P2BigTreasureFsmParms& parms)
{
    mParms             = parms;
    mState             = P2BT_Stay; // BigTreasure.cpp onInit starts in Stay
    mStateTimer        = 0.0f;
    mChosenWeapon      = -1;
    mAwaitingWeaponPick = false;
    mPendingNext       = P2BT_Dead;
    mWaitingForIK      = false;
}

const char* P2BigTreasureFsm::stateName(P2BigTreasurePhase state)
{
    switch (state) {
    case P2BT_Dead: return "Dead";
    case P2BT_Stay: return "Stay";
    case P2BT_Land: return "Land";
    case P2BT_Wait: return "Wait";
    case P2BT_ItemWait: return "ItemWait";
    case P2BT_Flick: return "Flick";
    case P2BT_PreAttack: return "PreAttack";
    case P2BT_Attack: return "Attack";
    case P2BT_PutItem: return "PutItem";
    case P2BT_DropItem: return "DropItem";
    case P2BT_Walk: return "Walk";
    case P2BT_ItemWalk: return "ItemWalk";
    }
    return "?";
}

void P2BigTreasureFsm::enter(P2BigTreasurePhase next, P2BigTreasureFsmOutput& out)
{
    const P2BigTreasurePhase prev = mState;
    mState              = next;
    mStateTimer         = 0.0f;
    // Source re-picks the weapon only when entering PreAttack
    // (setTreasureAttack in StatePreAttack::init :483). Attack and PutItem
    // reuse the index chosen in PreAttack (:551-564, :620-633), so the
    // choice carries across those transitions and is only cleared on a fresh
    // PreAttack entry.
    mAwaitingWeaponPick = next == P2BT_PreAttack; // host must feed the pick
    if (next == P2BT_PreAttack) {
        mChosenWeapon = -1;
    }
    mPendingNext        = P2BT_Dead;
    mWaitingForIK       = false;
    out.entered         = true;
    out.state           = next;

    // Previous-state cleanup (non-generic side effects only; the host stops
    // blend motions generically on any transition).
    if (prev == P2BT_Land) {
        out.bitterImmuneOff  = true; // :287
        out.startProgramedIK = true; // :288
    }
    if (prev == P2BT_Attack) {
        out.finishAttack = true; // :612-613 (torn down even on loss)
    }

    // New-state init side effects the host must apply.
    switch (next) {
    case P2BT_Stay:
        out.bitterImmuneOn = true; // :138
        break;
    case P2BT_Land:
        out.bitterImmuneOn = true; // Land remains bitter-immune
        break;
    case P2BT_PreAttack:
        out.pickWeapon            = true; // setTreasureAttack (:483)
        out.resetAttackLimitTimer = true; // :477
        break;
    case P2BT_Walk:
    case P2BT_ItemWalk:
        out.startIKMotion = true; // :740 / :806
        break;
    default:
        break;
    }
}

void P2BigTreasureFsm::update(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    out    = P2BigTreasureFsmOutput{};
    out.state = mState;

    // onKill: unconditional Dead, any state (BigTreasure.cpp:115-120).
    if (in.killed) {
        enter(P2BT_Dead, out);
        return;
    }

    switch (mState) {
    case P2BT_Dead: execDead(in, out); break;
    case P2BT_Stay: execStay(in, out); break;
    case P2BT_Land: execLand(in, out); break;
    case P2BT_Wait: execWait(in, out); break;
    case P2BT_ItemWait: execItemWait(in, out); break;
    case P2BT_Flick: execFlick(in, out); break;
    case P2BT_PreAttack: execPreAttack(in, out); break;
    case P2BT_Attack: execAttack(in, out); break;
    case P2BT_PutItem: execPutItem(in, out); break;
    case P2BT_DropItem: execDropItem(in, out); break;
    case P2BT_Walk: execWalk(in, out); break;
    case P2BT_ItemWalk: execItemWalk(in, out); break;
    }
}

void P2BigTreasureFsm::execDead(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateDead (:58-118). Terminal; only two keyframes produce FSM-visible
    // outputs: KEYEVENT_100 at frame 320 (throwup + Loozy release) and
    // KEYEVENT_END at the clip tail (kill). Keyframes 2-11 are host-owned
    // effect hookups the host dispatches from state + keyframe.
    if (in.keyEvent100) {
        out.throwupItem  = true; // :108-110
        out.releaseLoozy = true;
    }
    if (in.animEnd) {
        out.killRequested = true; // :114-116
    }
}

void P2BigTreasureFsm::execStay(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateStay (:132-176). Two-phase: wait for a target within the private
    // radius, then count up to the Land delay (or the boot-demo fast path).
    if (mStateTimer < 0.01f) {
        if (in.hasTarget) {
            mStateTimer = in.bootDemoPlayed ? 0.01f : mParms.stayTargetDelay;
        }
    } else {
        mStateTimer += kSourceDelta;
        if (mStateTimer > mParms.stayTargetDelay) {
            enter(P2BT_Land, out);
        }
    }
}

void P2BigTreasureFsm::execLand(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateLand (:212-278). Key events 2/4/6/8/9 are host-side effects; on
    // KEYEVENT_END pick the follow-on by health/flick/capture order.
    if (!in.animEnd) {
        return;
    }
    if (in.health <= 0.0f) {
        enter(P2BT_Dead, out);
        return;
    }
    if (in.flickTrigger) {
        enter(in.hasAnyWeapon ? P2BT_PreAttack : P2BT_Flick, out); // :265-270
        return;
    }
    enter(in.hasAnyWeapon ? P2BT_ItemWalk : P2BT_Walk, out); // :271-275
}

void P2BigTreasureFsm::execWait(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateWait (:313-337). Timer ticks first; Dead/Flick/Walk in source are
    // finishMotion-then-END, which the policy applies immediately.
    mStateTimer += kSourceDelta;
    if (in.health <= 0.0f) {
        enter(P2BT_Dead, out); // :318-320
        return;
    }
    if (in.flickTrigger) {
        enter(P2BT_Flick, out); // :321-323
        return;
    }
    if (mStateTimer > mParms.waitTimerLimit) {
        enter(P2BT_Walk, out); // :324-327
    }
}

void P2BigTreasureFsm::execItemWait(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateItemWait (:372-397). Weapon-loss guard first; power guards then;
    // timer increments after the guards (source order).
    if (!in.hasAnyWeapon) {
        enter(P2BT_DropItem, out); // :375-378
        return;
    }
    if (in.flickTrigger || in.attackLimitTime) {
        enter(P2BT_PreAttack, out); // :380-383
        return;
    }
    if (mStateTimer > mParms.waitTimerLimit) {
        enter(P2BT_ItemWalk, out); // :384-386
        return;
    }
    mStateTimer += kSourceDelta;
}

void P2BigTreasureFsm::execFlick(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateFlick (:432-455). KEYEVENT_2 shakes; END resolves by health.
    if (in.keyEvent2) {
        out.flickRequested = true; // :440-445
    }
    if (in.animEnd) {
        enter(in.health <= 0.0f ? P2BT_Dead : P2BT_Walk, out); // :447-453
    }
}

void P2BigTreasureFsm::execPreAttack(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StatePreAttack (:494-534). Weapon-loss guards first (DropItem when all
    // gone, PreAttack re-entry when the chosen weapon fell). Then the
    // per-weapon pre-attack time gate and the END -> Attack transit.
    if (in.chosenWeapon >= 0 && validWeapon(in.chosenWeapon)) {
        mChosenWeapon       = in.chosenWeapon;
        mAwaitingWeaponPick = false;
    }
    if (!in.hasAnyWeapon) {
        enter(P2BT_DropItem, out); // :497-500
        return;
    }
    if (!mAwaitingWeaponPick && !(validWeapon(mChosenWeapon)
                                  && in.weaponAttached[mChosenWeapon])) {
        enter(P2BT_PreAttack, out); // :502-505 re-pick
        return;
    }
    mStateTimer += kSourceDelta;
    if (in.shouldFinishMotion) {
        out.finishMotionRequested = true;
    }
    if (in.animEnd) {
        enter(P2BT_Attack, out); // :531-533
    }
}

void P2BigTreasureFsm::execAttack(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateAttack (:570-601). Same two weapon-loss guards as PreAttack.
    if (in.chosenWeapon >= 0 && validWeapon(in.chosenWeapon)) {
        mChosenWeapon       = in.chosenWeapon;
        mAwaitingWeaponPick = false;
    }
    if (!in.hasAnyWeapon) {
        enter(P2BT_DropItem, out); // :573-576
        return;
    }
    if (!mAwaitingWeaponPick && !(validWeapon(mChosenWeapon)
                                  && in.weaponAttached[mChosenWeapon])) {
        enter(P2BT_PreAttack, out); // :578-581
        return;
    }
    mStateTimer += kSourceDelta;
    if (in.keyEvent2) {
        out.startAttack = true; // :595-597
    }
    if (in.shouldFinishMotion) {
        out.finishMotionRequested = true;
    }
    if (in.animEnd) {
        enter(P2BT_PutItem, out); // :598-600
    }
}

void P2BigTreasureFsm::execPutItem(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StatePutItem (:639-662). Same two weapon-loss guards; END splits on
    // the flick trigger.
    if (in.chosenWeapon >= 0 && validWeapon(in.chosenWeapon)) {
        mChosenWeapon       = in.chosenWeapon;
        mAwaitingWeaponPick = false;
    }
    if (!in.hasAnyWeapon) {
        enter(P2BT_DropItem, out); // :642-645
        return;
    }
    if (!mAwaitingWeaponPick && !(validWeapon(mChosenWeapon)
                                  && in.weaponAttached[mChosenWeapon])) {
        enter(P2BT_PreAttack, out); // :647-650
        return;
    }
    if (in.animEnd) {
        enter(in.flickTrigger ? P2BT_PreAttack : P2BT_ItemWalk, out); // :655-661
    }
}

void P2BigTreasureFsm::execDropItem(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateDropItem (:696-712). END resolves to Dead / Flick / Walk by
    // health and flick order.
    if (in.animEnd) {
        if (in.health <= 0.0f) {
            enter(P2BT_Dead, out); // :703-705
        } else if (in.flickTrigger) {
            enter(P2BT_Flick, out); // :706-708
        } else {
            enter(P2BT_Walk, out); // :709-711
        }
    }
}

void P2BigTreasureFsm::execWalk(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateWalk (:748-779). Health death is immediate; flick/timer exits
    // request an IK finish and transit when the host reports finishIKMotion.
    // The timer and IK gate run every tick as in source.
    if (in.health <= 0.0f) {
        enter(P2BT_Dead, out); // :753-756
        return;
    }
    if (in.flickTrigger) {
        mPendingNext              = P2BT_Flick; // :758-761
        mWaitingForIK             = true;
        out.finishIKMotionRequested = true;
    } else if (mStateTimer > mParms.walkTimerLimit) {
        mPendingNext              = P2BT_Wait; // :762-765
        mWaitingForIK             = true;
        out.finishIKMotionRequested = true;
    }
    mStateTimer += kSourceDelta; // :767
    if (mWaitingForIK && in.animEnd && in.finishIKMotion) {
        enter(mPendingNext, out); // :773-775 (KEYEVENT_END && isFinishIKMotion)
    }
}

void P2BigTreasureFsm::execItemWalk(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out)
{
    // StateItemWalk (:814-864). Death immediate. The swap-vs-else split
    // mirrors getCurrAnimationIndex() == 28: while the armed walk anim is
    // still playing and all weapons are gone, request the anim 28 -> 24 swap
    // and skip the flick/timer branch; the timer and IK gate run every tick
    // as in source (isFinishIKMotion checked regardless of branch).
    if (in.health <= 0.0f) {
        enter(P2BT_Dead, out); // :819-822
        return;
    }
    if (!in.hasAnyWeapon && !in.itemWalkSwapped) {
        out.itemWalkWeaponSwap = true; // :824-827
    } else {
        if (in.flickTrigger || in.attackLimitTime) {
            mPendingNext              = in.hasAnyWeapon ? P2BT_PreAttack : P2BT_Flick; // :828-835
            mWaitingForIK             = true;
            out.finishIKMotionRequested = true;
        } else if (mStateTimer > mParms.walkTimerLimit) {
            mPendingNext              = in.hasAnyWeapon ? P2BT_ItemWait : P2BT_Wait; // :837-844
            mWaitingForIK             = true;
            out.finishIKMotionRequested = true;
        }
    }
    mStateTimer += kSourceDelta; // :848
    if (mWaitingForIK && in.finishIKMotion) {
        enter(mPendingNext, out); // :850-852
    }
}