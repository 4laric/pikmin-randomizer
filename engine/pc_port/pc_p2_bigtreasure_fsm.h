#pragma once

#include "pc_p2_bigtreasure.h"

// 12-state BigTreasure (Titan Dweevil) FSM policy, mirroring the source
// machine registered in FSM::init (BigTreasureState.cpp:20-35 at research
// revision 632af93787b9c95b63f0c13be32b161375ce3a96). Engine-free: the host
// feeds per-tick inputs (health, weapon capture status, target sensing,
// animation keyframes, flick/attack-limit triggers, IK finish, kill event,
// and the host-supplied weapon pick result) and consumes outputs (state
// transitions and action requests). The policy never touches creatures,
// animations, the map, weapons, or the attack pool; the host seam performs
// requested effects through the ownership and attack-director modules.
//
// Per-element pre-attack/attack durations are host-evaluated and supplied as
// `shouldFinishMotion` (the host compares stateTimer against the per-weapon
// threshold). All randomness enters as explicit host-supplied values
// (flickTrigger, attackLimitTime, bootDemoPlayed, chosenWeapon), keeping
// fixtures deterministic. Ticks are the 30 Hz source rate.

struct P2BigTreasureFsmParms {
    float stayTargetDelay = 4.0f;   // Stay timer after target detection
    float waitTimerLimit = 5.0f;    // Wait / ItemWait timer threshold
    float walkTimerLimit = 10.0f;   // Walk / ItemWalk timer threshold
};

struct P2BigTreasureFsmInput {
    float health = 0.0f;
    bool hasAnyWeapon = false;
    bool weaponAttached[P2BTWEAPON_Count] = {};
    int chosenWeapon = -1;           // host-fed result of pickWeapon()
    bool hasTarget = false;          // Olimar / Pikmin within private radius
    bool bootDemoPlayed = false;     // first-encounter demo played this session
    bool animEnd = false;            // host KEYEVENT_END pulse (one tick)
    bool keyEvent2 = false;          // host KEYEVENT_2 pulse
    bool keyEvent100 = false;        // host KEYEVENT_100 pulse (Dead)
    bool flickTrigger = false;       // host: isStartFlick() result
    bool attackLimitTime = false;    // host: isAttackLimitTime() result
    bool shouldFinishMotion = false; // host: stateTimer > perWeaponTimeMax
    bool finishIKMotion = false;     // host: IK motion reports finished
    bool itemWalkSwapped = false;    // host: ItemWalk anim left index 28
    bool killed = false;             // host: onKill event
};

struct P2BigTreasureFsmOutput {
    P2BigTreasurePhase state = P2BT_Dead;
    bool entered = false;

    // Action requests the host should perform this tick:
    bool pickWeapon = false;              // PreAttack init: call pickWeapon()
    bool resetAttackLimitTimer = false;   // PreAttack init: reset pacer timer
    bool startAttack = false;             // Attack KEYEVENT_2: call startAttack()
    bool finishAttack = false;            // Attack cleanup: call finishAttack()
    bool flickRequested = false;          // Flick KEYEVENT_2: flickStickPikmin
    bool throwupItem = false;             // Dead KEYEVENT_100
    bool releaseLoozy = false;            // Dead KEYEVENT_100
    bool killRequested = false;           // Dead KEYEVENT_END
    bool startIKMotion = false;           // Walk / ItemWalk init
    bool finishMotionRequested = false;   // PreAttack / Attack: per-weapon time max reached
    bool finishIKMotionRequested = false; // Walk / ItemWalk: request IK finish
    bool bitterImmuneOn = false;          // Stay / Land init
    bool bitterImmuneOff = false;         // Land cleanup
    bool startProgramedIK = false;        // Land cleanup
    bool itemWalkWeaponSwap = false;      // ItemWalk: weapons gone mid-walk
};

class P2BigTreasureFsm {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;

    void reset(const P2BigTreasureFsmParms& parms);
    void update(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);

    P2BigTreasurePhase state() const { return mState; }
    float stateTimer() const { return mStateTimer; }
    int chosenWeapon() const { return mChosenWeapon; }
    static const char* stateName(P2BigTreasurePhase state);

private:
    // Lane 32 persistence proposal (#246): engine-free serialization access
    // defined in pc_p2_bigtreasure_save.cpp. Not wired into the game save path.
    friend struct P2BigTreasureSaveAccess;

    void enter(P2BigTreasurePhase next, P2BigTreasureFsmOutput& out);

    void execDead(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execStay(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execLand(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execWait(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execItemWait(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execFlick(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execPreAttack(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execAttack(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execPutItem(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execDropItem(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execWalk(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);
    void execItemWalk(const P2BigTreasureFsmInput& in, P2BigTreasureFsmOutput& out);

    P2BigTreasureFsmParms mParms;
    P2BigTreasurePhase mState = P2BT_Stay;
    float mStateTimer = 0.0f;
    int mChosenWeapon = -1;
    bool mAwaitingWeaponPick = false;
    P2BigTreasurePhase mPendingNext = P2BT_Dead;
    bool mWaitingForIK = false;
};
