#include "pc_p2_demon_escape.h"
#include "pc_p2_demon_capture.h"
#include <cassert>
#include <cstdio>
int main() {
    P2DemonEscapeWindow w; int draws=0;
    auto fail=[&]{++draws; return 0.99f;};
    for(int i=0;i<5;++i) assert(w.step(true,true,fail).animationSpeed==30);
    assert(draws==0); auto r=w.step(true,true,fail); assert(w.count()==6&&draws==1&&!r.escape);
    draws=0; auto pass=[&]{++draws; return 0.0f;};
    assert(w.step(true,false,pass).escape&&draws==2);
    w.reset(); w.step(true,true,fail);
    for(int i=0;i<27;++i) w.step(true,false,fail);
    assert(w.count()==1); w.step(true,false,fail); assert(w.count()==0);
    w.reset(); w.step(false,true,fail); assert(w.count()==0);
    for(int i=0;i<100;++i) w.step(true,true,fail);
    assert(w.count()==28); w.reset(); assert(w.count()==0);
    P2DemonTargetGate gate; assert(gate.reset(12800));
    P2DemonCaptain c{true,false,0,1};
    assert(gate.step(0,{0,100,90,100},&c,1).found);
    assert(!gate.reset(-1)&&gate.timer()==12800); gate.reset();
    assert(!gate.step(0,{0,100,90,100},&c,1).found);
    puts("p2_demon_escape_test PASS");
}
