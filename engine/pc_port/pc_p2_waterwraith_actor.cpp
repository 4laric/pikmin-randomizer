#include "pc_p2_waterwraith_actor.h"

#include <cmath>

// State semantics transcribed from BlackManState.cpp / blackMan.cpp at research
// revision 632af937. Deliberate, documented simplifications:
// - Locomotion is host-driven (route waypoints), not the retained-assembly
//   `walkFunc`/`findNextRoutePoint` pathfinder. The two-step timer and speeds
//   are carried from the proper parms.
// - Clip playback and key-event effects are host-owned; the policy emits the
//   action request booleans and the key pulses drive the source branches.
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
    out.dismountRequested = true;
    out.collisionStOff    = true;
    if (mRig.attachedToOwner()) {
        mRig.dismount();
    }
    enter(P2BM_Escape, out);
}

void P2WaterwraithActor::updateLocomotion(float delta)
{
    mVelocity = P2WaterwraithVec3{};
    if (mPhase == P2BM_Walk && mWaypointCount > 0 && mWaypointIndex < mWaypointCount) {
        const P2WaterwraithVec3 target = mWaypoints[mWaypointIndex].position;
        const float dx                 = target.x - mPosition.x;
        const float dz                 = target.z - mPosition.z;
        const float dist               = std::sqrt(dx * dx + dz * dz);
        if (dist <= mParms.waypointGoalRadius) {
            ++mWaypointIndex; // reached -> host supplies/finds the next waypoint
        } else {
            const float desired = std::atan2(dx, dz); // source forward = (sin, cos)
            float diff          = desired - mFacing;
            while (diff > kPi) {
                diff -= 2.0f * kPi;
            }
            while (diff < -kPi) {
                diff += 2.0f * kPi;
            }
            float step = diff * mParms.rotationSpeed;
            if (step > mParms.maxRotationStep) {
                step = mParms.maxRotationStep;
            }
            if (step < -mParms.maxRotationStep) {
                step = -mParms.maxRotationStep;
            }
            mFacing += step;

            const float speed = currentSpeed();
            mVelocity.x       = std::sin(mFacing) * speed;
            mVelocity.z       = std::cos(mFacing) * speed;
            mPosition.x += mVelocity.x * delta;
            mPosition.z += mVelocity.z * delta;
        }
    }
    pushRig();
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

    updateLocomotion(delta);
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
