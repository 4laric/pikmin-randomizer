#include "pc_p2_original_corpse_profile.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <set>
using namespace p2original;
int main(){
 unsigned checks=0,failures=0;
 auto check=[&](bool ok,const char* name){++checks;if(!ok){++failures;std::printf("FAIL %s\n",name);}};
 // Independent golden literals: legal GPVE01 revision0 carcass_config.txt,
 // SHA a76c476352cb0d7386a8ab448f0e35285cc8668f43f2b9189cfdd87b03de9de0.
 // The retail table has a null sentinel at index0; authored indices below are
 // preserved, rather than compacted to source order or P1 chassis order.
 const CorpseProfile expected[]={
  {26,17,"Catfish",5,10,5,22,15,10,150,0,0,0},
  {33,23,"FireChappy",10,20,12,45,30,35,700,0,0,55},
  {34,35,"SnakeCrow",5,10,15,20,15,15,200,0,0,122.5f},
  {95,41,"Rkabuto",7,15,8,34,34,20,250,29,0,0},
  {96,40,"Fkabuto",7,15,8,34,34,20,250,29,0,0},
  {1,1,"Kochappy",3,6,4,22,13,14,200,0,0,0},
  {45,2,"YellowKochappy",3,6,4,22,13,14,200,0,0,0},
  {44,3,"BlueKochappy",3,6,4,22,13,14,200,0,0,0},
  {2,4,"Chappy",10,20,12,40,30,30,700,0,0,55},
  {43,5,"YellowChappy",10,20,12,40,30,30,700,0,0,55},
  {42,6,"BlueChappy",10,20,12,40,30,30,700,0,0,55},
  {12,7,"UjiA",1,1,2,10,10,10,90,0,0,0},
  {13,8,"UjiB",1,1,3,10,10,10,90,0,0,0},
  {14,9,"Tobi",1,1,4,12,12,12,90,0,0,0},
  {17,10,"Frog",7,14,8,30,22,14,400,-27.3f,0,12.3f},
  {18,11,"MaroFrog",7,14,8,30,22,14,400,-0.6f,0,-34},
  {24,12,"Tank",7,15,8,25,18,10,250,32.3f,0,-2.5f},
  {25,13,"Wtank",7,15,8,25,18,10,250,32.3f,0,-2.5f},
  {15,20,"Armor",8,16,8,25,20,12,200,0,0,0},
 };
 auto equal=[](float a,float b){return std::isfinite(a)&&std::fabs(a-b)<0.00001f;};
 for(const auto& golden:expected){
  const auto* p=corpseProfile(golden.source);check(p!=nullptr,"retail profile exists");if(!p)continue;
  check(p->source==golden.source&&p->index==golden.index&&!std::strcmp(p->name,golden.name),"exact source index name");
  check(p->minimum==golden.minimum&&p->maximum==golden.maximum&&p->seeds==golden.seeds,"exact retail carry and Onion yield");
  check(equal(p->radius,golden.radius)&&equal(p->pickRadius,golden.pickRadius)&&equal(p->height,golden.height)&&equal(p->inertia,golden.inertia),"exact retail dimensions and inertia");
  check(equal(p->offsetX,golden.offsetX)&&equal(p->offsetY,golden.offsetY)&&equal(p->offsetZ,golden.offsetZ),"exact authored corpse offset");
  check(!corpseDisabled(golden.source),"profile never no-corpse");
 }
 const unsigned noCorpse[]={0,3,4,5,6,7,8,9,10,11,16,19,20,21,22,29,31,36,37,46,47,48,49,50,51,52,55,56,57,66,69,72,73,74,80,81,82,83,85,86,87,88,89,90,91,92,93,98,99};
 std::set<unsigned> noCorpseSet;
 for(unsigned source:noCorpse){check(noCorpseSet.insert(source).second,"no-corpse fixture unique");check(corpseDisabled(source)&&!corpseProfile(source),"known no-corpse source");}
 check(noCorpseSet.size()==49,"49 audited no-corpse sources");
 const unsigned profileSources[]={1,45,44,2,43,42,12,13,14,17,18,24,25,23,32,58,26,27,28,15,30,53,33,35,41,38,40,54,59,60,61,62,65,67,34,70,63,76,75,96,95,71,101,79,78,97,68,77,84,94};
 std::set<unsigned> sources,indices;
 for(unsigned source:profileSources){
  const auto* p=corpseProfile(source);
  check(sources.insert(source).second&&p,"50 profile source fixture unique");
  if(!p)continue;
  check(indices.insert(p->index).second&&p->index>=1&&p->index<=50,"retail indices unique and bounded");
  check(!noCorpseSet.count(source)&&!corpseDisabled(source),"no overlap with no-corpse sources");
  check(p->minimum&&p->minimum<=p->maximum&&p->maximum<=128&&p->seeds&&p->radius>0&&p->pickRadius>0&&p->height>0,"all physical profiles internally valid");
 }
 check(sources.size()==50&&indices.size()==50,"50 audited profiles exactly");
 unsigned actualProfiles=0,actualDisabled=0;
 for(unsigned source=0;source<=101;++source){
  actualProfiles+=corpseProfile(source)!=nullptr;actualDisabled+=corpseDisabled(source);
  check((corpseProfile(source)!=nullptr)==bool(sources.count(source)),"no unexpected profile mapping");
  check(corpseDisabled(source)==bool(noCorpseSet.count(source)),"no unexpected disabled mapping");
 }
 check(actualProfiles==50&&actualDisabled==49,"complete catalog partition counts");
 for(unsigned source:{39u,64u,100u,102u,65536u,std::numeric_limits<unsigned>::max()})check(!corpseProfile(source)&&!corpseDisabled(source),"unclassified source refuses fallback");
 check(!corpseProfile(55)&&corpseDisabled(55),"Withering never corpse");
 std::printf("original_corpse_profile checks=%u failures=%u engine=0 source=GPVE01-r0\n",checks,failures);return failures?1:0;
}
