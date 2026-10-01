#include "pc_p2_groink_target.h"

namespace {
constexpr float pi = 3.14159265358979323846f;
bool bounded(float x) { return std::isfinite(x)&&std::fabs(x)<=1.0e6f; }
bool bounded(P2GroinkVec3 v) { return bounded(v.x)&&bounded(v.y)&&bounded(v.z); }
bool angle(float x) { return std::isfinite(x)&&std::fabs(x)<=2*pi; }
}

P2GroinkTargetResult p2_groink_select_target(const P2GroinkTargetQuery& q,
    const P2GroinkTargetCandidate* candidates, std::size_t count) {
    P2GroinkTargetResult out;
    const float norm=q.direction.x*q.direction.x+q.direction.z*q.direction.z;
    if (!bounded(q.muzzle)||!bounded(q.direction)||q.direction.y!=0||
        std::fabs(norm-1)>0.001f||!bounded(q.searchDistance)||q.searchDistance<0||
        count>4096||(count&&!candidates)) return out;
    // Reject a malformed snapshot atomically, including later candidates.
    for (std::size_t i=0;i<count;++i) if (!bounded(candidates[i].position)) return out;
    out.valid=true;
    for (std::size_t i=0;i<count;++i) {
        const auto& c=candidates[i];
        if (!c.alive||!(c.captain||c.pikmin)) continue;
        const P2GroinkVec3 p{c.position.x-q.muzzle.x,c.position.y-q.muzzle.y,c.position.z-q.muzzle.z};
        const float lateral=-q.direction.z*p.x+q.direction.x*p.z;
        const float forward=q.direction.x*p.x+q.direction.z*p.z;
        if (std::fabs(p.y)<200&&std::fabs(lateral)<25&&forward>1&&forward<q.searchDistance) {
            out.found=true; out.index=i; out.position=c.position; return out;
        }
    }
    return out;
}

P2GroinkAttackEndResult p2_groink_attack_end(const P2GroinkAttackEndInput& in) {
    P2GroinkAttackEndResult out;
    if (!bounded(in.health)||!std::isfinite(in.homeDistanceSquared)||in.homeDistanceSquared<0||
        in.homeDistanceSquared>4.0e12f||!bounded(in.territoryRadius)||in.territoryRadius<0||
        !bounded(in.homeRadius)||in.homeRadius<0||!angle(in.homeAngle)||!angle(in.pathAngle)||
        !angle(in.searchedAngle)||!bounded(in.maxAttackAngleDegrees)||in.maxAttackAngleDegrees<0) return out;
    out.valid=true;
    const auto home=std::fabs(in.homeAngle)<=pi/4 ? P2GroinkNextState::WalkHome : P2GroinkNextState::TurnHome;
    if (in.health<=0) out.state=P2GroinkNextState::Dead;
    else if (in.flick) out.state=P2GroinkNextState::Flick;
    else if (in.homeDistanceSquared>in.territoryRadius*in.territoryRadius) out.state=home;
    else {
        out.useAttackableQuery=true;
        if (in.attackable) out.state=P2GroinkNextState::Attack;
        else {
            out.useSearchedQuery=true;
            if (in.searchedTarget) out.state=std::fabs(in.searchedAngle)<=in.maxAttackAngleDegrees*(pi/180)
                ? P2GroinkNextState::Walk : P2GroinkNextState::Turn;
            else if (in.homeDistanceSquared<in.homeRadius*in.homeRadius)
                out.state=std::fabs(in.pathAngle)<=pi/4 ? P2GroinkNextState::WalkPath : P2GroinkNextState::TurnPath;
            else out.state=home;
        }
    }
    return out;
}
