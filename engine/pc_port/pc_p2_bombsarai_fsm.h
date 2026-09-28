#pragma once

#include "pc_p2_bombsarai_bomb.h"

// Isolated BombSarai (Careening Dirigibug) carrier FSM policy, mirroring the
// 13-state source machine registered in FSM::init
// (src/plugProjectNishimuraU/BombSaraiState.cpp:19-35 at revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; state semantics per
// docs/PIKMIN2_BOMBSARAI_AUDIT.md "FSM: states and transitions").
//
// Engine-free: the host feeds per-tick inputs (health, stuck-Pikmin census,
// target sensing, animation keyframes, bitter/kill events, and the flick
// roll) and consumes outputs (state entries, supply/throw/flick requests,
// hover mode). The policy never touches creatures, animations, RNG state,
// the bomb pool, or the map; the seam (pc_p2_bombsarai_arena.cpp) performs
// the requested effects through the lane's bomb/hover policies.

enum class P2BombSaraiFsmState {
    Dead = 0, Damage = 1,
    Wait = 2, BombWait = 3, Move = 4, BombMove = 5,
    Supply = 6, Release = 7, Fall = 8,
    TakeOff1 = 9, TakeOff2 = 10, Flick = 11, BombFlick = 12
};

// Retail disc values (docs/PIKMIN2_ENGINE_DISC_PARMS.md #244 tables) are the
// defaults where the disc overrides the header; source-hardcoded timers per
// the audit. Nothing here is invented by the policy.
struct P2BombSaraiFsmParms {
    float transitionHeight = 50.0f;  // fp03 (disc matches header)
    float flickChanceFree = 0.2f;    // fp31 retail (header 0.1)
    float flickChanceLaden = 0.8f;   // fp32 retail (header 0.7)
    float struggleSeconds = 0.8f;    // fp40 retail (header 3.0)
    float maxHealth = 1500.0f;       // general fp00 retail
    float carryCapSeconds = 15.0f;   // hardcoded (BombSaraiState.cpp:242-244)
    float waitIdleSeconds = 3.0f;    // hardcoded (:188-191)
    float noTargetSeconds = 3.0f;    // hardcoded (:263-266)
    float moveTimeoutSeconds = 5.0f; // hardcoded (:318-322)
    float stateGateSeconds = 5.0f;   // hardcoded state-timer gate
    float fallFloorDistance = 35.0f; // hardcoded (:585-587)
    float fallTimeoutSeconds = 1.0f; // hardcoded (:585-587)
};

// One 30 Hz source tick of host-fed inputs. Booleans are level values sampled
// by the host every tick except the keyframe pulses (animEnd, keyEvent2) and
// the kill event, which are edge events consumed this tick only.
struct P2BombSaraiFsmInput {
    float health = 0.0f;
    bool carrying = false;           // host-held bomb exists (mHeldBomb)
    int stuckPikmin = 0;             // total stuck (clamped 0..5 where source clamps)
    int stuckPurple = 0;
    bool targetWithinTerritory = false; // getAttackablePikmin gate (territory radius)
    bool targetAttackable = false;      // isTargetAttackable (max attack range/angle)
    bool targetWithinAttackXZ = false;  // within mAttackRadius in XZ
    bool waypointReached = false;       // walkToTarget arrival (25 units, source)
    float heightAboveGround = 0.0f;     // hover output (position.y - minY)
    bool animEnd = false;               // host keyframe: state animation END
    bool keyEvent2 = false;             // host keyframe: KEYEVENT_2
    bool bitterQueued = false;          // EB_BitterQueued
    bool killed = false;                // host kill event (onKill)
    float flickRoll = 1.0f;             // host-fed uniform [0,1); consumed only
                                        // when the height gate evaluates a flick
};

struct P2BombSaraiFsmOutput {
    P2BombSaraiFsmState state = P2BombSaraiFsmState::Wait;
    bool entered = false;          // state entered this tick
    bool supplyRequested = false;  // Supply init side effect (BombSaraiState.cpp:466)
    bool throwRequested = false;   // throwBomb call this tick
    P2BombSaraiThrowKind throwKind = P2BombSaraiThrowKind::Release;
    bool flickRequested = false;   // Flick/BombFlick KEYEVENT_2 (effect host-owned)
    bool fastTakeOff = false;      // rise factor 6 (TakeOff2, BombSarai.cpp:205)
    bool untargetable = false;     // informational; host owns damage routing
};

class P2BombSaraiFsm {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;

    void reset(const P2BombSaraiFsmParms& parms);

    // One 30 Hz source update. Exactly one output per call.
    void update(const P2BombSaraiFsmInput& input, P2BombSaraiFsmOutput& output);

    P2BombSaraiFsmState state() const { return mState; }
    float carrySeconds() const { return mCarryTimer; }
    float stateSeconds() const { return mStateTimer; }
    static const char* stateName(P2BombSaraiFsmState state);

private:
    // getNextStateOnHeight (BombSarai.cpp:314-340). Consulted from
    // Wait/BombWait/Move/BombMove only once altitude exceeds fp03 or the
    // state timer exceeds 5 s (:178-207, :318-354, :386-444, :247-266).
    // Returns true when it forces a transition into *next.
    bool gateOnHeight(const P2BombSaraiFsmInput& input, P2BombSaraiFsmState& next);
    void enter(P2BombSaraiFsmState next, P2BombSaraiFsmOutput& output);

    P2BombSaraiFsmParms mParms;
    P2BombSaraiFsmState mState = P2BombSaraiFsmState::Wait;
    float mStateTimer = 0.0f;
    float mCarryTimer = 0.0f;   // mBombCarryTimer (reset on Supply cleanup, :495-501)
    float mIdleTimer = 0.0f;    // Wait idle timer
    float mNoTargetTimer = 0.0f;
    float mFallTimer = 0.0f;
    float mStruggleTimer = 0.0f;
};
