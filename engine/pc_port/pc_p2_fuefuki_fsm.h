#pragma once
#include "pc_p2_fuefuki_interference_policy.h"
#include <cmath>
#include <cstdint>
#include <vector>

// Narrow P2 Fuefuki FSM bridge policy (#245): the nine source states and
// their transitions, driving pc_p2_fuefuki_interference_policy.h for squad
// ownership. Not a P1 actor, map or animation implementation. Source basis:
// native/tools/P2_FUEFUKI_AUDIT.md (projectPiki/pikmin2 632af937).
//
// Host conventions: fixed 30 Hz simulation ticks (delta = 1/30), no wall
// clock, all randomness/map/animation facts arrive as deterministic inputs.
// The host feeds animation key events exactly as the source consumes them
// (KEYEVENT_2, KEYEVENT_3, KEYEVENT_END of the motion that emitted them).

enum class P2FuefukiFsmState {
    Dead     = 0,
    Stay     = 1,
    Land     = 2,
    Jump     = 3,
    Wait     = 4,
    Turn     = 5,
    Walk     = 6,
    Whisle   = 7, // dev spelling, source StateID
    Struggle = 8,
};

enum P2FuefukiEventBit {
    P2FUEFUKI_EB_NoInterrupt  = 1 << 0,
    P2FUEFUKI_EB_Untargetable = 1 << 1,
    P2FUEFUKI_EB_Lifegauge    = 1 << 2,
    P2FUEFUKI_EB_BitterImmune = 1 << 3,
    P2FUEFUKI_EB_Cullable     = 1 << 4,
};

// Retail defaults mirror include/Game/Entities/Fuefuki.h ProperParms; the
// host substitutes parsed parm-asset values at integration time.
struct P2FuefukiFsmParms {
    float maxGroundTime = 30.0f;        // fp01
    float minGroundTime = 20.0f;        // fp02 (appear-timer base; host rolls)
    float airborneTime = 3.0f;          // fp03
    float minWhistleTime = 0.0f;        // fp11
    float maxWhistleTimeNoSquad = 5.0f; // fp12
    float maxWhistleTimeWithSquad = 10.0f; // fp13
    float struggleTime = 3.0f;          // fp21
    float jumpTime = 0.0f;              // fp22
    float normalLandingChance = 0.5f;   // fp31 (host rolls)
    float attackRadius = 0.0f;          // C_GENERALPARMS whistle ring base
    float walkStateCap = 5.0f;          // hard-coded Walk state cap
    float castDuration = 3.0f;          // hard-coded Whisle cast length
    float escapeSpeed = 1500.0f;        // hard-coded Jump escape speed
};

struct P2FuefukiCandidate {
    std::uint32_t id = 0;
    bool living = false, callable = false, stuckToMouth = false, alreadyTeki = false;
};

struct P2FuefukiFsmInput {
    float delta = 0.0f;          // fixed tick, e.g. 1/30
    float health = 1.0f;
    int stuckPikmin = 0;         // attackers stuck on the beetle
    bool animPlaying = false;    // current motion playing (mIsPlaying)
    int keyEvent = 0;            // 0 none, 2, 3, 4 = KEYEVENT_END
    bool motionFinished = false; // isFinishMotion (Walk)
    bool turnComplete = false;   // turnToTargetPos result (Turn)
    bool arriveTarget = false;   // host: wall triangle or XZ dist^2 < 625
    bool intruder = false;       // host: Navi / non-owned non-stuck Pikmin
                                 // inside mPrivateRadius this tick
    bool pressed = false;        // press/hipdrop callback this tick
    bool bittered = false;       // EB_Bittered
    bool water = false;          // mWaterBox present (ripple effects)
    bool landingNormal = true;   // host-rolled fp31 result for Land init
    std::vector<P2FuefukiCandidate> candidates; // in-ring Pikmin this tick
    std::vector<std::uint32_t> followerPings;   // ActTeki pings this tick
};

struct P2FuefukiFsmOut {
    bool accepted = false;
    P2FuefukiFsmState state = P2FuefukiFsmState::Land;
    bool transited = false;
    std::uint32_t eventSet = 0, eventClear = 0; // P2FuefukiEventBit masks
    bool teleportToTarget = false;   // Land init: relocate + random facing
    bool requestFinishMotion = false;
    bool zeroVelocity = false;
    bool escapeVelocity = false;     // target velocity 1500 * facing
    bool flickNavi = false, flickPikmin = false, flickStuck = false;
    bool downEffect = false, ripple = false, fadeRipple = false;
    bool startWhistleEffect = false, stopWhistleEffect = false, whistleEcho = false;
    bool kill = false;               // dead-anim END: host kills the creature
    bool carcassCarryAnim = false;   // startCarcassMotion -> FUEFUKIANIM_Carry
    float whistleRadius = 0.0f;      // modifier * attackRadius while casting
    bool squadActive = false;
    std::vector<std::uint32_t> claimed;
    std::vector<std::uint32_t> releasedPanic;   // ownerDied followers
    std::vector<std::uint32_t> releasedSuspend; // flying/suspend followers
    P2FuefukiSuspendFallback suspendFallback = P2FUEFUKI_SUSPEND_FALLBACK_FREE;
    std::vector<std::uint32_t> pinged;
};

class P2FuefukiFsm {
    static constexpr int NEXT_NULL = -1;
    P2FuefukiFsmParms parms;
    P2FuefukiInterferencePolicy interference;
    P2FuefukiFsmState state = P2FuefukiFsmState::Land;
    int next = NEXT_NULL;
    float appearTimer = 0.0f, stateTimer = 0.0f, whistleTimer = 0.0f;
    bool canStruggle = false;

    bool squadActive() const { return interference.squadActive(); }

    bool isJumpAway(const P2FuefukiFsmInput& in)
    {
        if (appearTimer > parms.maxGroundTime) return true;
        if (!squadActive() && in.intruder) {
            appearTimer = parms.maxGroundTime; // source pins the timer
            return true;
        }
        return false;
    }

    bool isWhisleTimeMax(const P2FuefukiFsmInput& in) const
    {
        if (squadActive())
            return in.stuckPikmin > 0 ? whistleTimer > parms.maxWhistleTimeNoSquad
                                      : whistleTimer > parms.maxWhistleTimeWithSquad;
        return whistleTimer > parms.maxWhistleTimeNoSquad;
    }

    void requestFinish(P2FuefukiFsmOut& out, int nextState)
    {
        next = nextState;
        out.requestFinishMotion = true;
    }

    // Source StateWhisle::cleanup runs on ANY exit: stop the cast, keep
    // claims. Source StateStruggle::cleanup re-arms struggle.
    void leaveCleanup(P2FuefukiFsmState leaving, P2FuefukiFsmOut& out)
    {
        if (leaving == P2FuefukiFsmState::Whisle) {
            interference.endCast(interferenceEpoch());
            out.stopWhistleEffect = true;
            out.whistleEcho       = true;
            out.eventSet |= P2FUEFUKI_EB_Cullable; // finishWhisle restores culling
        } else if (leaving == P2FuefukiFsmState::Struggle) {
            canStruggle = true;
        }
    }

    std::uint64_t interferenceEpoch() const { return boundEpoch; }

    void transit(P2FuefukiFsmOut& out, int targetRaw)
    {
        P2FuefukiFsmState target =
            targetRaw == NEXT_NULL ? P2FuefukiFsmState::Wait : static_cast<P2FuefukiFsmState>(targetRaw);
        leaveCleanup(state, out);
        next      = NEXT_NULL;
        out.transited = true;
        switch (target) {
        case P2FuefukiFsmState::Dead: {
            // Source StateDead::init: deathProcedure, zero velocity. The
            // owner-death release is committed before host death callbacks.
            out.releasedPanic = interference.ownerDied(boundEpoch);
            out.eventClear |= P2FUEFUKI_EB_Cullable;
            out.zeroVelocity = true;
            break;
        }
        case P2FuefukiFsmState::Stay:
            canStruggle = false;
            appearTimer = 0.0f; // resetAppearTimer (host rolls fp01-fp02 weight)
            stateTimer  = 0.0f;
            out.eventSet |= P2FUEFUKI_EB_BitterImmune | P2FUEFUKI_EB_Untargetable;
            out.eventClear |= P2FUEFUKI_EB_NoInterrupt | P2FUEFUKI_EB_Lifegauge | P2FUEFUKI_EB_Cullable;
            out.zeroVelocity = true;
            // Beetle is airborne: followers exit with the Success/emote
            // branch (source ActTeki isFlying). Not a Panic release. The
            // brain destination is the resolved source constant Free
            // (ActTeki::getNextAIType()==ACT_Free, aiAction.cpp:108-110).
            {
                P2FuefukiSuspendOut susp = interference.suspend(boundEpoch);
                out.releasedSuspend      = susp.released;
                out.suspendFallback      = susp.fallback;
            }
            break;
        case P2FuefukiFsmState::Land:
            canStruggle = false;
            next        = static_cast<int>(P2FuefukiFsmState::Wait);
            stateTimer  = 0.0f;
            appearTimer = 0.0f;
            whistleTimer = (parms.maxWhistleTimeNoSquad - parms.minWhistleTime);
            out.eventClear |= P2FUEFUKI_EB_BitterImmune | P2FUEFUKI_EB_Untargetable | P2FUEFUKI_EB_Cullable;
            out.eventSet |= P2FUEFUKI_EB_NoInterrupt;
            out.zeroVelocity     = true;
            out.teleportToTarget = true;
            break;
        case P2FuefukiFsmState::Jump:
            canStruggle = true;
            stateTimer  = 0.0f;
            out.eventClear |= P2FUEFUKI_EB_BitterImmune;
            out.zeroVelocity = true;
            break;
        case P2FuefukiFsmState::Wait:
        case P2FuefukiFsmState::Turn:
        case P2FuefukiFsmState::Walk:
            stateTimer       = 0.0f;
            out.zeroVelocity = true;
            break;
        case P2FuefukiFsmState::Whisle:
            stateTimer = 0.0f;
            whistleTimer = 0.0f;
            interference.beginCast(boundEpoch);
            out.eventClear |= P2FUEFUKI_EB_Cullable; // non-cullable while casting
            out.zeroVelocity        = true;
            out.startWhistleEffect  = true;
            break;
        case P2FuefukiFsmState::Struggle:
            canStruggle      = false;
            stateTimer       = 0.0f;
            out.zeroVelocity = true;
            break;
        }
        state = target;
    }

    void enterDead(P2FuefukiFsmOut& out) { transit(out, static_cast<int>(P2FuefukiFsmState::Dead)); }

    std::uint64_t boundEpoch = 0;

public:
    explicit P2FuefukiFsm(P2FuefukiFsmParms p = P2FuefukiFsmParms()) : parms(p) { }

    P2FuefukiFsmState getState() const { return state; }
    P2FuefukiInterferencePolicy& squad() { return interference; }

    // Bind the squad-ownership epoch; spawn() emits the source onInit ->
    // FUEFUKI_Land entry commands.
    P2FuefukiFsmOut spawn(P2FuefukiOwnershipTable& table, std::uint64_t epoch)
    {
        P2FuefukiFsmOut out;
        if (boundEpoch || !interference.bind(&table, epoch)) return out;
        boundEpoch   = epoch;
        out.accepted = true;
        state        = P2FuefukiFsmState::Stay; // leave Land-entry path honest
        transit(out, static_cast<int>(P2FuefukiFsmState::Land));
        out.accepted = true;
        out.state    = state;
        out.releasedSuspend.clear(); // spawn has no followers to suspend
        return out;
    }

    P2FuefukiFsmOut tick(const P2FuefukiFsmInput& in)
    {
        P2FuefukiFsmOut out;
        if (!boundEpoch || !std::isfinite(in.delta) || in.delta < 0.0f || !std::isfinite(in.health))
            return out;
        out.accepted = true;

        appearTimer += in.delta;

        // Follower pings arrive from ActTeki exec in any state.
        for (std::uint32_t id : in.followerPings)
            if (interference.ping(boundEpoch, id).accepted) out.pinged.push_back(id);
        interference.tickSquad(boundEpoch);
        out.squadActive = squadActive();

        // press/hipdrop -> Struggle (source pressCallBack/hipdropCallBack).
        if (in.pressed && canStruggle && !in.bittered && state != P2FuefukiFsmState::Dead
            && state != P2FuefukiFsmState::Struggle) {
            transit(out, static_cast<int>(P2FuefukiFsmState::Struggle));
            out.state = state;
            return out;
        }

        const float dt = in.delta;
        switch (state) {
        case P2FuefukiFsmState::Dead:
            if (in.animPlaying && in.keyEvent == 4) {
                out.kill             = true;
                out.carcassCarryAnim = true;
            }
            break;

        case P2FuefukiFsmState::Stay:
            stateTimer += dt;
            if (stateTimer > parms.airborneTime) transit(out, static_cast<int>(P2FuefukiFsmState::Land));
            break;

        case P2FuefukiFsmState::Land:
            if (isJumpAway(in)) {
                requestFinish(out, static_cast<int>(P2FuefukiFsmState::Jump));
            } else if (isWhisleTimeMax(in)) {
                requestFinish(out, static_cast<int>(P2FuefukiFsmState::Whisle));
            }
            if (in.animPlaying) {
                if (in.keyEvent == 2) {
                    out.eventClear |= P2FUEFUKI_EB_NoInterrupt;
                    out.eventSet |= P2FUEFUKI_EB_Lifegauge;
                    out.downEffect = true;
                    if (in.water) out.ripple = true;
                } else if (in.keyEvent == 3) {
                    canStruggle = true;
                    out.eventSet |= P2FUEFUKI_EB_Cullable;
                } else if (in.keyEvent == 4) {
                    transit(out, next);
                }
            }
            break;

        case P2FuefukiFsmState::Jump:
            if (canStruggle) {
                out.zeroVelocity = true;
                if (in.health <= 0.0f) {
                    enterDead(out);
                    break;
                }
            } else {
                out.escapeVelocity = true;
                out.flickStuck     = true;
            }
            if (stateTimer > parms.jumpTime) out.requestFinishMotion = true;
            stateTimer += dt;
            if (in.animPlaying) {
                if (in.keyEvent == 2) {
                    out.eventSet |= P2FUEFUKI_EB_BitterImmune;
                } else if (in.keyEvent == 3) {
                    canStruggle = false;
                    out.eventSet |= P2FUEFUKI_EB_Untargetable;
                    out.eventClear |= P2FUEFUKI_EB_Lifegauge | P2FUEFUKI_EB_Cullable;
                    out.escapeVelocity = true;
                    out.flickNavi = out.flickPikmin = out.flickStuck = true;
                    out.downEffect = true;
                    if (in.water) out.fadeRipple = true;
                } else if (in.keyEvent == 4) {
                    transit(out, static_cast<int>(P2FuefukiFsmState::Stay));
                }
            }
            break;

        case P2FuefukiFsmState::Wait:
            if (stateTimer > 0.0f) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Turn));
            if (isWhisleTimeMax(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Whisle));
            if (isJumpAway(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Jump));
            if (in.health <= 0.0f) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Dead));
            stateTimer += dt;
            whistleTimer += dt;
            if (in.animPlaying && in.keyEvent == 4) transit(out, next);
            break;

        case P2FuefukiFsmState::Turn:
            if (in.turnComplete) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Walk));
            if (isWhisleTimeMax(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Whisle));
            if (isJumpAway(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Jump));
            if (in.health <= 0.0f) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Dead));
            stateTimer += dt;
            whistleTimer += dt;
            if (in.animPlaying && in.keyEvent == 4) transit(out, next);
            break;

        case P2FuefukiFsmState::Walk:
            if (!in.motionFinished) {
                if (in.arriveTarget)
                    requestFinish(out, static_cast<int>(squadActive() ? P2FuefukiFsmState::Turn
                                                                      : P2FuefukiFsmState::Wait));
            } else {
                out.zeroVelocity = true;
            }
            if (stateTimer > parms.walkStateCap)
                requestFinish(out, static_cast<int>(squadActive() ? P2FuefukiFsmState::Turn
                                                                  : P2FuefukiFsmState::Wait));
            if (isWhisleTimeMax(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Whisle));
            if (isJumpAway(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Jump));
            if (in.health <= 0.0f) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Dead));
            stateTimer += dt;
            whistleTimer += dt;
            if (in.animPlaying && in.keyEvent == 4) transit(out, next);
            break;

        case P2FuefukiFsmState::Whisle: {
            P2FuefukiCommand cast = interference.tickCast(boundEpoch, dt);
            if (cast.accepted) out.whistleRadius = cast.radiusModifier * parms.attackRadius;
            for (const P2FuefukiCandidate& cand : in.candidates) {
                P2FuefukiCommand r = interference.admit(boundEpoch, cand.id, cand.living, cand.callable,
                                                        cand.stuckToMouth, cand.alreadyTeki);
                if (r.claim) out.claimed.push_back(cand.id);
            }
            if (stateTimer > parms.castDuration)
                requestFinish(out, static_cast<int>(squadActive() ? P2FuefukiFsmState::Turn
                                                                  : P2FuefukiFsmState::Wait));
            if (isJumpAway(in)) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Jump));
            if (in.health <= 0.0f) requestFinish(out, static_cast<int>(P2FuefukiFsmState::Dead));
            stateTimer += dt;
            if (in.animPlaying && in.keyEvent == 4) transit(out, next);
            break;
        }

        case P2FuefukiFsmState::Struggle:
            if (in.health <= 0.0f || (in.stuckPikmin == 0 && stateTimer > 3.0f)
                || stateTimer > parms.struggleTime)
                out.requestFinishMotion = true;
            stateTimer += dt;
            whistleTimer += dt;
            if (in.animPlaying && in.keyEvent == 4)
                transit(out, static_cast<int>(in.health <= 0.0f ? P2FuefukiFsmState::Dead
                                                                : P2FuefukiFsmState::Jump));
            break;
        }

        out.state = state;
        return out;
    }
};
