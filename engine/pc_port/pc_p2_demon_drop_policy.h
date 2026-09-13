#pragma once
#include <cmath>
#include <cstdint>

// Narrow P2 FallMeck -> KokeDamage policy, not a P1 state implementation.
enum class P2DemonDropPhase { Idle, Falling, Knockdown, Lay, GetUp };
struct P2DemonDropCommand {
    bool accepted=false;
    bool startFall=false, startKnockdown=false, startGetUp=false, resume=false;
    bool impactZeroDamage=false, deliverDamage=false, nudge=false;
    float damage=0, actualY=0, targetY=0;
};
class P2DemonDropPolicy {
    std::uint64_t generation=0;
    P2DemonDropPhase state=P2DemonDropPhase::Idle;
    float pendingDamage=0, recovery=0;
    bool current(std::uint64_t id) const { return id && id==generation && state!=P2DemonDropPhase::Idle; }
public:
    P2DemonDropPhase phase() const { return state; }
    void cancel() { state=P2DemonDropPhase::Idle; pendingDamage=0; recovery=0; }
    P2DemonDropCommand begin(std::uint64_t id,float damage,float retailSpeed) {
        P2DemonDropCommand out;
        if(state!=P2DemonDropPhase::Idle || !id || id<=generation || !std::isfinite(damage) ||
           !std::isfinite(retailSpeed) || retailSpeed<0) return out;
        generation=id; pendingDamage=damage; state=P2DemonDropPhase::Falling;
        out.accepted=true; out.startFall=true;
        out.actualY=damage>0 ? -400.f : -100.f;
        out.targetY=-retailSpeed;
        return out;
    }
    P2DemonDropCommand bounce(std::uint64_t id) {
        P2DemonDropCommand out;
        if(!current(id)||state!=P2DemonDropPhase::Falling) return out;
        out.accepted=true;
        if(pendingDamage>0) {
            state=P2DemonDropPhase::Knockdown;
            out.impactZeroDamage=true; out.startKnockdown=true;
            recovery=1.f;
        } else { cancel(); out.nudge=true; out.resume=true; }
        return out;
    }
    // The host binds the event to the animation phase that emitted it.
    P2DemonDropCommand animationEnd(std::uint64_t id,P2DemonDropPhase emittedBy) {
        P2DemonDropCommand out;
        if(!current(id)||state!=emittedBy) return out;
        if(state==P2DemonDropPhase::Knockdown) {
            state=P2DemonDropPhase::Lay;
            out.accepted=true; out.deliverDamage=true; out.damage=pendingDamage;
            pendingDamage=0; // Commit before host damage callbacks/reentrancy.
        } else if(state==P2DemonDropPhase::GetUp) {
            cancel(); out.accepted=true; out.resume=true;
        }
        return out;
    }
    P2DemonDropCommand tick(std::uint64_t id,float delta) {
        P2DemonDropCommand out;
        if(!current(id)||state!=P2DemonDropPhase::Lay||!std::isfinite(delta)||delta<0) return out;
        out.accepted=true; recovery-=delta;
        if(recovery<=0) { state=P2DemonDropPhase::GetUp; out.startGetUp=true; }
        return out;
    }
};
