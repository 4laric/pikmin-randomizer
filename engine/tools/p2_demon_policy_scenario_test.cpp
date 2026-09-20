#include "pc_p2_demon_capture.h"
#include "pc_p2_demon_attack_window.h"
#include "pc_p2_demon_escape.h"
#include "pc_p2_demon_drop_policy.h"
#include <cassert>
#include <cstdio>

// Simulated receiver, deliberately separate from policy attempt counts.
struct Receiver {
    bool occupied=false;
    unsigned attempts=0;
    void stimulate(bool accepts) { ++attempts; if(accepts) occupied=true; }
};
static void attack(Receiver& receiver,bool accepts) {
    P2DemonTargetGate target;
    assert(target.reset(12800)); // Source spawn, not the post-drop cooldown.
    P2DemonTargetInput input{0,100,90,100};
    P2DemonCaptain captain;
    assert(target.step(1.f/30,input,&captain,1).found);
    P2DemonAttackWindow window;
    auto frame=window.step(17,true,false);
    assert(frame.attemptCapture);
    auto grab=p2_demon_grab_check(true,false,receiver.occupied,100,15);
    if(frame.attemptCapture&&grab.attempt) receiver.stimulate(accepts);
}
int main() {
    using E=P2DemonAttackEvent; using N=P2DemonAttackNext; using S=P2DemonDropPhase;
    auto event=P2DemonAttackWindow::eventDecision;
    Receiver rejected;
    attack(rejected,false);
    assert(rejected.attempts==1&&!rejected.occupied);
    assert(event(true,true,E::CaptureCheck,rejected.occupied).next==N::Fail);
    assert(event(true,true,E::End,rejected.occupied).next==N::Move);

    Receiver accepted;
    attack(accepted,true);
    assert(event(true,true,E::CaptureCheck,accepted.occupied).next==N::None);
    assert(event(true,true,E::End,accepted.occupied).next==N::CatchFly);
    assert(!p2_demon_grab_check(true,false,accepted.occupied,100,15).attempt);
    P2DemonDropPolicy drop;
    auto entry=drop.begin(1,10,200);
    assert(entry.startFall&&entry.actualY==-400&&entry.targetY==-200);
    accepted.occupied=false; // Simulated receiver's endStick; host must implement this.
    assert(event(true,true,E::End,accepted.occupied).next==N::Move);
    float damage=0;
    auto impact=drop.bounce(1); assert(impact.impactZeroDamage&&!impact.deliverDamage);
    auto end=drop.animationEnd(1,S::Knockdown);
    if(end.deliverDamage) damage+=end.damage;
    end=drop.animationEnd(1,S::Knockdown);
    if(end.deliverDamage) damage+=end.damage;
    assert(damage==10);
    assert(drop.tick(1,1).startGetUp);
    assert(drop.animationEnd(1,S::GetUp).resume);

    attack(accepted,true);
    P2DemonEscapeWindow escape;
    unsigned draws=0;
    auto random=[&] { ++draws; return 0.f; };
    for(int i=0;i<5;++i) assert(!escape.step(accepted.occupied,true,random).escape);
    assert(draws==0);
    if(escape.step(accepted.occupied,true,random).escape) accepted.occupied=false;
    assert(draws==2&&!accepted.occupied);
    assert(event(true,true,E::End,accepted.occupied).next==N::Move);
    assert(drop.phase()==S::Idle); // Voluntary escape must not arm drop damage.

    drop.begin(2,10,200); drop.bounce(2); drop.cancel();
    assert(!drop.animationEnd(2,S::Knockdown).deliverDamage);
    assert(drop.begin(3,10,200).accepted);
    assert(!drop.animationEnd(2,S::Knockdown).accepted);
    puts("p2_demon_policy_scenario_test PASS (simulated receiver; no native gameplay)");
}
