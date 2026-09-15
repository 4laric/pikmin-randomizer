#pragma once

// Waterwraith (99 BlackMan) phase machine for lane 31 (#443 / parent #175),
// built on the dependent-roller ownership/vulnerability policy
// (pc_p2_waterwraith, `P2WaterwraithRig`). Engine-free: no actor, map, receiver,
// sound, effect or strike dependency. The host feeds per-tick trigger booleans
// and a route; the policy owns the nine source phases and the single Tyre child.
//
// Source: US GPVE01 rev 0, research rev 632af937 (src/plugProjectMorimuraU/
// blackManState.cpp, blackMan.cpp; include/Game/Entities/BlackMan.h). State IDs
// are BlackMan.h:367-378. Transitions below cite the source state machine.
//
// Phase machine (host-fed triggers name the source predicate):
//   Walk   -> Bend    if isTyreFreeze          (walkFunc -> isTyreFreeze, :837)
//   Walk   -> Dead    if body health <= 0      (StateWalk::exec :73)
//   Walk   -> Escape  if isTyreDead            (:78)
//   Walk   -> Flick   if isStartFlick          (:83, postFlickState = Walk)
//   Walk   -> Tired   if escapePhase wind-down (host: continuous escape timer)
//   Walk   -> Freeze  if rollerless quake      (earthquakeCallBack :727)
//   Freeze -> Dead / Flick / Walk              (StateFreeze :212)
//   Bend   -> Dead / Escape / Flick / Recover  (StateBend :292)
//   Flick  -> postFlickState (Walk/Freeze/Bend) or Escape (StateFlick :590)
//   Recover-> Escape / Walk (moveRestart)      (StateRecover :503)
//   Escape -> Walk                             (StateEscape :378)
//   Fall   -> Recover                          (StateFall :438, isFallEnd)
//   Tired  -> Walk                             (StateTired :642)
//   Dead: KEYEVENT_5 releases the held treasure, KEYEVENT_END kills (:152).
//
// Retained-assembly caveat: the source `walkFunc`/`findNextRoutePoint`/joint
// callbacks sit beside retained PowerPC assembly and their evaluation order is
// inferred (assets audit sec.0). This policy therefore does NOT port the
// retained-assembly pathfinding; locomotion is a HOST-DRIVEN route (the host
// supplies/updates waypoints) advanced at the source retail travel speed fp05
// = 120 with a documented two-step timer (ip01 retail 0, so the first step is
// effectively instantaneous). No claim of natural-Map navigation is made.
//
// Damage model (structural, not a receiver): only Purple hits are accepted, and
// while the roller is attached only when `P2WaterwraithRig::damageable()` is
// true (frozen); after dismount the body accepts hits until `ownerInvulnerableSet()`. While riding/moving the hit is ignored. Damage while
// the child is still attached routes to the Tyre health (source freeze/bend
// routes to `mTyre`, blackMan.cpp:672-681); after dismount it routes to the
// wraith body health (general fp00 = 1500). This expresses the Purple-only
// vulnerability without a gameplay receiver adapter (lane 10/11 owns that).

#include "pc_p2_waterwraith.h"

#include <cstddef>

// Routing outcome of `p2_waterwraith_actor_apply_damage`.
enum P2WaterwraithDamageResult {
    P2WWDMG_Ignored = 0, // non-Purple, non-positive, dead actor, or not damageable
    P2WWDMG_Roller  = 1, // accepted while the child roller is attached + frozen
    P2WWDMG_Body    = 2, // accepted after dismount, applied to the wraith body
};

// One host-supplied route waypoint (XZ plane; Y is carried through untouched).
struct P2WaterwraithWaypoint {
    P2WaterwraithVec3 position{};
};

// Build-time defaults mirror the source headers; disc/retail values are noted.
struct P2WaterwraithActorParms {
    float bodyMaxHealth = 1500.0f;    // BlackMan general fp00 (retail 1500)
    float travelSpeed = 120.0f;       // proper fp05 (retail 120)
    float walkSpeed = 50.0f;          // proper fp11 (retail 50; pre-two-step crawl)
    float rotationSpeed = 0.04f;      // proper fp06 (retail 0.04)
    float maxRotationStep = 3.0f;     // proper fp07 (retail 3.0)
    float waypointGoalRadius = 50.0f; // Parms::mWaypointGoalRadius
    int twoStepTimerTicks = 0;        // proper ip01 (retail 0; header default 300)
    int dosinStopTimerLength = 200;   // proper ip03
    int freezeTimerLength = 200;      // proper ip04
    int continuousEscapeTimerLength = 200; // proper ip05
    int standStillTimerLength = 200;  // proper ip06
    float properRotationSpeed = 25.0f;     // Tyre fp01 (retail 25.0)
    P2BlackManPhase startPhase = P2BM_Fall; // onInit: Fall unless cave y_01 (:168)
};

// Per-tick host inputs. All triggers are one-tick pulses unless noted.
struct P2WaterwraithActorInput {
    // Wraith-facing source triggers.
    bool isTyreFreeze = false;    // roller reports Freeze -> Bend (walkFunc)
    bool isStartFlick = false;    // EnemyFunc::isStartFlick -> Flick
    bool isTyreDead = false;      // roller health <= 0 + anim end -> Escape
    bool isFallEnd = false;       // Fall: ground/pellet contact -> Recover
    bool hardFall = false;        // Fall: hard-constraint termination -> Recover
    bool rollerlessQuake = false; // Walk/Tired with no child -> Freeze stun
    bool tired = false;           // Walk escape-phase wind-down -> Tired
    // Tyre-child triggers (the actor owns the child and applies these to the rig).
    bool landFloorContact = false; // Tyre Land -> Freeze
    bool quakeFreeze = false;      // Tyre Move -> Freeze
    bool moveRestart = false;      // Tyre Freeze -> Move
    bool tyreDeathStart = false;   // begin tyre_getoff (requires zero HP + dismount)
    bool tyreDeadAnimEnd = false;  // tyre_getoff end -> remove the child
    // Animation / effect key pulses (host owns the clips and effects).
    bool keyEvent2 = false;
    bool keyEvent4 = false;
    bool keyEvent5 = false; // Dead: release held treasure
    bool animEnd = false;   // current clip end key
    bool finalFloor = false; // Recover KEYEVENT_5 fanfare anchor
};

struct P2WaterwraithActorOutput {
    P2BlackManPhase state = P2BM_Walk;
    bool entered = false;      // a transition happened this tick
    // Host action requests.
    bool startDeadMotion = false;
    bool startEscapeMotion = false; // getoff
    bool startFallMotion = false;
    bool startBendMotion = false;
    bool startRecoverMotion = false;
    bool startFlickMotion = false;
    bool startTiredMotion = false;
    bool endFallConstraint = false; // leave Fall: drop the hard constraint
    bool collisionStOn = false;
    bool collisionStOff = false;
    bool flickRequested = false;
    bool dismountRequested = false;
    bool tyreDeathStarted = false;
    bool tyreRemoved = false;
    bool releaseTreasure = false; // Dead KEYEVENT_5
    bool killRequested = false;   // Dead KEYEVENT_END
    bool moveRestartRequested = false;
    bool finishMotionRequested = false;
    bool fanfare = false; // Fall KEYEVENT_2 / Recover KEYEVENT_5 on final floor
};

class P2WaterwraithActor {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;
    static constexpr int kMaxWaypoints = 16;
    // Lane-level gauge marker (no source constant): pinch below 1/4 of maximum.
    static constexpr float kPinchFraction = 0.25f;

    P2WaterwraithActor();
    explicit P2WaterwraithActor(const P2WaterwraithActorParms& parms);

    // Births the single Tyre child and enters `startPhase` (source onInit).
    void reset(const P2WaterwraithActorParms& parms);
    void reset();

    bool alive() const { return mAlive; }
    P2BlackManPhase phase() const { return mPhase; }
    static const char* phaseName(P2BlackManPhase phase);
    const char* phaseName() const { return phaseName(mPhase); }

    // The actor owns the child; the host may read (not own) the rig.
    P2WaterwraithRig& rig() { return mRig; }
    const P2WaterwraithRig& rig() const { return mRig; }

    float bodyHealth() const { return mBodyHealth; }
    float bodyMaxHealth() const { return mParms.bodyMaxHealth; }
    bool bodyPinched() const { return mBodyPinched; }
    bool bodyZeroed() const { return mBodyZeroed; }
    bool rollerPinched() const { return mRollerPinched; }
    bool rollerZeroed() const { return mRollerZeroed; }
    // Combined gauge marker for whichever pool is currently exposed.
    bool pinched() const { return mRollerPinched || mBodyPinched; }
    bool zeroed() const { return mRollerZeroed || mBodyZeroed; }

    // Host-driven route (retained-assembly pathfinding is intentionally omitted).
    int setRoute(const P2WaterwraithWaypoint* waypoints, std::size_t count);
    void clearRoute();
    int waypointCount() const { return mWaypointCount; }
    int waypointIndex() const { return mWaypointIndex; }
    bool reachedRouteEnd() const { return mWaypointCount > 0 && mWaypointIndex >= mWaypointCount; }
    P2WaterwraithVec3 nextWaypoint() const;

    // Two-step locomotion state (source walkFunc :861-871).
    float currentSpeed() const { return mStepPhase == 0 ? mParms.walkSpeed : mParms.travelSpeed; }
    bool twoStepActive() const { return mStepPhase != 0; }
    int stepTimer() const { return mStepTimer; }

    P2WaterwraithVec3 position() const { return mPosition; }
    P2WaterwraithVec3 velocity() const { return mVelocity; }
    float facing() const { return mFacing; }

    // One 30 Hz policy tick. Advances locomotion and pushes the child position,
    // velocity and facing so the rig derives the roll angle.
    void tick(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out,
              float delta = kSourceDelta);

private:
    friend P2WaterwraithDamageResult p2_waterwraith_actor_apply_damage(P2WaterwraithActor& actor,
                                                                       float damage, bool isPurple,
                                                                       bool* outDead);

    void enter(P2BlackManPhase next, P2WaterwraithActorOutput& out);
    void beginEscape(P2WaterwraithActorOutput& out);
    void updateLocomotion(float delta);
    void pushRig();
    void refreshHealthFlags();

    void execWalk(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execDead(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execFreeze(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execBend(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execEscape(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execFall(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execFlick(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execRecover(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);
    void execTired(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out);

    P2WaterwraithActorParms mParms;
    P2WaterwraithRig mRig;
    P2BlackManPhase mPhase = P2BM_Walk;
    bool mAlive = false;
    float mBodyHealth = 0.0f;
    float mStateTimer = 0.0f;
    int mIntTimer = 0;
    int mPostFlickState = 0; // P2BlackManPhase to resume after Flick
    int mStepPhase = 0;
    int mStepTimer = 0;
    bool mRollerPinched = false;
    bool mRollerZeroed = false;
    bool mBodyPinched = false;
    bool mBodyZeroed = false;

    P2WaterwraithVec3 mPosition{};
    P2WaterwraithVec3 mVelocity{};
    float mFacing = 0.0f;
    float mScale = 1.0f;

    P2WaterwraithWaypoint mWaypoints[kMaxWaypoints];
    int mWaypointCount = 0;
    int mWaypointIndex = 0;
};

// Routes a hit through the per-target vulnerability gates. Only Purple damage
// is accepted (structural vulnerability). While the child is attached the
// damage goes to the Tyre health, gated on the roller's `damageable()`; after
// dismount it goes to the wraith body health, gated on the dismount flag
// (EB_Invulnerable) which persists past child removal so the exposed body stays
// vulnerable until the wraith itself dies. `outDead` (optional) reports the
// underlying target's death gate (roller death still requires the dismounted
// EB_Invulnerable flag; body death is HP <= 0).
P2WaterwraithDamageResult p2_waterwraith_actor_apply_damage(P2WaterwraithActor& actor,
                                                             float damage, bool isPurple,
                                                             bool* outDead = nullptr);
