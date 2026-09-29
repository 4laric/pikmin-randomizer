#pragma once
// Own-identity Chappy-family FSM policy (inst-chappy, #871). Engine-free:
// pure input -> output transition tables transcribed from the P2 source
// states, so tools/p2_chappy_fsm_test.cpp pins them without the engine.
//
// Adult branch (ChappyBase::FSM, chappyState.cpp): Sleep is the spawn
// state; sight or damage wakes through Turn into Walk; Walk closes to
// Attack inside range; Attack returns to Walk on completion; Flick
// interrupts on shake-off condition and resumes; distance from home
// routes TurnToHome -> GoHome -> Sleep; health at zero routes Dead.
// Kuma branch: patrols waypoints (TurnPath/WalkPath), Lost when the
// target escapes, Rebirth on the revive timer, Attack/Flick/Dead shared.
// KumaKo branch: Wait by default, WalkPath toward the parent Bulbear,
// Walk/Attack/Flick/Dead shared, Press on trampling. King branch: walks
// the territory, WarCry on sight, Attack in range, Hide/HideWait/Appear
// burrow cycle, Eat/Swallow for bombs, Damage on bomb stun, Dead at zero.
#include "pc_p2_chappy_policy.h"

namespace p2chappyfsm {

enum Family {
    FAMILY_ADULT = 0, // 2 Chappy, 33 FireChappy, 43 YellowChappy
    FAMILY_KUMA = 1,  // 35 KumaChappy, 67 LeafChappy
    FAMILY_KUMAKO = 2, // 76 KumaKochappy
    FAMILY_KING = 3,  // 53 KingChappy
};

inline Family familyForSource(unsigned source)
{
    switch (source) {
    case 35:
    case 67:
        return FAMILY_KUMA;
    case 76:
        return FAMILY_KUMAKO;
    case 53:
        return FAMILY_KING;
    default:
        return FAMILY_ADULT;
    }
}

// State ids are the source StateID orders (see pc_p2_chappy_policy.h).
// Adult: Turn 0, Dead 1, Flick 2, Walk 3, Attack 4, TurnToHome 5,
// GoHome 6, Sleep 7. Kuma: Dead 0, Rebirth 1, Lost 2, Attack 3, Flick 4,
// Turn 5, TurnPath 6, Walk 7, WalkPath 8. KumaKo: Dead 0, Press 1,
// Wait 2, Attack 3, Flick 4, Walk 5, WalkPath 6. King: Walk 0,
// Attack 1, Dead 2, Flick 3, WarCry 4, Damage 5, Turn 6, Eat 7, Hide 8,
// HideWait 9, Appear 10, Caution 11, Swallow 12.
struct In {
    int state = 7;
    float hp = 1.0f;
    bool seesTarget = false;
    bool inRange = false;
    bool damaged = false;
    bool flick = false;
    bool farFromHome = false;
    bool attackDone = false;
    bool lostTarget = false;
    bool reviveReady = false;
    bool parentNear = false;
    bool burrowed = false;
    bool bombStun = false;
};

struct Out {
    int next = 7;
    bool changed = false;
};

inline Out tickAdult(const In& in)
{
    Out out;
    out.next = in.state;
    if (in.hp <= 0.0f) {
        out.next = p2chappy::ADULT_DEAD;
    } else if (in.flick && in.state != p2chappy::ADULT_DEAD) {
        out.next = p2chappy::ADULT_FLICK;
    } else {
        switch (in.state) {
        case p2chappy::ADULT_SLEEP:
            if (in.damaged || in.seesTarget) out.next = p2chappy::ADULT_TURN;
            break;
        case p2chappy::ADULT_TURN:
            out.next = p2chappy::ADULT_WALK;
            break;
        case p2chappy::ADULT_WALK:
            if (in.inRange) out.next = p2chappy::ADULT_ATTACK;
            else if (in.farFromHome) out.next = p2chappy::ADULT_TURN_TO_HOME;
            break;
        case p2chappy::ADULT_ATTACK:
            if (in.attackDone) out.next = p2chappy::ADULT_WALK;
            break;
        case p2chappy::ADULT_FLICK:
            if (in.attackDone) out.next = p2chappy::ADULT_WALK;
            break;
        case p2chappy::ADULT_TURN_TO_HOME:
            out.next = p2chappy::ADULT_GO_HOME;
            break;
        case p2chappy::ADULT_GO_HOME:
            if (!in.farFromHome) out.next = p2chappy::ADULT_SLEEP;
            break;
        default:
            break;
        }
    }
    out.changed = (out.next != in.state);
    return out;
}

inline Out tickKuma(const In& in)
{
    Out out;
    out.next = in.state;
    if (in.hp <= 0.0f) {
        out.next = 0; // Dead
    } else if (in.flick) {
        out.next = 4; // Flick
    } else {
        switch (in.state) {
        case 6: // TurnPath
            out.next = 8; // WalkPath
            break;
        case 8: // WalkPath
            if (in.seesTarget) out.next = 7; // Walk
            else if (in.lostTarget) out.next = 2; // Lost
            break;
        case 7: // Walk
            if (in.inRange) out.next = 3; // Attack
            else if (in.lostTarget) out.next = 2; // Lost
            break;
        case 3: // Attack
            if (in.attackDone) out.next = 7; // Walk
            break;
        case 4: // Flick
            if (in.attackDone) out.next = 7; // Walk
            break;
        case 2: // Lost
            if (in.seesTarget) out.next = 7; // Walk
            else if (in.reviveReady) out.next = 1; // Rebirth
            break;
        case 1: // Rebirth
            if (in.attackDone) out.next = 6; // TurnPath
            break;
        case 5: // Turn
            out.next = 7; // Walk
            break;
        default:
            break;
        }
    }
    out.changed = (out.next != in.state);
    return out;
}

inline Out tickKumako(const In& in)
{
    Out out;
    out.next = in.state;
    if (in.hp <= 0.0f) {
        out.next = 0; // Dead
    } else if (in.flick) {
        out.next = 4; // Flick
    } else {
        switch (in.state) {
        case 2: // Wait
            if (in.parentNear || in.seesTarget) out.next = 6; // WalkPath
            break;
        case 6: // WalkPath
            if (in.inRange) out.next = 3; // Attack
            else if (!in.parentNear && !in.seesTarget) out.next = 2; // Wait
            break;
        case 5: // Walk
            if (in.inRange) out.next = 3; // Attack
            break;
        case 3: // Attack
            if (in.attackDone) out.next = 5; // Walk
            break;
        case 4: // Flick
            if (in.attackDone) out.next = 5; // Walk
            break;
        default:
            break;
        }
    }
    out.changed = (out.next != in.state);
    return out;
}

inline Out tickKing(const In& in)
{
    Out out;
    out.next = in.state;
    if (in.hp <= 0.0f) {
        out.next = 2; // Dead
    } else if (in.bombStun) {
        out.next = 5; // Damage
    } else if (in.flick) {
        out.next = 3; // Flick
    } else {
        switch (in.state) {
        case 0: // Walk
            if (in.inRange) out.next = 1; // Attack
            else if (in.seesTarget) out.next = 4; // WarCry
            else if (in.burrowed) out.next = 8; // Hide
            break;
        case 4: // WarCry
            if (in.attackDone) out.next = 0; // Walk
            break;
        case 1: // Attack
            if (in.attackDone) out.next = 0; // Walk
            break;
        case 8: // Hide
            out.next = 9; // HideWait
            break;
        case 9: // HideWait
            if (!in.burrowed) out.next = 10; // Appear
            break;
        case 10: // Appear
            if (in.attackDone) out.next = 11; // Caution
            break;
        case 11: // Caution
            if (in.attackDone) out.next = 0; // Walk
            break;
        case 7: // Eat
            out.next = 12; // Swallow
            break;
        case 12: // Swallow
            if (in.attackDone) out.next = 0; // Walk
            break;
        default:
            break;
        }
    }
    out.changed = (out.next != in.state);
    return out;
}

inline Out tick(unsigned source, const In& in)
{
    switch (familyForSource(source)) {
    case FAMILY_KUMA:
        return tickKuma(in);
    case FAMILY_KUMAKO:
        return tickKumako(in);
    case FAMILY_KING:
        return tickKing(in);
    default:
        return tickAdult(in);
    }
}

} // namespace p2chappyfsm
