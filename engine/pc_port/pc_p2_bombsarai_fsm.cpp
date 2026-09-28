#include "pc_p2_bombsarai_fsm.h"

// State semantics transcribed from the audit (docs/PIKMIN2_BOMBSARAI_AUDIT.md
// lines 15-33), source src/plugProjectNishimuraU/BombSaraiState.cpp and
// BombSarai.cpp at revision 632af93787b9c95b63f0c13be32b161375ce3a96.
//
// Simplifications, all documented and host-visible:
// - Animation timing is host-fed keyframes (animEnd / keyEvent2 inputs); the
//   policy owns no clip lengths. The seam supplies a pinned schedule until
//   the #128 converter provides retail .bca durations.
// - The flick roll is a host-fed uniform (flickRoll) consumed only when the
//   height gate actually evaluates a flick, keeping the policy RNG-free.
// - Horizontal movement (walkToTarget) is host-owned; the policy consumes
//   only its arrival/timeout outcomes.

namespace {
int clampStuck(int count) // source clamps the stuck census to [0, 5]
{
    return count < 0 ? 0 : (count > 5 ? 5 : count);
}
}

void P2BombSaraiFsm::reset(const P2BombSaraiFsmParms& parms)
{
    mParms = parms;
    mState = P2BombSaraiFsmState::Wait; // BombSarai.cpp:50
    mStateTimer = mCarryTimer = mIdleTimer = mNoTargetTimer = mFallTimer = mStruggleTimer = 0.0f;
}

const char* P2BombSaraiFsm::stateName(P2BombSaraiFsmState state)
{
    switch (state) {
    case P2BombSaraiFsmState::Dead: return "Dead";
    case P2BombSaraiFsmState::Damage: return "Damage";
    case P2BombSaraiFsmState::Wait: return "Wait";
    case P2BombSaraiFsmState::BombWait: return "BombWait";
    case P2BombSaraiFsmState::Move: return "Move";
    case P2BombSaraiFsmState::BombMove: return "BombMove";
    case P2BombSaraiFsmState::Supply: return "Supply";
    case P2BombSaraiFsmState::Release: return "Release";
    case P2BombSaraiFsmState::Fall: return "Fall";
    case P2BombSaraiFsmState::TakeOff1: return "TakeOff1";
    case P2BombSaraiFsmState::TakeOff2: return "TakeOff2";
    case P2BombSaraiFsmState::Flick: return "Flick";
    case P2BombSaraiFsmState::BombFlick: return "BombFlick";
    }
    return "?";
}

void P2BombSaraiFsm::enter(P2BombSaraiFsmState next, P2BombSaraiFsmOutput& output)
{
    if (mState == P2BombSaraiFsmState::Supply) {
        mCarryTimer = 0.0f; // Supply cleanup resets mBombCarryTimer (:495-501)
    }
    mState = next;
    mStateTimer = mIdleTimer = mNoTargetTimer = mFallTimer = mStruggleTimer = 0.0f;
    output.entered = true;
    output.state = next;
    if (next == P2BombSaraiFsmState::Supply) {
        // supplyBomb() runs in state init (:466); a failed birth is the
        // host's silent no-payload path, the FSM proceeds regardless.
        output.supplyRequested = true;
    }
}

bool P2BombSaraiFsm::gateOnHeight(const P2BombSaraiFsmInput& input, P2BombSaraiFsmState& next)
{
    // getNextStateOnHeight (BombSarai.cpp:314-340).
    if (input.health <= 0.0f || input.stuckPurple > 0) {
        next = P2BombSaraiFsmState::Fall;
        return true;
    }
    const int stuck = clampStuck(input.stuckPikmin);
    if (stuck >= 1) {
        const float chance = mParms.flickChanceFree
            + (mParms.flickChanceLaden - mParms.flickChanceFree) * (float)stuck / 5.0f;
        if (input.flickRoll < chance) {
            next = input.carrying ? P2BombSaraiFsmState::BombFlick : P2BombSaraiFsmState::Flick;
        } else {
            next = P2BombSaraiFsmState::Fall; // roll failure defaults to Fall (:336)
        }
        return true;
    }
    return false;
}

void P2BombSaraiFsm::update(const P2BombSaraiFsmInput& input, P2BombSaraiFsmOutput& output)
{
    output = P2BombSaraiFsmOutput{};
    output.state = mState;

    mStateTimer += kSourceDelta;
    if (input.carrying) {
        mCarryTimer += kSourceDelta;
    }

    // onKill (BombSarai.cpp:57-61): unconditional zero-velocity drop, any state.
    if (input.killed) {
        if (input.carrying) {
            output.throwRequested = true;
            output.throwKind = P2BombSaraiThrowKind::Death;
        }
        enter(P2BombSaraiFsmState::Dead, output);
        return;
    }

    // Shared height gate for the hover states (altitude > fp03 or 5 s gate).
    const bool hoverState = mState == P2BombSaraiFsmState::Wait
        || mState == P2BombSaraiFsmState::BombWait || mState == P2BombSaraiFsmState::Move
        || mState == P2BombSaraiFsmState::BombMove;
    if (hoverState
        && (input.heightAboveGround > mParms.transitionHeight
            || mStateTimer > mParms.stateGateSeconds)) {
        P2BombSaraiFsmState next;
        if (gateOnHeight(input, next)) {
            enter(next, output);
            return;
        }
    }

    switch (mState) {
    case P2BombSaraiFsmState::Dead:
        break;

    case P2BombSaraiFsmState::Wait:
        output.untargetable = true;
        mIdleTimer = input.targetWithinTerritory ? 0.0f : mIdleTimer + kSourceDelta;
        if (input.animEnd) {
            if (input.targetWithinTerritory) {
                enter(P2BombSaraiFsmState::Supply, output);
            } else if (mIdleTimer > mParms.waitIdleSeconds) {
                enter(P2BombSaraiFsmState::Move, output);
            }
        }
        break;

    case P2BombSaraiFsmState::Move:
        if (input.animEnd) {
            if (input.targetWithinTerritory) {
                enter(P2BombSaraiFsmState::Supply, output);
            } else if (mStateTimer > mParms.moveTimeoutSeconds || input.waypointReached) {
                enter(P2BombSaraiFsmState::Wait, output);
            }
        }
        break;

    case P2BombSaraiFsmState::Supply:
        output.untargetable = true;
        if (input.animEnd) {
            P2BombSaraiFsmState next;
            if (gateOnHeight(input, next)) {
                enter(next, output);
            } else {
                enter(P2BombSaraiFsmState::BombMove, output);
            }
        }
        break;

    case P2BombSaraiFsmState::BombWait:
        output.untargetable = true;
        if (input.bitterQueued) {
            enter(P2BombSaraiFsmState::Fall, output);
        } else if ((input.carrying && mCarryTimer > mParms.carryCapSeconds)
                   || input.targetAttackable || input.targetWithinAttackXZ) {
            enter(P2BombSaraiFsmState::Release, output);
        } else {
            mNoTargetTimer = input.targetWithinTerritory ? 0.0f : mNoTargetTimer + kSourceDelta;
            if (input.targetWithinTerritory) {
                enter(P2BombSaraiFsmState::BombMove, output);
            } else if (mNoTargetTimer > mParms.noTargetSeconds) {
                enter(P2BombSaraiFsmState::Wait, output);
            }
        }
        break;

    case P2BombSaraiFsmState::BombMove:
        if (input.bitterQueued) {
            enter(P2BombSaraiFsmState::Fall, output);
        } else if ((input.carrying && mCarryTimer > mParms.carryCapSeconds)
                   || input.targetAttackable || input.targetWithinAttackXZ) {
            enter(P2BombSaraiFsmState::Release, output);
        } else if (input.waypointReached) {
            enter(P2BombSaraiFsmState::BombWait, output);
        }
        break;

    case P2BombSaraiFsmState::Release:
        if (input.keyEvent2 && input.carrying) {
            // Fixed lob, no homing (:528-534).
            output.throwRequested = true;
            output.throwKind = P2BombSaraiThrowKind::Release;
        }
        if (input.animEnd) {
            P2BombSaraiFsmState next;
            if (gateOnHeight(input, next)) {
                enter(next, output);
            } else {
                enter(P2BombSaraiFsmState::Wait, output);
            }
        }
        break;

    case P2BombSaraiFsmState::Fall:
        mFallTimer += kSourceDelta;
        if (input.keyEvent2 && input.carrying) {
            // Skyward ejection, higher pop-up than Release (:592-596).
            output.throwRequested = true;
            output.throwKind = P2BombSaraiThrowKind::Fall;
        }
        if (input.heightAboveGround <= mParms.fallFloorDistance
            || mFallTimer > mParms.fallTimeoutSeconds || input.animEnd) {
            enter(input.health <= 0.0f ? P2BombSaraiFsmState::Dead
                                       : P2BombSaraiFsmState::Damage, output);
        }
        break;

    case P2BombSaraiFsmState::Damage:
        mStruggleTimer += kSourceDelta;
        if (input.health <= 0.0f || input.stuckPikmin <= 0
            || mStruggleTimer > mParms.struggleSeconds) {
            if (input.health <= 0.0f) {
                enter(P2BombSaraiFsmState::Dead, output);
            } else if (input.health > 0.5f * mParms.maxHealth) {
                enter(P2BombSaraiFsmState::TakeOff1, output); // 50% split (:137-145)
            } else {
                enter(P2BombSaraiFsmState::TakeOff2, output);
            }
        }
        break;

    case P2BombSaraiFsmState::TakeOff1:
    case P2BombSaraiFsmState::TakeOff2:
        output.untargetable = true;
        output.fastTakeOff = mState == P2BombSaraiFsmState::TakeOff2; // rise factor 6
        if (input.health <= 0.0f) {
            enter(P2BombSaraiFsmState::Fall, output);
        } else if (input.heightAboveGround > mParms.transitionHeight) {
            P2BombSaraiFsmState next;
            if (gateOnHeight(input, next)) {
                enter(next, output);
            } else if (input.animEnd) {
                enter(P2BombSaraiFsmState::Move, output);
            }
        } else if (input.animEnd) {
            enter(P2BombSaraiFsmState::Move, output);
        }
        break;

    case P2BombSaraiFsmState::Flick:
        if (input.keyEvent2) {
            output.flickRequested = true; // flickStickPikmin effect is host-owned
        }
        if (input.animEnd) {
            enter(P2BombSaraiFsmState::Move, output);
        }
        break;

    case P2BombSaraiFsmState::BombFlick:
        if (input.bitterQueued) {
            enter(P2BombSaraiFsmState::Fall, output); // bittered mid-swing (:804-807)
        } else {
            if (input.keyEvent2) {
                output.flickRequested = true;
            }
            if (input.animEnd) {
                enter(P2BombSaraiFsmState::BombMove, output);
            }
        }
        break;
    }
}
