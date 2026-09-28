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
// Retained-assembly caveat: the source `findNextRoutePoint` map-graph search
// beside retained PowerPC assembly is not ported; the map-graph leg itself
// stays a seam-supplied waypoint list. Muse l63 (#503) ports everything else
// around it: the actor owns target selection (captain chase > pod approach >
// route fallback), the escape distance bands/timer/smoothing, the pod motion
// choice, the route-find cadence counters (the seam answers
// routeRefreshRequested with the next waypoint) and turn damping. No claim of
// natural-Map graph navigation is made.
//
// Damage model (structural, not a receiver). The RIDING ROLLER accepts only
// Purple hits, and only while `P2WaterwraithRig::damageable()` is true (frozen);
// while riding/moving the hit is ignored. After dismount the exposed BODY
// accepts hits from ANY Pikmin until `ownerInvulnerableSet()` fades (source
// `EnemyBase::damageCallBack`, blackMan.cpp:672-681 / :680, has no color gate).
// Damage while the child is still attached routes to the Tyre health; after
// dismount it routes to the wraith body health (general fp00 = 1500). This is
// the structural expression of the source vulnerability window without a
// gameplay receiver adapter (lane 10/11 owns the shared production route).

#include "pc_p2_waterwraith.h"

#include <cstddef>

// Routing outcome of `p2_waterwraith_actor_apply_damage`.
enum P2WaterwraithDamageResult {
    P2WWDMG_Ignored = 0, // non-positive, dead actor, or not in the target's window
    P2WWDMG_Roller  = 1, // accepted while the child roller is attached + frozen (Purple-only)
    P2WWDMG_Body    = 2, // accepted after dismount, applied to the wraith body (any Pikmin)
};

// One host-supplied route waypoint (XZ plane; Y is carried through untouched).
struct P2WaterwraithWaypoint {
    P2WaterwraithVec3 position{};
};

// Actor-owned steering target selection (muse l63, #503). The actor picks its
// own target per source walkFunc (blackMan.cpp:831-1027, research 632af937):
//   Chase   : escapePhase 2 steers to the live captain XZ (:873-929).
//   PodSeek : escapePhase 4 steers to the Pod XZ (:930-973).
//   Route   : last-resort fallback to the host-supplied waypoint list.
//   Hold    : no valid target (stand still).
enum P2WaterwraithSteerMode {
    P2WWSTEER_Hold = 0,
    P2WWSTEER_Route = 1,
    P2WWSTEER_Chase = 2,
    P2WWSTEER_PodSeek = 3,
};

// Motion request for the host clip player (source startMotion analogues in
// walkFunc: WRAITHANIM_Wait/Walk/Run/Move/Through). The policy emits one per
// tick; the host player deduplicates. None = no request this tick.
enum P2WaterwraithMotion {
    P2WWMOTION_None = 0,
    P2WWMOTION_Wait = 1,
    P2WWMOTION_Walk = 2,
    P2WWMOTION_Run = 3,
    P2WWMOTION_Move = 4,
    P2WWMOTION_Through = 5,
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
    // Autonomous driver parms (muse l63, #503; header defaults from BlackMan.h).
    int startEscapePhase = 1;        // C_PARMS mStartPhase (retail 1; 2 = chase, 4 = pod-seek)
    float escapeSpeed = 10.0f;       // proper fp02 (retail 10)
    float escapeRotationSpeed = 0.1f;    // proper fp03 (retail 0.1)
    float maxEscapeRotationStep = 10.0f; // proper fp04 (retail 10)
    float walkingSpeed = 10.0f;      // proper fp11 (retail 10)
    float podMoveSpeed = 10.0f;      // proper fp01 (retail 10)
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
    // Autonomous driver feeds (muse l63, #503). Positions are XZ plane values
    // read from live engine state by the encounter each tick (captain = active
    // Navi, the source walkFunc chase target :874); the actor owns all target
    // selection, bands, timers and smoothing. podValid stays false on this
    // host (no live Pod position exists) so pod-seek remains engine-free
    // verified until a Pod position source lands.
    bool captainValid = false; // live active-captain XZ available
    float captainX = 0.0f;
    float captainZ = 0.0f;
    bool podValid = false; // live Pod XZ available (false on this host)
    float podX = 0.0f;
    float podZ = 0.0f;
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
    // Autonomous driver outputs (muse l63, #503).
    P2WaterwraithMotion motionRequest = P2WWMOTION_None; // clip-player request
    bool routeRefreshRequested = false; // route cadence fired: source would
        // call findNextRoutePoint (:1001); the seam supplies the next waypoint
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

    // Autonomous driver state (muse l63, #503; source walkFunc :873-1007).
    int escapePhase() const { return mEscapePhase; }
    P2WaterwraithSteerMode steerMode() const { return mSteerMode; }
    P2WaterwraithMotion lastMotion() const { return mLastMotion; }
    static const char* steerModeName(P2WaterwraithSteerMode mode);
    static const char* motionName(P2WaterwraithMotion motion);
    int escapeTimer() const { return mEscapeTimer; }
    float escapeMoveSpeed() const { return mEscapeMoveSpeed; }
    // Sticky route-refresh edge for the seam marker (set when the cadence
    // fires alongside out.routeRefreshRequested; cleared by ack).
    bool routeRefreshPending() const { return mRouteRefreshPending; }
    void ackRouteRefresh() { mRouteRefreshPending = false; }

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
    void updateLocomotion(float delta, P2WaterwraithActorOutput& out);
    void observeDriver(const P2WaterwraithActorInput& in);
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
    // Autonomous driver (muse l63, #503): source mEscapePhase axis (distinct
    // from the FSM phase), escape chase timer/speed (:873-929), route-find
    // cadence (:997-1007) and actor-owned target selection.
    int mEscapePhase = 1;
    int mEscapeTimer = 0;
    float mEscapeMoveSpeed = 0.0f;
    int mRouteFindTimer = 0;
    int mRouteFindCooldownTimer = 0;
    P2WaterwraithVec3 mHomePosition{};
    P2WaterwraithVec3 mLastRoutePos{};
    P2WaterwraithSteerMode mSteerMode = P2WWSTEER_Hold;
    P2WaterwraithMotion mLastMotion = P2WWMOTION_None;
    bool mRouteRefreshPending = false;
    // Latest live driver observations stashed from the tick input (captain =
    // active Navi XZ, pod = Pod XZ) for the chase/pod branches.
    bool mCaptainValid = false;
    float mCaptainX = 0.0f;
    float mCaptainZ = 0.0f;
    bool mPodValid = false;
    float mPodX = 0.0f;
    float mPodZ = 0.0f;
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
