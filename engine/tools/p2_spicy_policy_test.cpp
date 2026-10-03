#include "pc_p2_spicy_policy.h"
#include "pc_p2_original_resource_state.h"
#include "pc_p2_original_honey_policy.h"
#include <cassert>
#include <cstdio>
#include <limits>
using namespace p2originalresource;
int main() {
    p2sprays::SpicyStatus s;
    assert(!s.active() && s.animationRate()==1);
    s.begin(); assert(s.remaining==40 && s.animationRate()==2);
    assert(!s.tick(30,false) && s.remaining==40);
    assert(!s.tick(std::numeric_limits<float>::quiet_NaN(),true) && s.remaining==40);
    assert(!s.tick(-1,true) && s.remaining==40);
    assert(!s.tick(39.5f,true) && s.active());
    s.begin(); assert(s.remaining==40); // re-spray extends; does not stack
    assert(!s.tick(39.5f,true)); assert(s.tick(.5f,true) && !s.active());
    s.begin(); s.clear(); assert(!s.active());
    assert(s.restore(17.25f) && s.remaining==17.25f);
    assert(!s.restore(-1) && !s.restore(40.01f));
    assert(!s.restore(std::numeric_limits<float>::infinity()) && s.remaining==17.25f);
    assert(!s.restore(std::numeric_limits<float>::quiet_NaN()) && s.remaining==17.25f);
    assert(s.restore(0) && !s.active());
    // Actual shared receiver implementation, strict source event boundary.
    honey::ReceiverClip clip;clip.duration=35;clip.keys={{14,2}};
    honey::ReceiverClock clock;bool finishing=true;int actions=0,ends=0;
    auto emit=[&](int key){if(key==2)++actions;if(key==1000)++ends;return true;};
    assert(clock.advance(clip,14,finishing,emit)&&actions==0);
    assert(clock.advance(clip,.9f,finishing,emit)&&actions==0);
    assert(clock.advance(clip,.1f,finishing,emit)&&actions==1);
    assert(clock.advance(clip,20,finishing,emit)&&ends==1);
    assert(clock.advance(clip,10,finishing,emit)&&actions==1&&ends==1);
    ResourceState inventory; ResourceSnapshot snapshot; EggContents contents; std::string e;
    assert(!inventory.useSpray(HoneyKind::Spicy,e));
    assert(inventory.restore(snapshot,contents,e));
    assert(inventory.addBerry(HoneyKind::Spicy,9,p2sprays::BerriesPerSpray,e));
    assert(!inventory.useSpray(HoneyKind::Spicy,e));
    assert(inventory.addBerry(HoneyKind::Spicy,1,p2sprays::BerriesPerSpray,e));
    assert(inventory.sprayCount(HoneyKind::Spicy)==1);
    assert(inventory.useSpray(HoneyKind::Spicy,e)); assert(!inventory.useSpray(HoneyKind::Spicy,e));
    std::puts("P2_SPICY_POLICY_PASS timing/pause/refresh/recovery and real stock production/use; gameplay untested");
}
