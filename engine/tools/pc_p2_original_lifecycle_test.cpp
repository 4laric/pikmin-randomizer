#include "pc_p2_original_lifecycle.h"
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace p2original;
static int checks=0;static void check(bool b){++checks;if(!b)throw std::runtime_error("lifecycle "+std::to_string(checks));}
int main(){std::string e,f(64,'a'),bytes;GeneratorState s;s.uid=0x52000001;s.count=3;s.reserved=5;s.deathCount=1;s.dayNum=5;s.resurrectionDays=2;s.epoch=8;s.activation=1;GenerationDecision d;
 check(decideOriginalGeneration(s,6,false,d,e));check(d.generate&&d.remaining==2&&d.next.deathCount==1&&d.next.epoch==8&&!d.resetDeaths);
 check(decideOriginalGeneration(s,7,false,d,e));check(d.generate&&d.remaining==3&&d.next.deathCount==0&&d.next.dayNum==7&&d.next.epoch==9&&d.resetDeaths);
 check(decideOriginalGeneration(s,6,true,d,e));check(d.remaining==3&&d.next.dayNum==6&&d.next.epoch==9);
 auto noTrack=s;noTrack.reserved=3;check(decideOriginalGeneration(noTrack,20,false,d,e));check(!d.generate&&!d.expired&&d.next.deathCount==1&&d.next.epoch==8);
 auto expired=s;expired.dayLimit=5;check(decideOriginalGeneration(expired,6,true,d,e));check(d.expired&&!d.generate&&d.next.deathCount==1);
 expired.dayLimit=-2;check(decideOriginalGeneration(expired,0,false,d,e));check(d.expired);
 check(originalDeath(s,noTrack,e));check(noTrack.deathCount==2&&noTrack.dayNum==5&&noTrack.epoch==8);
 noTrack.deathCount=3;check(!originalDeath(noTrack,expired,e));
 auto negative=s;negative.resurrectionDays=-10;check(decideOriginalGeneration(negative,0,false,d,e));check(d.resetDeaths&&d.next.dayNum==0);
 auto max=s;max.epoch=std::numeric_limits<std::uint64_t>::max();check(!decideOriginalGeneration(max,7,false,d,e));
 check(encodeOriginalState(f,s,bytes,e));check(bytes.size()==132);
 GeneratorState restored;check(decodeOriginalState(f,s.uid,s.count,bytes,restored,e));check(restored.deathCount==1&&restored.epoch==8&&restored.resurrectionDays==2&&restored.reserved==5&&restored.activation==1);
 check(!decodeOriginalState(std::string(64,'b'),s.uid,s.count,bytes,restored,e));check(!decodeOriginalState(f,s.uid+1,s.count,bytes,restored,e));check(!decodeOriginalState(f,s.uid,s.count+1,bytes,restored,e));
 for(unsigned i=0;i<bytes.size();++i){auto bad=bytes;bad[i]^=1;check(!decodeOriginalState(f,s.uid,s.count,bad,restored,e));}
 check(!decodeOriginalState(f,s.uid,s.count,bytes+"x",restored,e));check(!decodeOriginalState(f,s.uid,s.count,bytes.substr(1),restored,e));
 auto unborn=s;unborn.epoch=0;unborn.deathCount=0;check(encodeOriginalState(f,unborn,bytes,e));check(decodeOriginalState(f,s.uid,s.count,bytes,restored,e));check(restored.epoch==0);check(decideOriginalGeneration(restored,5,true,d,e));check(d.next.epoch==1);
 auto untouched=s;check(!originalDeath(unborn,untouched,e));
 check(untouched.uid==s.uid&&untouched.count==s.count&&untouched.reserved==s.reserved&&untouched.deathCount==s.deathCount&&untouched.dayNum==s.dayNum&&untouched.resurrectionDays==s.resurrectionDays&&untouched.dayLimit==s.dayLimit&&untouched.epoch==s.epoch&&untouched.activation==s.activation);
 auto entered=s;check(beginOriginalActivation(s,entered,e));check(entered.activation==2&&entered.epoch==8&&entered.dayNum==5&&entered.deathCount==1);
 auto exhausted=s;exhausted.activation=std::numeric_limits<std::uint64_t>::max();auto preserved=s;check(!beginOriginalActivation(exhausted,preserved,e));check(preserved.activation==s.activation&&preserved.epoch==s.epoch);
 auto oldWire=bytes;oldWire.replace(0,4,"OGC1");oldWire.erase(92,8);check(oldWire.size()==124);check(!decodeOriginalState(f,s.uid,s.count,oldWire,restored,e));
 std::cout<<"PASS original lifecycle/cache "<<checks<<" controls\n";
}
