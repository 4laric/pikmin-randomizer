#include "pc_p2_groink_events.h"
#include <cstdio>
#include <cstdlib>
void check(bool value,const char* text) { if(!value) { std::fprintf(stderr,"FAIL %s\n",text); std::exit(1); } }
using E=P2GroinkAttackEvent;
int main() {
    P2GroinkAttackCursor cursor;
    check(cursor.start({44,{11,22,25,32}}),"retail attack metadata");
    for(int i=1;i<=11;++i) check(cursor.animate(1).event==E::None,"no event on key boundary");
    check(cursor.animate(0).event==E::None && cursor.frame()==11,"stop at key does not fire");
    check(cursor.animate(0.5f).event==E::None,"integer crossing required");
    check(cursor.animate(0.5f).event==E::Charge,"frame12 charge");
    for(int i=0;i<50;++i) check(cursor.animate(0).event==E::None && cursor.frame()==12,"no held event during aim pause");
    for(int i=13;i<=22;++i) check(cursor.animate(1).event==E::None,"no early smoke");
    check(cursor.animate(1).event==E::Smoke,"frame23 smoke");
    check(cursor.animate(1).event==E::None && cursor.animate(1).event==E::None,"no early fire");
    check(cursor.animate(1).event==E::Fire,"frame26 fire");
    for(int i=27;i<=32;++i) check(cursor.animate(1).event==E::None,"no early return");
    check(cursor.animate(1).event==E::Return,"frame33 return");
    check(cursor.animate(0).event==E::None,"return pause consumes no edge");
    for(int i=34;i<44;++i) check(cursor.animate(1).event==E::None,"no early end");
    check(cursor.animate(1).event==E::End && cursor.frame()==43,"END clamps display frame");
    for(int i=0;i<10;++i) check(cursor.animate(1).event==E::None,"END once");
    const float old=cursor.frame();
    check(!cursor.animate(NAN).valid && cursor.frame()==old,"invalid increment immutable");
    check(!cursor.start({44,{11,11,25,32}}) && cursor.completed(),"invalid clip preserves state");
    cursor.reset(); check(!cursor.animate(1).valid,"reset requires start");
    check(cursor.start({10,{1,2,3,5}}),"bounded dense keys");
    check(cursor.animate(4).event==E::Fire,"last callback wins as source single slot");

    // Normal enemy-manager ordering: FSM consumes the previous animation latch,
    // gun rotation follows FSM, and animation generates next tick's latch.
    cursor.start({44,{11,22,25,32}}); P2GroinkAttack attack; attack.begin();
    P2GroinkGunRotation gun; bool stopped=false; int fires=0,ends=0,pauses=0;
    E pending=E::None;
    for(int tick=0;tick<250 && !ends;++tick) {
        P2GroinkAttackInput input; input.motionStopped=stopped; input.gunRotating=gun.rotating();
        input.gunLocked=gun.locked(); input.event=pending;
        auto commands=attack.step(input,P2GroinkPolicy::kSourceDelta); check(commands.valid,"composed attack tick");
        for(std::size_t i=0;i<commands.count;++i) switch(commands.items[i]) {
            case P2GroinkAttackCommand::StopMotion: stopped=true; ++pauses; break;
            case P2GroinkAttackCommand::ResumeMotion: stopped=false; break;
            case P2GroinkAttackCommand::StartAim: gun.start(); break;
            case P2GroinkAttackCommand::ReturnGun: gun.finish(); break;
            case P2GroinkAttackCommand::EmitVolley: ++fires; check(cursor.frame()==26,"fire follows animation not tick"); break;
            case P2GroinkAttackCommand::ResolveNextState: ++ends; break;
            default: break;
        }
        check(gun.update({0,40,0},{0,0,250},250,15,P2GroinkPolicy::kSourceDelta),"composed rotation");
        pending=cursor.animate(stopped?0:1).event;
    }
    check(fires==1 && pauses==2 && ends==1,"one cycle with both waits");
    std::puts("p2_groink_events_test PASS");
}
