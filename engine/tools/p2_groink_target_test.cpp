#include "pc_p2_groink_target.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <initializer_list>
int main() {
    P2GroinkTargetQuery q{{10,20,30},{0,0,1},250};
    P2GroinkTargetCandidate c[]={{{10,20,200},true,true,false},{{10,20,40},true,false,true}};
    auto pick=[&]{return p2_groink_select_target(q,c,2);};
    assert(pick().found&&pick().index==0); // First cell candidate, not nearest.
    c[0].alive=false; assert(pick().index==1); c[0].alive=true;
    c[0].captain=false; assert(pick().index==1); c[0].captain=true;
    for (auto p : {P2GroinkVec3{35,20,100},{10,220,100},{10,20,31},{10,20,280}}) {
        c[0].position=p; assert(pick().index==1);
    }
    c[0].position={34,219,279}; assert(pick().index==0);
    q.direction={1,0,0}; c[0].position={100,20,30}; assert(pick().found&&pick().index==0);
    c[1].position.x=std::numeric_limits<float>::quiet_NaN(); assert(!pick().valid);
    assert(p2_groink_select_target(q,nullptr,0).valid);
    assert(!p2_groink_select_target(q,nullptr,1).valid);
    P2GroinkAttackEndInput in; in.territoryRadius=100; in.homeRadius=10; in.maxAttackAngleDegrees=45;
    auto end=[&]{return p2_groink_attack_end(in);};
    using S=P2GroinkNextState;
    in.health=0; in.flick=true; in.attackable=true;
    assert(end().state==S::Dead&&!end().useAttackableQuery);
    in.health=1; assert(end().state==S::Flick); in.flick=false;
    in.homeDistanceSquared=10001; assert(end().state==S::WalkHome&&!end().useAttackableQuery);
    in.homeAngle=1; assert(end().state==S::TurnHome);
    in.homeDistanceSquared=10000; assert(end().state==S::Attack&&end().useAttackableQuery&&!end().useSearchedQuery);
    in.attackable=false; in.searchedTarget=true; in.searchedAngle=0;
    assert(end().state==S::Walk&&end().useSearchedQuery); in.searchedAngle=1; assert(end().state==S::Turn);
    in.searchedAngle=in.maxAttackAngleDegrees*(3.14159265358979323846f/180); assert(end().state==S::Walk);
    in.searchedAngle=std::nextafter(in.searchedAngle,2.0f); assert(end().state==S::Turn);
    in.searchedTarget=false; in.homeDistanceSquared=99; assert(end().state==S::WalkPath);
    in.pathAngle=1; assert(end().state==S::TurnPath);
    in.homeDistanceSquared=100; assert(end().state==S::TurnHome);
    in.homeAngle=3.14159265358979323846f/4; assert(end().state==S::WalkHome);
    in.homeAngle=std::nextafter(in.homeAngle,2.0f); assert(end().state==S::TurnHome);
    in.homeDistanceSquared=-1; assert(!end().valid&&end().state==S::None);
    puts("p2_groink_target_test PASS");
}
