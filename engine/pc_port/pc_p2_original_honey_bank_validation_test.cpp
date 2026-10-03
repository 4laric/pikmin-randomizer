#include "pc_p2_original_honey_bank_validation.h"
#include <cassert>
#include <iostream>
using namespace p2originalresource::honey;
int main(){
 std::array<ReceiverClip,7> clips;const float durations[]={30,20,8,40,40,60,50};for(unsigned i=0;i<7;++i)clips[i].duration=durations[i];clips[4].loopStart=0;clips[4].loopEnd=39;clips[4].keys={{0,0},{39,1}};
 std::string fp(64,'a'),error;unsigned motion=99;ReceiverClock restored;
 auto check=[&](Phase phase,const char* payload){return animationSnapshot("P2OHA1 "+fp+" "+payload,fp,phase,clips,motion,restored,error);};
 assert(check(Phase::Wait,"4 0 0 0"));assert(check(Phase::Wait,"4 1 1 0"));assert(check(Phase::Wait,"4 39.9 1 0"));
 assert(!check(Phase::Wait,"4 1 0 0"));assert(!check(Phase::Wait,"4 0 1 0"));assert(!check(Phase::Wait,"4 39.9 2 0")); // cannot skip or replay keys
 assert(!check(Phase::Wait,"4 39 2 1"));assert(!check(Phase::Wait,"4 40 2 0")); // loop cannot complete or retain overshoot
 assert(check(Phase::Fall,"0 29 0 1"));assert(!check(Phase::Fall,"0 28 0 1"));assert(!check(Phase::Fall,"0 29 1 1"));
 assert(!check(Phase::Shrink,"6 49 0 1"));assert(!check(Phase::Bounce,"3 39 0 1"));assert(!check(Phase::Touch,"5 59 0 1"));assert(!check(static_cast<Phase>(42),"6 0 0 0"));
 assert(!check(Phase::Bounce,"0 0 0 0"));assert(!check(Phase::Dead,"6 49 0 1"));assert(!check(Phase::Touch,"5 nan 0 0"));assert(!check(Phase::Touch,"5 0 0 0 junk"));
 assert(!animationSnapshot("P2OHA1 "+std::string(64,'b')+" 0 0 0 0",fp,Phase::Fall,clips,motion,restored,error));
 assert(check(Phase::Wait,"4 0 0 0"));bool finishing=false;std::vector<int> events;assert(restored.advance(clips[motion],40,finishing,[&](int key){events.push_back(key);return true;})&&restored.frame==0&&restored.next==0);
 assert(check(Phase::Wait,"4 0 0 0"));events.clear();assert(restored.advance(clips[4],1,finishing,[&](int key){events.push_back(key);return true;})&&events==std::vector<int>{0});
 std::cout<<"P2_ORIGINAL_HONEY_BANK_VALIDATION_PASS\n";
}
