#include "pc_p2_groink_attack.h"
#include <cstdio>
#include <cstdlib>
#include <initializer_list>

using C = P2GroinkAttackCommand;
using E = P2GroinkAttackEvent;
constexpr float dt = P2GroinkPolicy::kSourceDelta;
void check(bool v, const char* text) { if (!v) { std::fprintf(stderr,"FAIL %s\n",text); std::exit(1); } }
void expect(const P2GroinkAttackCommands& out, std::initializer_list<C> commands) {
    check(out.valid && out.count==commands.size(),"command count");
    unsigned i=0; for (auto c:commands) check(out.items[i++]==c,"command ordering");
}
int main() {
    P2GroinkAttack attack;
    P2GroinkAttackInput in;
    check(!attack.step(in,dt).valid,"begin required"); attack.begin();
    in.event=E::Charge;
    expect(attack.step(in,dt),{C::StopMotion,C::StartAim,C::StartCharge});
    check(attack.waitTime()==0,"charge clears wait");
    in.event=E::None; in.motionStopped=true; in.gunLocked=true; in.gunRotating=true;
    expect(attack.step(in,dt),{C::RefreshTarget}); // zero wait delays resume
    expect(attack.step(in,dt),{C::ResumeMotion,C::RefreshTarget});
    in.motionStopped=false; in.gunRotating=false; in.event=E::Smoke;
    expect(attack.step(in,dt),{C::LargeSmoke,C::FinishCharge});
    in.event=E::Fire; expect(attack.step(in,dt),{C::EmitVolley});
    in.motionFinishing=true; expect(attack.step(in,dt),{C::EmitVolley});
    in.flick=true; expect(attack.step(in,dt),{C::FinishMotion,C::EmitVolley});
    in.health=0; expect(attack.step(in,dt),{C::FinishMotion});
    in.event=E::End; expect(attack.step(in,dt),{C::FinishMotion,C::ExitDead});
    check(!attack.step(in,dt).valid,"end deactivates controller");
    attack.begin(); in={}; in.motionStopped=true; in.flick=true; in.event=E::End;
    expect(attack.step(in,dt),{C::ResumeMotion,C::FinishMotion,C::ExitFlick});
    attack.begin(); in={}; in.event=E::End;
    expect(attack.step(in,dt),{C::ResolveNextState});
    attack.begin(); in={}; in.event=E::Return;
    expect(attack.step(in,dt),{C::StopMotion,C::ReturnGun});
    in.event=E::None; in.motionStopped=true; in.gunRotating=true;
    expect(attack.step(in,dt),{C::RefreshTarget});
    in.gunRotating=false; in.gunLocked=true;
    expect(attack.step(in,dt),{C::ResumeMotion});
    const float wait=attack.waitTime(); in.activeTick=false; in.event=E::Fire;
    expect(attack.step(in,dt),{}); check(attack.waitTime()==wait,"paused timer and event unchanged");
    in.activeTick=true;
    check(!attack.step(in,0.1f).valid && attack.waitTime()==wait,"invalid delta immutable");
    in.health=NAN; check(!attack.step(in,dt).valid && attack.waitTime()==wait,"invalid health immutable");
    attack.reset(); check(!attack.step({},dt).valid,"reset inactive");

    P2GroinkGunRotation gun; gun.start();
    check(gun.rotating() && !gun.locked() && !gun.finished() && gun.angle()==0,"start flags");
    for (int i=0;i<30;++i) check(gun.update({0,40,0},{0,0,250},250,15,dt),"aim update");
    check(gun.locked() && gun.speed()>0,"aim acquired lock");
    check(gun.update({0,40,0},{0,0,70},250,15,dt) && gun.locked(),"source lock latches during retarget");
    gun.finish(); check(gun.rotating() && !gun.locked() && gun.finished(),"finish retains rotation");
    int count=0;
    while(gun.rotating() && count++<300) check(gun.update({}, {},0,0,dt),"return needs no target");
    check(count<300 && gun.locked() && gun.finished(),"return unlocks animation");
    gun.start(); check(!gun.locked() && !gun.finished() && gun.speed()==0,"second cycle clean");
    float next=123; bool done=false;
    check(P2GroinkGunRotation::returnStep(0.034f,next,done) && done && std::fabs(next-0.009f)<1e-6f,"post-step return threshold");
    check(P2GroinkGunRotation::returnStep(6.27f,next,done) && done && next>6.28f,"wrapped positive return");
    check(P2GroinkGunRotation::returnStep(-6.27f,next,done) && done && next<-6.28f,"wrapped negative return");
    next=123; done=false;
    check(!P2GroinkGunRotation::returnStep(NAN,next,done) && next==123 && !done,"invalid return immutable");
    check(!gun.update({}, {},250,15,0.1f) && gun.angle()==0,"invalid gun tick immutable");
    std::puts("p2_groink_attack_test PASS");
}
