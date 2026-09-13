#include "pc_p2_demon_drop_policy.h"
#include <cassert>
#include <limits>
#include <cstdio>
int main() {
    using S=P2DemonDropPhase;
    P2DemonDropPolicy p;
    auto c=p.begin(1,12,200); assert(c.accepted&&c.startFall&&c.actualY==-400&&c.targetY==-200);
    assert(!p.begin(2,1,200).accepted);
    assert(!p.animationEnd(1,S::Knockdown).deliverDamage);
    assert(!p.bounce(2).accepted);
    c=p.bounce(1); assert(c.startKnockdown&&c.impactZeroDamage&&!c.deliverDamage);
    assert(!p.bounce(1).accepted);
    c=p.animationEnd(1,S::Knockdown); assert(c.deliverDamage&&c.damage==12);
    assert(!p.animationEnd(1,S::Knockdown).deliverDamage);
    assert(!p.tick(1,0).startGetUp);
    assert(!p.tick(1,-1).accepted);
    assert(!p.tick(1,std::numeric_limits<float>::infinity()).accepted);
    assert(!p.tick(1,.5f).startGetUp);
    assert(p.tick(1,.5f).startGetUp);
    assert(!p.animationEnd(1,S::Knockdown).resume);
    assert(p.animationEnd(1,S::GetUp).resume);
    assert(!p.begin(1,1,200).accepted);
    c=p.begin(2,0,200); assert(c.actualY==-100&&c.targetY==-200);
    c=p.bounce(2); assert(c.resume&&c.nudge&&!c.deliverDamage);
    p.begin(3,10,200); p.bounce(3); p.cancel();
    assert(!p.animationEnd(3,S::Knockdown).deliverDamage);
    assert(p.begin(4,10,200).accepted);
    assert(!p.bounce(3).accepted);
    p.cancel();
    assert(!p.begin(5,1,-1).accepted);
    assert(!p.begin(5,std::numeric_limits<float>::quiet_NaN(),200).accepted);
    assert(p.begin(5,1,200).accepted);
    p.cancel();
    assert(!p.bounce(5).accepted);
    c=p.begin(6,-1,200); assert(c.accepted&&c.actualY==-100);
    c=p.bounce(6); assert(c.nudge&&c.resume&&!c.deliverDamage);
    p.begin(7,10,200); p.bounce(7); p.animationEnd(7,S::Knockdown);
    assert(p.tick(7,1000).startGetUp);
    assert(!p.tick(7,1000).startGetUp);
    puts("p2_demon_drop_policy_test PASS");
}
