#include "pc_p2_demon_capture.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main() {
    P2DemonTargetGate gate;
    P2DemonTargetInput in{0,100,90,200};
    P2DemonCaptain c[]={{true,false,0,10000},{true,false,0,100}};
    for(int i=0;i<12;++i) assert(!gate.step(0.25f,in,c,2).found);
    auto r=gate.step(0.01f,in,c,2); assert(r.valid&&r.found&&r.index==0);
    c[0].stuckToMouth=true; assert(gate.step(0,in,c,2).index==1);
    c[1].alive=false; assert(!gate.step(0,in,c,2).found); c[1].alive=true;
    in.homeDistanceSquaredXZ=10000; assert(!gate.step(0,in,c,2).found); in.homeDistanceSquaredXZ=0;
    c[1].distanceSquaredXZ=40000; assert(!gate.step(0,in,c,2).found); c[1].distanceSquaredXZ=100;
    c[1].angleRadians=90*0.017453292519943295f; assert(gate.step(0,in,c,2).found);
    c[1].angleRadians=std::nextafter(c[1].angleRadians,4.0f); assert(!gate.step(0,in,c,2).found);
    float before=gate.timer(); assert(gate.step(0.2f,in,c,2,false).valid&&gate.timer()==before);
    assert(!gate.step(-1,in,c,2).valid&&gate.timer()==before);
    c[1].angleRadians=std::numeric_limits<float>::quiet_NaN(); assert(!gate.step(0.1f,in,c,2).valid&&gate.timer()==before);
    gate.reset(); assert(gate.timer()==0);
    assert(p2_demon_grab_check(true,false,false,99,10).attempt);
    assert(!p2_demon_grab_check(true,false,false,100,10).attempt);
    assert(!p2_demon_grab_check(true,true,false,0,10).attempt);
    assert(!p2_demon_grab_check(false,false,false,0,10).attempt);
    assert(!p2_demon_grab_check(true,false,true,0,10).attempt);
    assert(!p2_demon_grab_check(true,false,false,0,0).attempt);
    assert(!p2_demon_grab_check(true,false,false,-1,10).valid);
    puts("p2_demon_capture_test PASS");
}
