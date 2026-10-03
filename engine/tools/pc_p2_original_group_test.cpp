#include "pc_p2_original_group.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace p2original;
static unsigned checks=0;
static void check(bool b){++checks;if(!b)throw std::runtime_error("group control "+std::to_string(checks));}
struct Provider:GroupProvider {
 int storage[10]{};unsigned births=0,releases=0,binds=0,preflightRows=0,reserveRows=0;bool admitted=true,reserved=true,releaseOK=true,bindOK=true,nullFirst=false,duplicate=false;
 std::vector<std::string> events;std::function<void(Creature*)> onRelease;
 bool preflight(const std::vector<CatalogRow>& rows,std::string&)override{preflightRows=unsigned(rows.size());events.push_back("preflight");return admitted;}
 bool reserve(const std::vector<CatalogRow>& rows,std::string&)override{reserveRows=unsigned(rows.size());events.push_back("reserve");return reserved;}
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
 // Retry after a partial attempt allocates a fresh identity; physical cleanup
 // remains retryable when the family refuses release.
 Provider pending;pending.releaseOK=false;
 check(course.install({{generator,source}},pending,e));floors=0;
 check(course.initialize(generator,5,true,math,floor,e));check(pending.births==2&&pending.binds==2);
 check(!course.unload(e));check(course.owns(generator)&&pending.releases==0);
 pending.releaseOK=true;check(course.unload(e));check(pending.releases==2&&!course.owns(generator));
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
 // Uncached literal reread resets source death counters but cannot replay the
 // preceding visit's actor identity, including same native pool addresses.
 source.reserved=0;source.activation=0;source.epoch=0;
 check(course.install({{generator,source}},provider,e));floors=0;
 check(course.initialize(generator,7,true,math,floor,e));check(course.state(generator,current,alive));
 const auto prior=current;check(current.deathCount==0&&current.dayNum==7&&alive==2);
 std::string frontier;check(course.encodeFrontier(frontier,e));check(frontier.size()==125);
 check(!course.decodeFrontier(std::string(64,'a'),frontier,e));check(course.unload(e));
 check(course.install({{generator,source}},provider,e));floors=0;
 check(course.initialize(generator,8,true,math,floor,e));check(course.state(generator,current,alive));
 check(current.epoch>prior.epoch&&current.activation>prior.activation&&current.deathCount==0&&current.dayNum==8);
 check(course.unload(e));check(course.decodeFrontier(std::string(64,'a'),frontier,e));
 // Same-process selected-checkpoint rollback merges identity marks, while a
 // new process adopts the saved frontier. Corruption refuses atomically.
 std::string latest;check(course.encodeFrontier(latest,e));check(latest!=frontier);
 check(!course.decodeFrontier(std::string(64,'b'),frontier,e));
 for(size_t length=0;length<frontier.size();++length)check(!course.decodeFrontier(std::string(64,'a'),frontier.substr(0,length),e));
 bad=frontier;bad[80]^=1;check(!course.decodeFrontier(std::string(64,'a'),bad,e));
 std::string unchanged;check(course.encodeFrontier(unchanged,e)&&unchanged==latest);
 IncarnationFrontier fresh;check(fresh.decode(std::string(64,'a'),frontier,e));
 check(fresh.encode(unchanged,e)&&unchanged==frontier);
 GenerationDecision decision;check(fresh.activate(source,9,true,decision,e));
 check(decision.next.epoch==prior.epoch+1&&decision.next.activation==prior.activation+1&&decision.next.dayNum==9&&decision.next.deathCount==0);
 IncarnationFrontier savedOnly;check(savedOnly.initialize(std::string(64,'a'),e));
 source.reserved=3;check(!savedOnly.activate(source,0,false,decision,e));
 check(savedOnly.encode(unchanged,e)&&unchanged.size()==105);
 IncarnationFrontier roundTrip;check(roundTrip.decode(std::string(64,'a'),unchanged,e));
 std::uint64_t typedActivation=99;
 check(!roundTrip.nextActivation(0,typedActivation,e)&&typedActivation==99);
 check(roundTrip.nextActivation(0x52000001u,typedActivation,e)&&typedActivation==1);
 check(roundTrip.encode(unchanged,e)&&unchanged.size()==125);
 IncarnationFrontier typedRestored;check(typedRestored.decode(std::string(64,'a'),unchanged,e));
 check(typedRestored.nextActivation(0x52000001u,typedActivation,e)&&typedActivation==2);
 // Calendar admission selects a strict subset without deleting inactive authority.
 CatalogRow inactive=row;inactive.index=1;inactive.sourceKey="tutorial/defaultgen.txt#1";inactive.enemy.uid=originalGeneratorUid(inactive.sourceKey);
 ActorRegistry calendarRegistry;check(calendarRegistry.install(std::string(64,'c'),{row,inactive},[](const CatalogRow&,std::string&){return true;},e));
 GroupCourse calendarCourse(calendarRegistry);Provider calendarProvider;GeneratorState active;active.uid=row.enemy.uid;active.count=row.enemy.count;
 check(!calendarCourse.install({{generator,active}},calendarProvider,e));check(calendarProvider.events.empty());
 check(calendarCourse.install({{generator,active}},calendarProvider,e,true));
 check(calendarProvider.preflightRows==1&&calendarProvider.reserveRows==1&&calendarProvider.births==0);
 check(calendarRegistry.rows().size()==2&&calendarRegistry.find(inactive.enemy.uid));check(calendarCourse.owns(generator));
 check(calendarCourse.unload(e));calendarProvider.events.clear();
 int secondNative=0;auto* secondGenerator=reinterpret_cast<Generator*>(&secondNative);
 check(!calendarCourse.install({{generator,active},{secondGenerator,active}},calendarProvider,e,true));check(calendarProvider.events.empty());
 check(calendarCourse.install({},calendarProvider,e,true));check(calendarProvider.preflightRows==0&&calendarProvider.reserveRows==0&&calendarProvider.births==0);
 check(calendarRegistry.rows().size()==2&&calendarCourse.unload(e));calendarProvider.events.clear();
 active.uid=0x12345678;check(!calendarCourse.install({{generator,active}},calendarProvider,e,true));check(calendarProvider.events.empty());
 std::cout<<"PASS original native group coordinator "<<checks<<" controls\n";
}
