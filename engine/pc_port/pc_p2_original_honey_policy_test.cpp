#include "pc_p2_original_honey_policy.h"
#include <cassert>
#include <iostream>
using namespace p2originalresource;using namespace p2originalresource::honey;
int main(){
 Policy p;assert(!p.absorbable()&&!p.absorb());assert(p.bounce()&&p.motion()==3&&!p.absorbable());assert(p.key()&&p.phase==Phase::Wait&&p.motion()==4);
 assert(!p.contact(9.9f,0,false,true,false));assert(p.contact(10,0,false,true,false)&&p.phase==Phase::Touch);
 assert(p.absorb()&&p.phase==Phase::Shrink&&p.absorbable());assert(p.absorb()&&p.absorb());assert(p.key()&&!p.alive()&&!p.absorb());
 p=Policy{};p.kind=HoneyKind::Spicy;p.bounce();p.key();assert(!p.contact(10,0,false,true,false));assert(p.contact(10,0,true,false,false));p.key();assert(!p.contact(10,0,false,false,true));
 Drink d;assert(!d.shouldAbsorb(true));d.loopStart();assert(d.shouldAbsorb(true));d.absorbedOnce();assert(!d.shouldAbsorb(true));assert(d.pikiLoopEnd(true,true));
 Drink c;c.loopStart();c.absorbedOnce();assert(!c.naviLoopEnd(true,true));assert(c.naviLoopEnd(false,true));
 Drink timeout;for(unsigned i=0;i<180;++i)timeout.pikiTick();assert(!timeout.absorbed);timeout.pikiTick();assert(timeout.absorbed&&timeout.ticks==180);
 // Each captain owns its own receiver on the same shrinking drop.
 Drink first,second;first.loopStart();second.loopStart();assert(first.shouldAbsorb(true)&&second.shouldAbsorb(true));first.absorbedOnce();assert(second.shouldAbsorb(true));
 ReceiverClip clip;clip.duration=45;clip.loopStart=11;clip.loopEnd=29;clip.keys={{11,0},{29,1}};
 assert(clip.valid());ReceiverClock clock;bool finishing=false;std::vector<int> events;
 auto emit=[&](int k){events.push_back(k);return true;};
 assert(clock.advance(clip,11,finishing,emit)&&events.empty()); // strict key frame < int(timer)
 assert(clock.advance(clip,0.9f,finishing,emit)&&events.empty());
 assert(clock.advance(clip,0.1f,finishing,emit)&&events==std::vector<int>{0});
 assert(clock.advance(clip,18,finishing,emit)&&events==std::vector<int>({0,1})&&clock.frame==11); // source discards overshoot
 events.clear();assert(clock.advance(clip,100,finishing,emit)&&events==std::vector<int>({0,1})&&clock.frame==11); // one loop per update
 finishing=true;events.clear();assert(clock.advance(clip,34,finishing,emit)&&events==std::vector<int>({0,1,1000})&&clock.complete&&clock.frame==44);
 assert(clock.advance(clip,30,finishing,emit)&&events.size()==3); // END exactly once
 ReceiverClip grow;grow.duration=30;grow.keys={{14,2}};clock.reset();events.clear();finishing=false;
 assert(clock.advance(grow,14,finishing,emit)&&events.empty());assert(clock.advance(grow,1,finishing,emit)&&events==std::vector<int>{2});
 assert(clock.advance(grow,15,finishing,emit)&&events==std::vector<int>({2,1000}));
 clock.reset();events.clear();bool stopped=false;assert(clock.advance(grow,30,finishing,[&](int k){events.push_back(k);stopped=true;return false;})&&stopped&&events==std::vector<int>{2});
 clock.reset();events.clear();finishing=false;assert(clock.advance(clip,100,finishing,[&](int k){events.push_back(k);if(k==1)finishing=true;return true;})&&events==std::vector<int>({0,1,1000})&&clock.complete); // handler finish before loop switch
 std::cout<<"P2_ORIGINAL_HONEY_POLICY_PASS\n";
}
