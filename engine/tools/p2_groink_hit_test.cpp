#include "pc_p2_groink_hit.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main() {
    P2GroinkHitInput in{{0,0,0},{0,0,10},2,10,25,false};
    P2GroinkHitCandidate c{{1,0,5},P2GroinkCandidateKind::Pikmin,true,false,4};
    auto hit=[&] { return p2_groink_classify_hit(in,c); };
    auto h=hit(); assert(h.valid&&h.insideSweep&&h.kind==P2GroinkHitKind::Bomb&&h.damage==25&&h.impulse.x==150&&h.impulse.y==100);
    c.kind=P2GroinkCandidateKind::Captain; assert(hit().impulse.y==0);
    c.kind=P2GroinkCandidateKind::Enemy; assert(hit().damage==100); c.owner=true; assert(hit().kind==P2GroinkHitKind::None); c.owner=false;
    c.kind=P2GroinkCandidateKind::OtherPiki; in.terminal=true; assert(hit().insideSweep&&hit().kind==P2GroinkHitKind::None);
    c.position={2,0,10}; h=hit(); assert(!h.insideSweep&&h.kind==P2GroinkHitKind::Wind&&h.impulse.x==135&&h.impulse.y==135);
    c.position={10,0,10}; assert(hit().kind==P2GroinkHitKind::None);
    c.kind=P2GroinkCandidateKind::Enemy; c.position={4,0,10}; assert(hit().kind==P2GroinkHitKind::None);
    c.position.x=3; assert(hit().kind==P2GroinkHitKind::Bomb); in.terminal=false; assert(hit().kind==P2GroinkHitKind::None);
    c.kind=P2GroinkCandidateKind::Pikmin; c.position={0,0,-2}; assert(!hit().insideSweep);
    c.position.z=12; assert(!hit().insideSweep); c.position.z=11; assert(hit().insideSweep);
    c.position={0,2,5}; assert(!hit().insideSweep); c.position.y=1; assert(hit().insideSweep);
    c.position={0,0,5}; h=hit(); assert(h.impulse.x==0&&h.impulse.z==0&&h.impulse.y==100);
    in.terminal=true; c.position={0,3,10}; h=hit(); assert(h.kind==P2GroinkHitKind::Wind&&h.impulse.x==0&&h.impulse.z==0&&h.impulse.y==127.5f);
    c.kind=P2GroinkCandidateKind::Captain; h=hit(); assert(h.kind==P2GroinkHitKind::Wind&&h.impulse.y==0);
    in.radius=0; in.terminalRadius=0; h=hit(); assert(h.valid&&!h.insideSweep&&h.kind==P2GroinkHitKind::None);
    in.terminalRadius=10; assert(hit().kind==P2GroinkHitKind::Wind);
    in.radius=2;
    c.alive=false; assert(hit().kind==P2GroinkHitKind::None); c.alive=true;
    in.end=in.start; in.terminal=true; assert(hit().kind==P2GroinkHitKind::None);
    in.end={0,10,0}; c.position={999,5,999}; assert(hit().insideSweep); // Source zero cross-product basis, not a capsule.
    in.damage=std::numeric_limits<float>::quiet_NaN(); assert(!hit().valid);
    puts("p2_groink_hit_test PASS");
}
