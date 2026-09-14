#include "pc_p2_groink_attack.h"

P2GroinkAttackCommands P2GroinkAttack::step(const P2GroinkAttackInput& in, float delta) {
    P2GroinkAttackCommands out;
    if (!mActive) return out;
    if (!in.activeTick) { out.valid = true; return out; }
    if (!std::isfinite(delta) || std::fabs(delta-P2GroinkPolicy::kSourceDelta)>1e-6f
        || !std::isfinite(in.health)
        || unsigned(in.event)>unsigned(P2GroinkAttackEvent::End)) return out;
    out.valid = true;
    auto add = [&](P2GroinkAttackCommand command) { out.items[out.count++] = command; };
    bool stopped = in.motionStopped;
    bool finishing = in.motionFinishing;
    // Source has two identical lock+positive-wait branches for aiming/return.
    if (stopped && in.gunLocked && mWait>0) {
        mWait = 0; stopped = false; add(P2GroinkAttackCommand::ResumeMotion);
    }
    if (in.gunRotating) add(P2GroinkAttackCommand::RefreshTarget);
    mWait += delta;
    if (in.health<=0 || in.flick) {
        if (stopped) { stopped = false; add(P2GroinkAttackCommand::ResumeMotion); }
        finishing = true; add(P2GroinkAttackCommand::FinishMotion);
    }
    switch (in.event) {
    case P2GroinkAttackEvent::Charge:
        mWait = 0;
        add(P2GroinkAttackCommand::StopMotion);
        add(P2GroinkAttackCommand::StartAim);
        add(P2GroinkAttackCommand::StartCharge);
        break;
    case P2GroinkAttackEvent::Smoke:
        add(P2GroinkAttackCommand::LargeSmoke);
        add(P2GroinkAttackCommand::FinishCharge);
        break;
    case P2GroinkAttackEvent::Fire:
        // Keep source OR: a living flick-interrupted actor may still emit.
        if (!finishing || !(in.health<=0)) add(P2GroinkAttackCommand::EmitVolley);
        break;
    case P2GroinkAttackEvent::Return:
        mWait = 0;
        add(P2GroinkAttackCommand::StopMotion);
        add(P2GroinkAttackCommand::ReturnGun);
        break;
    case P2GroinkAttackEvent::End:
        add(in.health<=0 ? P2GroinkAttackCommand::ExitDead : in.flick
            ? P2GroinkAttackCommand::ExitFlick : P2GroinkAttackCommand::ResolveNextState);
        mActive = false;
        break;
    case P2GroinkAttackEvent::None: break;
    }
    return out;
}

bool P2GroinkGunRotation::returnStep(float angle, float& next, bool& done) {
    if (!std::isfinite(angle)) return false;
    constexpr float tau = 6.2831853071795864769f;
    // Reachable source angles lie within a single turn. Do not silently wrap
    // malformed host values into an apparently valid gun pose.
    if (angle < -tau || angle > tau) return false;
    float target = 0;
    if (target>=angle) {
        if (tau-(target-angle)<target-angle) target-=tau;
    } else if (tau-(angle-target)<angle-target) target+=tau;
    next = std::fabs(angle-target)<0.025f ? target : angle<target ? angle+0.025f : angle-0.025f;
    done = std::fabs(next-target)<0.01f;
    return true;
}

bool P2GroinkGunRotation::update(const P2GroinkVec3& muzzle, const P2GroinkVec3& target,
                                float search, float radius, float delta) {
    if (!std::isfinite(delta) || std::fabs(delta-P2GroinkPolicy::kSourceDelta)>1e-6f) return false;
    if (!mRotating) return true;
    if (mFinished) {
        float next; bool done;
        if (!returnStep(mAngle,next,done)) return false;
        mAngle = next;
        if (done) { mRotating = false; mLocked = true; }
    } else {
        const auto result = P2GroinkPolicy::aim(muzzle,target,search,radius,delta,mAngle);
        if (!result.valid) return false;
        mAngle = result.angle; mSpeed = result.shellSpeed;
        // Source lock is latched until start/finish, not cleared by a new target.
        if (result.locked) mLocked = true;
    }
    return true;
}
