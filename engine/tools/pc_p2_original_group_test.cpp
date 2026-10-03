#include "pc_p2_original_group.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace p2original;
static unsigned checks=0;
static void check(bool b){++checks;if(!b)throw std::runtime_error("group control "+std::to_string(checks));}
struct Provider:GroupProvider {
 int storage[10]{};unsigned births=0,releases=0,binds=0;bool admitted=true,reserved=true,releaseOK=true,bindOK=true,nullFirst=false,duplicate=false;
 std::vector<std::string> events;std::function<void(Creature*)> onRelease;
 bool preflight(const std::vector<CatalogRow>&,std::string&)override{events.push_back("preflight");return admitted;}
 bool reserve(const std::vector<CatalogRow>&,std::string&)override{events.push_back("reserve");return reserved;}
 bool birth(const CatalogRow&,Generator*,unsigned n,const Position& p,float facing,Creature*& out,std::string&)override{
  events.push_back("birth"+std::to_string(n));check(p.y==float(n+10));check(std::fabs(facing-1.57079637f)<0.000001f);
  out=(nullFirst&&n==0)?nullptr:reinterpret_cast<Creature*>(&storage[duplicate?0:n]);++births;return true;
 }
 bool bind(const CatalogRow&,Creature*,unsigned token,std::string&)override{++binds;check(token>=0x53000001u);return bindOK;}
 bool release(Creature* actor,unsigned,std::string&)override{if(!releaseOK)return false;if(onRelease)onRelease(actor);++releases;return true;}
};
int main(){
 std::string e;CatalogRow row;row.course="tutorial";row.member="defaultgen.txt";row.sourceKey="tutorial/defaultgen.txt#0";row.enemy.uid=originalGeneratorUid(row.sourceKey);row.enemy.count=2;row.enemy.directionDegrees=90;
 ActorRegistry registry;check(registry.install(std::string(64,'a'),{row},[](const CatalogRow&,std::string&){return true;},e));
 int nativeGenerator=0;auto* generator=reinterpret_cast<Generator*>(&nativeGenerator);GeneratorState source;source.uid=row.enemy.uid;source.count=2;source.reserved=5;source.resurrectionDays=2;
 GroupCourse course(registry);Provider provider;
 provider.admitted=false;check(!course.install({{generator,source}},provider,e));check(!course.owns(generator));check(provider.births==0&&provider.events.size()==1);
 provider.admitted=true;provider.reserved=false;check(!course.install({{generator,source}},provider,e));check(provider.births==0&&!course.owns(generator));
 provider.reserved=true;check(course.install({{generator,source}},provider,e));check(course.owns(generator));
 Math math;unsigned draws=0;math.draw=[&](float& out,std::string&){++draws;out=0.5f;return true;};math.sinCos=[](float a,float& s,float& c,std::string&){s=std::sin(a);c=std::cos(a);return true;};math.squareRoot=[](float a,float& out,std::string&){out=std::sqrt(a);return true;};
 // Even if caller supplies a batch floor, native group must interleave the
 // distinct source floor bridge and birth. No floor inside placement phase.
 math.mapAvailable=true;math.floor=[](const Position&,float&,std::string&){throw std::runtime_error("batched source floor called");return false;};
 unsigned floors=0;auto floor=[&](const Position&,float& y,std::string&){provider.events.push_back("floor"+std::to_string(floors));y=float(floors+++10);return true;};
 check(course.initialize(generator,5,true,math,floor,e));check(draws==0&&floors==2&&provider.births==2&&provider.binds==2);
 const auto n=provider.events.size();check(provider.events[n-4]=="floor0"&&provider.events[n-3]=="birth0"&&provider.events[n-2]=="floor1"&&provider.events[n-1]=="birth1");
 GeneratorState current;unsigned alive=0;check(course.state(generator,current,alive));check(alive==2&&current.epoch==1&&current.activation==1&&current.dayNum==5);
 check(!course.initialize(generator,5,true,math,floor,e));check(!course.death(generator,nullptr,e));
 auto* first=reinterpret_cast<Creature*>(&provider.storage[0]);check(course.death(generator,first,e));check(!course.death(generator,first,e));check(course.state(generator,current,alive));check(alive==1&&current.deathCount==1&&current.dayNum==5);
 std::string cache;check(!course.cache(generator,std::string(64,'b'),cache,e));check(cache.empty());check(course.cache(generator,std::string(64,'a'),cache,e));check(cache.size()==132);
 provider.releaseOK=false;check(!course.unload(e));check(course.owns(generator));unsigned id=0,token=0;check(registry.query(first,id,token));
 provider.releaseOK=true;check(course.unload(e));check(!course.owns(generator)&&provider.releases==2&&!registry.query(first,id,token));
 // Real callback execution across unload/RAM entry preserves source epoch,
 // changes activation, and uses remaining count rather than P1 alive loops.
 check(course.install({{generator,source}},provider,e));check(course.restoreState(generator,std::string(64,'a'),cache,e));floors=0;
 check(course.initialize(generator,6,false,math,floor,e));check(course.state(generator,current,alive));check(alive==1&&current.epoch==1&&current.activation==2&&current.deathCount==1&&current.dayNum==5);
 check(registry.query(first,id,token));check(course.death(generator,first,e));check(course.retiredNative(first,e));check(!registry.query(first,id,token));check(course.retiredNative(first,e));check(course.unload(e));
 // Unknown/corrupt cache and changed source metadata never alter state.
 check(course.install({{generator,source}},provider,e));auto bad=cache;bad[70]^=1;check(!course.restoreState(generator,std::string(64,'a'),bad,e));check(course.state(generator,current,alive)&&current.epoch==0&&alive==0);check(course.unload(e));
 // A partial family-bind failure retains concrete actor association so the
 // owner can dispose it; repeated init is refused, no identity replay.
 source.activation=10;Provider partial;partial.bindOK=false;check(course.install({{generator,source}},partial,e));floors=0;check(!course.initialize(generator,5,true,math,floor,e));check(partial.births==1);check(!course.initialize(generator,5,true,math,floor,e));check(!course.cache(generator,std::string(64,'a'),cache,e));check(course.unload(e)&&partial.releases==1);
 // Replay the same activation after a partial attempt: registry refuses the
 // retired logical ID, but failed token0 physical cleanup remains retryable.
 Provider pending;pending.releaseOK=false;
 check(course.install({{generator,source}},pending,e));floors=0;
 check(!course.initialize(generator,5,true,math,floor,e));check(pending.births==1&&pending.binds==0);
 check(!course.unload(e));check(course.owns(generator)&&pending.releases==0);
 pending.releaseOK=true;check(course.unload(e));check(pending.releases==1&&!course.owns(generator));
 // Actual native order: release -> detachGenerator/informDeath -> doKill/
 // family forget -> retirement. Both partial construction and normal unload
 // suppress synthetic death increments, while natural deaths above remain1.
 source.activation=20;Provider realOrder;
 realOrder.onRelease=[&](Creature* actor){
  GeneratorState before,after;unsigned beforeAlive=0,afterAlive=0;
  check(course.state(generator,before,beforeAlive));
  check(!course.initialize(generator,5,true,math,floor,e));check(!course.unload(e));
  check(!course.cache(generator,std::string(64,'a'),cache,e));
  check(course.death(generator,actor,e));
  check(course.state(generator,after,afterAlive));check(before.deathCount==after.deathCount&&before.dayNum==after.dayNum);
  check(course.retiredNative(actor,e));check(!registry.query(actor,id,token));
 };
 check(course.install({{generator,source}},realOrder,e));floors=0;
 check(course.initialize(generator,5,true,math,floor,e));check(course.unload(e));check(realOrder.releases==2);
 source.activation=21;realOrder.bindOK=false;
 check(course.install({{generator,source}},realOrder,e));floors=0;
 check(!course.initialize(generator,5,true,math,floor,e));check(course.unload(e));check(realOrder.releases==3);
 // Missing typed SaveCreature loader is explicit, not successful empty load.
 source.reserved=3;check(course.install({{generator,source}},provider,e));check(!course.initialize(generator,6,false,math,floor,e));check(e.find("saved-creature payload")!=std::string::npos);check(course.unload(e));
 std::cout<<"PASS original native group coordinator "<<checks<<" controls\n";
}
