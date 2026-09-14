#include "pc_p2_groink_hit.h"

namespace {
using V = P2GroinkVec3;
V sub(V a, V b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
V mul(V a, float b) { return {a.x*b,a.y*b,a.z*b}; }
float dot(V a, V b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
V cross(V a,V b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
V norm(V a) { const float n=std::sqrt(dot(a,a)); return n>0 ? mul(a,1/n) : a; }
bool finite(float x) { return std::isfinite(x) && std::fabs(x)<=1.0e6f; }
bool finite(V a) { return finite(a.x)&&finite(a.y)&&finite(a.z); }
}

P2GroinkHitCommand p2_groink_classify_hit(const P2GroinkHitInput& in,
                                        const P2GroinkHitCandidate& c) {
    P2GroinkHitCommand out;
    if (!finite(in.start)||!finite(in.end)||!finite(c.position)||
        !finite(in.radius)||in.radius<0||!finite(in.terminalRadius)||in.terminalRadius<0||
        !finite(in.damage)||in.damage<0||!finite(c.cellRadius)||c.cellRadius<0||
        c.kind<P2GroinkCandidateKind::Other||c.kind>P2GroinkCandidateKind::Enemy) return out;
    out.valid=true;
    const V delta=sub(in.end,in.start);
    const float distance=std::sqrt(dot(delta,delta));
    if (!c.alive || distance<=0) return out;
    const V forward=norm(delta), side=norm(cross({0,1,0},forward)), up=norm(cross(forward,side));
    const V sep=sub(c.position,in.start);
    const float lateral=dot(side,sep), vertical=dot(up,sep), along=dot(forward,sep);
    const bool piki=c.kind==P2GroinkCandidateKind::Pikmin||c.kind==P2GroinkCandidateKind::OtherPiki;
    const bool captain=c.kind==P2GroinkCandidateKind::Captain;
    const bool enemy=c.kind==P2GroinkCandidateKind::Enemy&&!c.owner;
    if (std::fabs(lateral)<in.radius && std::fabs(vertical)<in.radius &&
        along>-in.radius && along<distance+in.radius) {
        out.insideSweep=true;
        if (captain||c.kind==P2GroinkCandidateKind::Pikmin) {
            out.kind=P2GroinkHitKind::Bomb; out.damage=in.damage;
            out.impulse=mul(norm({lateral*side.x,0,lateral*side.z}),150);
            if (piki) out.impulse.y=100;
        } else if (enemy) { out.kind=P2GroinkHitKind::Bomb; out.damage=100; }
        return out; // Source clears check even when the species receives no interaction.
    }
    if (!in.terminal) return out;
    V radial=sub(c.position,in.end);
    const float d2=dot(radial,radial);
    if ((captain||piki) && d2<in.terminalRadius*in.terminalRadius) {
        const float factor=std::sqrt(d2)/in.terminalRadius;
        const float magnitude=150*(1-factor)+75*factor;
        radial.y=0; radial=norm(radial);
        if (piki) radial.y=1;
        out.kind=P2GroinkHitKind::Wind; out.impulse=mul(radial,magnitude);
    } else if (enemy && d2<c.cellRadius*c.cellRadius) {
        out.kind=P2GroinkHitKind::Bomb; out.damage=100;
    }
    return out;
}
