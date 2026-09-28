#include "pc_p2_waterwraith_actor.h"

#include <cmath>

// State semantics transcribed from BlackManState.cpp / blackMan.cpp at research
// revision 632af937. Deliberate, documented simplifications:
// - Muse l63 (#503) ports the walkFunc autonomous driver around the retained-
//   assembly map-graph search: the actor owns target selection (captain chase
//   > pod approach > seam route fallback), the escape bands/timer/smoothing,
//   the pod motion choice, the route-find cadence counters (the seam answers
//   routeRefreshRequested) and turn damping. The two-step timer and speeds are
//   carried from the proper parms.
// - Clip playback and key-event effects are host-owned; the policy emits the
//   action request booleans (plus motion requests) and the key pulses drive
//   the source branches.
// - Timer-expiry branches (freeze/bend/tired) complete the motion in the tick
//   the counter passes the source length; a host `animEnd` pulse does the same.
// - The Tyre death order is split into explicit host pulses
//   (isTyreDead -> dismount, tyreDeathStart, tyreDeadAnimEnd) so the child
//   lifetime is inspectable; the source interleaves these with the roller FSM.

namespace {

constexpr float kPi = 3.14159265358979323846f;

} // namespace

P2WaterwraithActor::P2WaterwraithActor()
{
    reset(P2WaterwraithActorParms{});
}

P2WaterwraithActor::P2WaterwraithActor(const P2WaterwraithActorParms& parms)
{
    reset(parms);
}

void P2WaterwraithActor::reset(const P2WaterwraithActorParms& parms)
{
    mParms = parms;
    mRig   = P2WaterwraithRig(parms.properRotationSpeed);
    mAlive = mRig.birth();
    mPhase = parms.startPhase;

    mStateTimer     = 0.0f;
    mIntTimer       = 0;
    mPostFlickState = static_cast<int>(parms.startPhase);
    mStepPhase      = 0;
    mStepTimer      = 0;
    mBodyHealth     = parms.bodyMaxHealth;

    mPosition = P2WaterwraithVec3{};
    mVelocity = P2WaterwraithVec3{};
    mFacing   = 0.0f;
    mScale    = 1.0f;

    // Autonomous driver birth state (source onInit :177-188, :239-241):
    // escape axis from the start parm, timers zeroed, home/last-route at the
    // birth position. The seam places the actor before ticking; reset-from-
    // origin keeps the cadence counters well-defined either way.
    mEscapePhase            = parms.startEscapePhase;
    mEscapeTimer            = 0;
    mEscapeMoveSpeed        = 0.0f;
    mRouteFindTimer         = 0;
    mRouteFindCooldownTimer = 0;
    mHomePosition           = mPosition;
    mLastRoutePos           = mPosition;
    mSteerMode              = P2WWSTEER_Hold;
    mLastMotion             = P2WWMOTION_None;
    mRouteRefreshPending    = false;

    mWaypointCount = 0;
    mWaypointIndex = 0;

    mRollerPinched = false;
    mRollerZeroed  = false;
    mBodyPinched   = false;
    mBodyZeroed    = false;

    if (mPhase == P2BM_Fall) {
        mRig.beginFall();
    }
    pushRig();
    refreshHealthFlags();
}

void P2WaterwraithActor::reset()
{
    reset(P2WaterwraithActorParms{});
}

const char* P2WaterwraithActor::phaseName(P2BlackManPhase phase)
{
    switch (phase) {
    case P2BM_Walk: return "walk";
    case P2BM_Dead: return "dead";
    case P2BM_Freeze: return "freeze";
    case P2BM_Bend: return "bend";
    case P2BM_Escape: return "escape";
    case P2BM_Fall: return "fall";
    case P2BM_Flick: return "flick";
    case P2BM_Recover: return "recover";
    case P2BM_Tired: return "tired";
    }
    return "?";
}

const char* P2WaterwraithActor::steerModeName(P2WaterwraithSteerMode mode)
{
    switch (mode) {
    case P2WWSTEER_Hold: return "hold";
    case P2WWSTEER_Route: return "route";
    case P2WWSTEER_Chase: return "chase";
    case P2WWSTEER_PodSeek: return "podseek";
    }
    return "?";
}

const char* P2WaterwraithActor::motionName(P2WaterwraithMotion motion)
{
    switch (motion) {
    case P2WWMOTION_None: return "none";
    case P2WWMOTION_Wait: return "wait";
    case P2WWMOTION_Walk: return "walk";
    case P2WWMOTION_Run: return "run";
    case P2WWMOTION_Move: return "move";
    case P2WWMOTION_Through: return "through";
    }
    return "?";
}

int P2WaterwraithActor::setRoute(const P2WaterwraithWaypoint* waypoints, std::size_t count)
{
    if (count > static_cast<std::size_t>(kMaxWaypoints)) {
        count = static_cast<std::size_t>(kMaxWaypoints);
    }
    for (std::size_t i = 0; i < count; ++i) {
        mWaypoints[i] = waypoints[i];
    }
    mWaypointCount = static_cast<int>(count);
    mWaypointIndex = 0;
    return mWaypointCount;
}

void P2WaterwraithActor::clearRoute()
{
    mWaypointCount = 0;
    mWaypointIndex = 0;
}

P2WaterwraithVec3 P2WaterwraithActor::nextWaypoint() const
{
    if (mWaypointIndex < mWaypointCount) {
        return mWaypoints[mWaypointIndex].position;
    }
    return mPosition;
}

void P2WaterwraithActor::refreshHealthFlags()
{
    const float rollerHealth = mRig.tyreHealth();
    mRollerZeroed  = mRig.alive() && rollerHealth <= 0.0f;
    mRollerPinched = mRig.alive() && rollerHealth <= P2WaterwraithRig::kTyreMaxHealth * kPinchFraction;
    mBodyZeroed    = mBodyHealth <= 0.0f;
    mBodyPinched   = mBodyHealth <= mParms.bodyMaxHealth * kPinchFraction;
}

void P2WaterwraithActor::pushRig()
{
    if (mRig.alive()) {
        mRig.push(mPosition, mVelocity, mFacing, mScale);
    }
}

void P2WaterwraithActor::enter(P2BlackManPhase next, P2WaterwraithActorOutput& out)
{
    const P2BlackManPhase prev = mPhase;
    mPhase                     = next;
    mStateTimer                = 0.0f;
    mIntTimer                  = 0;
    out.entered                = true;
    out.state                  = next;

    if (prev == P2BM_Fall) {
        out.endFallConstraint = true; // StateFall::exec disables EB_NoInterrupt
    }

    switch (next) {
    case P2BM_Dead:
        out.startDeadMotion = true; // StateDead::init (blackManState.cpp:137)
        mVelocity           = P2WaterwraithVec3{};
        break;
    case P2BM_Escape:
        out.startEscapeMotion = true; // StateEscape::init getoff (:359)
        break;
    case P2BM_Fall:
        out.startFallMotion = true; // StateFall::init land (:427)
        mRig.beginFall();
        break;
    case P2BM_Bend:
        out.startBendMotion = true; // StateBend::init bend (:271)
        out.collisionStOn   = true;
        break;
    case P2BM_Recover:
        out.startRecoverMotion = true; // StateRecover::init recover (:482)
        break;
    case P2BM_Flick:
        out.startFlickMotion = true; // StateFlick::init flick (:558)
        break;
    case P2BM_Tired:
        out.startTiredMotion = true; // StateTired::init wait2 (:631)
        mVelocity            = P2WaterwraithVec3{};
        break;
    default:
        break;
    }
}

void P2WaterwraithActor::beginEscape(P2WaterwraithActorOutput& out)
{
    // Source `isTyreDead` (:4054) sets EB_Invulnerable and drops mTyre; the rig
    // models that as dismount(). The wraith animation is tyre_getoff.
    // Muse l63: the same source block arms the captain chase
    // (mEscapePhase = 2, :4060), previously missing here.
    out.dismountRequested = true;
    out.collisionStOff    = true;
    if (mRig.attachedToOwner()) {
        mRig.dismount();
    }
    mEscapePhase = 2;
    mEscapeTimer = 0;
    enter(P2BM_Escape, out);
}

void P2WaterwraithActor::updateLocomotion(float delta, P2WaterwraithActorOutput& out)
{
    mVelocity  = P2WaterwraithVec3{};
    mSteerMode = P2WWSTEER_Hold;
    if (mPhase != P2BM_Walk) {
        pushRig();
        return;
    }

    // Actor-owned target selection (muse l63, #503). Priority mirrors source
    // walkFunc: the escape chase (captain XZ, :873-929) outranks the pod
    // approach (:930-973), which outranks the seam-supplied route fallback.
    P2WaterwraithVec3 target = mPosition;
    bool haveTarget           = false;
    float moveSpeed           = currentSpeed();
    float turnRate            = mParms.rotationSpeed;
    float maxStep             = mParms.maxRotationStep;
    if (mEscapePhase == 2 && mCaptainValid) {
        target      = P2WaterwraithVec3{ mCaptainX, mPosition.y, mCaptainZ };
        haveTarget  = true;
        mSteerMode  = P2WWSTEER_Chase;
        moveSpeed   = mEscapeMoveSpeed; // smoothed chase speed (:926-927)
        turnRate    = mParms.escapeRotationSpeed; // :928-929
        maxStep     = mParms.maxEscapeRotationStep;
    } else if (mEscapePhase == 4 && mPodValid) {
        target      = P2WaterwraithVec3{ mPodX, mPosition.y, mPodZ };
        haveTarget  = true;
        mSteerMode  = P2WWSTEER_PodSeek;
        moveSpeed   = mParms.podMoveSpeed; // :968-969 (pathfinder leg omitted)
    } else if (mWaypointCount > 0 && mWaypointIndex < mWaypointCount) {
        target      = mWaypoints[mWaypointIndex].position;
        haveTarget  = true;
        mSteerMode  = P2WWSTEER_Route;
    }

    if (haveTarget) {
        const float dx   = target.x - mPosition.x;
        const float dz   = target.z - mPosition.z;
        const float dist = std::sqrt(dx * dx + dz * dz);
        bool arrived     = false;
        if (mSteerMode == P2WWSTEER_Route && dist <= mParms.waypointGoalRadius) {
            ++mWaypointIndex; // reached -> seam supplies the next waypoint
            arrived = true;
        }
        if (!arrived && dist > 0.0f) {
            const float prevFacing = mFacing;
            const float desired    = std::atan2(dx, dz); // source forward = (sin, cos)
            float diff             = desired - mFacing;
            while (diff > kPi) {
                diff -= 2.0f * kPi;
            }
            while (diff < -kPi) {
                diff += 2.0f * kPi;
            }
            float step = diff * turnRate;
            if (step > maxStep) {
                step = maxStep;
            }
            if (step < -maxStep) {
                step = -maxStep;
            }
            mFacing += step;

            mVelocity.x = std::sin(mFacing) * moveSpeed;
            mVelocity.z = std::cos(mFacing) * moveSpeed;
            // Turn damping (source :1024-1027, "SICK DRIFTS"): halve the
            // planar velocity while turning, before integrating so the stored
            // position matches the stored velocity.
            float angDist = desired - prevFacing;
            while (angDist > kPi) {
                angDist -= 2.0f * kPi;
            }
            while (angDist < -kPi) {
                angDist += 2.0f * kPi;
            }
            if (angDist > 0.25f || angDist < -0.25f || (mFacing - prevFacing) > 0.05f
                || (prevFacing - mFacing) > 0.05f) {
                mVelocity.x *= 0.5f;
                mVelocity.z *= 0.5f;
            }
            mPosition.x += mVelocity.x * delta;
            mPosition.z += mVelocity.z * delta;
        }
    }

    // Route-find cadence (source :997-1007): every 60 ticks near the last
    // route position, arm the 120-tick timer and ask the seam for the next
    // waypoint (the engine-free stand-in for findNextRoutePoint).
    if (mRouteFindTimer == 0) {
        ++mRouteFindCooldownTimer;
        if (mRouteFindCooldownTimer > 60) {
            const float hx = mPosition.x - mLastRoutePos.x;
            const float hz = mPosition.z - mLastRoutePos.z;
            if (hx * hx + hz * hz < 100.0f) { // within 10 (:1000)
                mRouteFindTimer           = 120;
                out.routeRefreshRequested = true;
                mRouteRefreshPending      = true;
            }
            mLastRoutePos           = mPosition;
            mRouteFindCooldownTimer = 0;
        }
    }
    pushRig();
}

void P2WaterwraithActor::observeDriver(const P2WaterwraithActorInput& in)
{
    mCaptainValid = in.captainValid;
    mCaptainX     = in.captainX;
    mCaptainZ     = in.captainZ;
    mPodValid     = in.podValid;
    mPodX         = in.podX;
    mPodZ         = in.podZ;
}

void P2WaterwraithActor::execWalk(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // Source walkFunc (:831): ride regen while on the tyres, then the trigger
    // order is isTyreFreeze -> Bend, health, isTyreDead -> Escape, flick.
    if (mRig.attachedToOwner()) {
        mBodyHealth += mRig.rideRegen(true);
        if (mBodyHealth > mParms.bodyMaxHealth) {
            mBodyHealth = mParms.bodyMaxHealth;
        }
    }

    if (in.isTyreFreeze) {
        out.collisionStOn = true;
        enter(P2BM_Bend, out);
        return;
    }
    if (mBodyHealth <= 0.0f) {
        enter(P2BM_Dead, out);
        return;
    }
    if (in.isTyreDead) {
        beginEscape(out);
        return;
    }
    if (in.isStartFlick) {
        mPostFlickState = P2BM_Walk;
        enter(P2BM_Flick, out);
        return;
    }
    if (in.tired) {
        enter(P2BM_Tired, out);
        return;
    }

    // Start-phase snap (source :955-964): while the roller is attached and the
    // escape axis drifted from the start parm, re-adopt it. Phase 4 stops the
    // pathfinder, so movement pauses for the pod branch below.
    if (mRig.attachedToOwner() && mEscapePhase != mParms.startEscapePhase) {
        mEscapePhase = mParms.startEscapePhase;
        if (mEscapePhase == 4) {
            mVelocity = P2WaterwraithVec3{};
        }
    }

    // Autonomous escape chase (source :873-929, muse l63 #503). Runs only with
    // a live captain observation; otherwise the route fallback steers below.
    // Distance bands select the clip-player motion request; the close band
    // runs the escape timer and winds down to Tired past ip05 (:909-911).
    if (mEscapePhase == 2 && mCaptainValid) {
        const float dx      = mCaptainX - mPosition.x;
        const float dz      = mCaptainZ - mPosition.z;
        const float sqrDist = dx * dx + dz * dz;
        float turnSpeed     = mParms.escapeSpeed;
        if (sqrDist > 800.0f * 800.0f) {
            mEscapeTimer       = 0;
            out.motionRequest  = P2WWMOTION_Wait; // WRAITHANIM_Wait
            turnSpeed          = 0.0f; // :918-920 stand still while far
            mLastMotion        = P2WWMOTION_Wait;
        } else if (sqrDist > 400.0f * 400.0f) {
            mEscapeTimer      = 0;
            out.motionRequest = P2WWMOTION_Walk; // WRAITHANIM_Walk
            turnSpeed         = mParms.walkingSpeed; // :922-924
            mLastMotion       = P2WWMOTION_Walk;
        } else {
            ++mEscapeTimer;
            out.motionRequest = P2WWMOTION_Run; // WRAITHANIM_Run
            mLastMotion       = P2WWMOTION_Run;
            if (mEscapeTimer > mParms.continuousEscapeTimerLength) {
                enter(P2BM_Tired, out);
                return;
            }
        }
        mEscapeMoveSpeed += (turnSpeed - mEscapeMoveSpeed) * 0.2f; // :926
    } else if (mEscapePhase != 2 && mPodValid) {
        // Pod motion choice (source :930-953): Through within 100, else Move.
        // Steering to the Pod itself happens in updateLocomotion for phase 4.
        const float dx      = mPodX - mPosition.x;
        const float dz      = mPodZ - mPosition.z;
        const float sqrDist = dx * dx + dz * dz;
        if (sqrDist < 100.0f * 100.0f) {
            out.motionRequest = P2WWMOTION_Through; // WRAITHANIM_Through
            mLastMotion       = P2WWMOTION_Through;
        } else {
            out.motionRequest = P2WWMOTION_Move; // WRAITHANIM_Move
            mLastMotion       = P2WWMOTION_Move;
        }
    }

    ++mStepTimer;
    if (mStepPhase == 0 && mStepTimer > mParms.twoStepTimerTicks) {
        mStepPhase = 1; // fp05 travel speed now applies
        mStepTimer = 0;
    }
}

void P2WaterwraithActor::execDead(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    if (in.keyEvent5) {
        out.releaseTreasure = true; // StateDead KEYEVENT_5 (:164)
    }
    if (in.animEnd) {
        out.killRequested = true; // StateDead KEYEVENT_END -> kill (:167)
        mAlive            = false;
    }
}

void P2WaterwraithActor::execFreeze(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateFreeze (:212): rollerless stun (kagebozu_bend2).
    ++mIntTimer;
    if (mBodyHealth <= 0.0f) {
        enter(P2BM_Dead, out);
        return;
    }
    if (in.isStartFlick) {
        mPostFlickState = P2BM_Freeze;
        enter(P2BM_Flick, out);
        return;
    }
    if (in.animEnd) {
        out.collisionStOff = true;
        enter(P2BM_Walk, out);
        return;
    }
    if (mIntTimer > mParms.freezeTimerLength) {
        out.finishMotionRequested = true;
        out.collisionStOff        = true;
        enter(P2BM_Walk, out);
    }
}

void P2WaterwraithActor::execBend(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateBend (:292): the wraith bends onto the frozen roller.
    if (mBodyHealth <= 0.0f) {
        enter(P2BM_Dead, out);
        return;
    }
    if (in.isTyreDead) {
        beginEscape(out);
        return;
    }
    if (in.isStartFlick) {
        mPostFlickState = P2BM_Bend;
        enter(P2BM_Flick, out);
        return;
    }
    if (in.animEnd) {
        out.collisionStOff = true;
        if (in.isTyreDead) {
            beginEscape(out);
        } else {
            enter(P2BM_Recover, out);
        }
        return;
    }
    ++mIntTimer;
    if (mIntTimer > mParms.dosinStopTimerLength) {
        out.finishMotionRequested = true;
        out.collisionStOff        = true;
        if (in.isTyreDead) {
            beginEscape(out);
        } else {
            enter(P2BM_Recover, out);
        }
    }
}

void P2WaterwraithActor::execEscape(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateEscape (:378): getoff, then Walk on the end key.
    if (in.keyEvent2) {
        out.flickRequested = true;
    }
    if (in.animEnd) {
        enter(P2BM_Walk, out);
    }
}

void P2WaterwraithActor::execFall(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateFall (:438): fanfare on KEYEVENT_2; ground contact -> Recover.
    if (in.keyEvent2) {
        out.fanfare = true;
    }
    if (in.isFallEnd || in.hardFall) {
        enter(P2BM_Recover, out);
    }
}

void P2WaterwraithActor::execFlick(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateFlick (:590): roller death overrides; otherwise return to the saved
    // pre-flick phase.
    if (in.isTyreDead) {
        beginEscape(out);
        return;
    }
    if (in.keyEvent2) {
        out.flickRequested = true;
    }
    if (in.animEnd) {
        enter(static_cast<P2BlackManPhase>(mPostFlickState), out);
    }
}

void P2WaterwraithActor::execRecover(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateRecover (:503): lift the roller back up; moveRestart on the end key.
    if (in.isTyreDead) {
        beginEscape(out);
        return;
    }
    if (in.keyEvent2) {
        out.flickRequested = true;
    }
    if (in.keyEvent4) {
        out.collisionStOff = true; // tyreDownEffect anchor (host effect)
    }
    if (in.keyEvent5 && in.finalFloor) {
        out.fanfare = true; // StateRecover KEYEVENT_5 final-floor flag (:527)
    }
    if (in.animEnd) {
        out.moveRestartRequested = true;
        mRig.moveRestart(); // Freeze -> Move; roll resumes
        enter(P2BM_Walk, out);
    }
}

void P2WaterwraithActor::execTired(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out)
{
    // StateTired (:642): post-escape wind-down (kagebozu_wait2).
    mVelocity = P2WaterwraithVec3{};
    if (in.animEnd) {
        out.flickRequested = true;
        enter(P2BM_Walk, out);
        return;
    }
    ++mIntTimer;
    if (mIntTimer > mParms.standStillTimerLength) {
        out.finishMotionRequested = true;
        out.flickRequested        = true;
        enter(P2BM_Walk, out);
    }
}

void P2WaterwraithActor::tick(const P2WaterwraithActorInput& in, P2WaterwraithActorOutput& out,
                              float delta)
{
    out       = P2WaterwraithActorOutput{};
    out.state = mPhase;
    if (!mAlive || !std::isfinite(delta) || !(delta > 0.0f)) {
        return;
    }

    // Route-find timer decrement (source doSimulation :454-458): per-frame in
    // every phase, clamped at zero. The Walk cadence evaluates it in
    // updateLocomotion.
    if (mRouteFindTimer > 0) {
        --mRouteFindTimer;
    }

    // Stash the live driver observations for the chase/pod branches.
    observeDriver(in);

    // Tyre-child lifecycle triggers (the actor owns the child).
    if (in.landFloorContact) {
        mRig.landFloorContact();
    }
    if (in.quakeFreeze) {
        mRig.quakeFreeze();
    }
    if (in.moveRestart) {
        mRig.moveRestart();
    }
    if (in.tyreDeathStart && mRig.alive() && mRig.tyreHealth() <= 0.0f
        && mRig.ownerInvulnerableSet() && mRig.tyrePhase() != P2TYRE_Dead) {
        if (mRig.beginDead()) {
            out.tyreDeathStarted = true;
        }
    }
    if (in.tyreDeadAnimEnd && mRig.alive() && mRig.tyrePhase() == P2TYRE_Dead) {
        mRig.finishDead();
        out.tyreRemoved = true;
    }

    // Earthquake stun only reaches the wraith itself while it is rollerless
    // (blackMan.cpp:727: with a child the quake is delegated to the Tyre).
    if (in.rollerlessQuake && !mRig.attachedToOwner()
        && (mPhase == P2BM_Walk || mPhase == P2BM_Tired)) {
        enter(P2BM_Freeze, out);
    }

    switch (mPhase) {
    case P2BM_Walk: execWalk(in, out); break;
    case P2BM_Dead: execDead(in, out); break;
    case P2BM_Freeze: execFreeze(in, out); break;
    case P2BM_Bend: execBend(in, out); break;
    case P2BM_Escape: execEscape(in, out); break;
    case P2BM_Fall: execFall(in, out); break;
    case P2BM_Flick: execFlick(in, out); break;
    case P2BM_Recover: execRecover(in, out); break;
    case P2BM_Tired: execTired(in, out); break;
    }

    updateLocomotion(delta, out);
    refreshHealthFlags();
    out.state = mPhase;
}

P2WaterwraithDamageResult p2_waterwraith_actor_apply_damage(P2WaterwraithActor& actor, float damage,
                                                             bool isPurple, bool* outDead)
{
    if (outDead) {
        *outDead = false;
    }
    if (!(damage > 0.0f) || !actor.mAlive) {
        return P2WWDMG_Ignored;
    }

    if (actor.mRig.attachedToOwner()) {
        // Riding roller: structurally Purple-only (the P1-host adaptation of the
        // source collision flick vs. reachable roller attack), and the roller's
        // own `damageable()` window (frozen riding / dismounted tyre_getoff).
        // Freeze/bend damage routes to the Tyre health.
        if (!isPurple) {
            return P2WWDMG_Ignored; // non-Purple cannot damage the riding roller
        }
        if (!actor.mRig.damageable()) {
            return P2WWDMG_Ignored; // riding/moving: the hit does nothing
        }
        bool dead = false;
        actor.mRig.applyDamage(damage, &dead);
        actor.refreshHealthFlags();
        if (outDead) {
            *outDead = dead;
        }
        return P2WWDMG_Roller;
    }

    // Dismounted wraith: the exposed body stays damageable once EB_Invulnerable
    // is set, and that flag persists past the Tyre child's finishDead/removal
    // (tyreState.cpp:152-153). Do NOT reuse rig.damageable() here: it is false
    // once the removed child is dead, which would wrongly close the body's
    // vulnerability window and make body death unreachable. In the source the
    // dismounted body takes damage from ANY Pikmin (no color gate in
    // `EnemyBase::damageCallBack` at blackMan.cpp:680); the Purple-only rule
    // applies to the riding roller only.
    if (!actor.mRig.ownerInvulnerableSet()) {
        return P2WWDMG_Ignored; // still riding (no dismount yet)
    }
    if (actor.mBodyHealth <= 0.0f) {
        return P2WWDMG_Ignored; // already zeroed: no further body hits count
    }
    actor.mBodyHealth -= damage;
    if (actor.mBodyHealth < 0.0f) {
        actor.mBodyHealth = 0.0f;
    }
    actor.refreshHealthFlags();
    if (outDead) {
        *outDead = actor.mBodyHealth <= 0.0f;
    }
    return P2WWDMG_Body;
}
