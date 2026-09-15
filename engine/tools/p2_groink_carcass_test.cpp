#include "pc_p2_groink_carcass.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
int main() {
    using C=P2GroinkCarcassCommand;
    P2GroinkCarcass policy;
    assert(!policy.step(0.1f,true,true).valid);
    assert(policy.become({0.25f,0.5f,100}));
    auto r=policy.step(0.25f,true,true);
    assert(r.valid&&r.count==1&&r.commands[0]==C::ActivateGauge&&policy.health()==0);
    r=policy.step(0.25f,true,true); assert(r.count==0&&policy.health()==50);
    r=policy.step(0.25f,true,true); assert(r.count==2&&r.commands[0]==C::KillPellet&&r.commands[1]==C::RequestBirth);
    assert(policy.step(0.25f,true,true).count==0); // No invented retry if birth fails.
    r=policy.step(0.1f,false,false); assert(r.count==0&&policy.health()==100);
    r=policy.step(0.1f,false,true); assert(r.count==1&&r.commands[0]==C::DeactivateGauge&&policy.health()==0&&policy.timer()==0);
    assert(policy.step(0.1f,false,true).count==0);
    assert(policy.become({0.2f,0.1f,100}));
    r=policy.step(0.25f,true,false); assert(r.count==0&&policy.timer()==0.25f&&policy.health()==0);
    r=policy.step(0.25f,true,true); assert(r.count==2&&policy.health()==250); // No clamp/late gauge activation.
    assert(policy.become({1,1,100})); policy.step(0.1f,true,true);
    const float before=policy.timer(); policy.step(0.1f,false,true); assert(policy.timer()==before);
    r=policy.step(std::numeric_limits<float>::quiet_NaN(),true,true,false); assert(r.valid&&policy.timer()==before);
    assert(!policy.step(-1,true,true).valid&&policy.timer()==before);
    assert(!policy.become({0,0,10})&&policy.timer()==before);
    assert(policy.become({0,1,100})); r=policy.step(0,true,true); assert(r.count==0&&policy.health()==0);
    r=policy.step(0.1f,true,true); assert(r.count==0&&policy.health()==10);
    assert(policy.become({0,1,0})); assert(policy.step(0.1f,true,true).count==0);
    policy.reset(); assert(!policy.ready()&&policy.timer()==0&&policy.health()==0);
    puts("p2_groink_carcass_test PASS");
}
