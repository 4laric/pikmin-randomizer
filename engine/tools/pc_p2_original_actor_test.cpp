#include "pc_p2_original_actor.h"
#include "pc_p2_original_lifecycle.h"
#include <iostream>
#include <stdexcept>
using namespace p2original;
static int checks=0;
static void check(bool b){++checks;if(!b)throw std::runtime_error("original actor test "+std::to_string(checks));}
int main(){
 ActorRegistry r;std::string e;CatalogRow row;row.course="tutorial";row.member="defaultgen.txt";row.sourceKey="tutorial/defaultgen.txt#0";
 row.enemy.uid=originalGeneratorUid(row.sourceKey);row.enemy.source=0;row.enemy.count=2;
 auto yes=[](const CatalogRow&,std::string&){return true;};
 check(r.install(std::string(64,'a'),{row},yes,e));
 int g=0,a=0,b=0;auto* gen=reinterpret_cast<Generator*>(&g);auto* one=reinterpret_cast<Creature*>(&a);auto* two=reinterpret_cast<Creature*>(&b);
 std::uint64_t gh=0,h1=0,h2=0;unsigned t1=0,t2=0;
 check(!r.actor(one,row.enemy.uid,0,1,t1,h1,e));check(t1==0&&h1==0);
 check(r.generator(gen,row.enemy.uid,gh,e));check(gh!=0);
 check(r.actor(one,row.enemy.uid,0,1,t1,h1,e));check(r.actor(two,row.enemy.uid,1,1,t2,h2,e));
 check(t1!=t2&&t1>=0x53000001u&&t2<=0x53ffffffu);
 unsigned source=999,token=0;InstanceIdentity identity;
 check(r.query(one,source,token,&identity));check(source==0&&token==t1);
 check(identity.generator==row.enemy.uid&&identity.ordinal==0&&identity.epoch==1&&identity.catalog==std::string(64,'a'));
 check(!r.retireGenerator(gen,gh));check(!r.install(std::string(64,'b'),{row},yes,e));
 check(!r.retire(one,h2));check(r.query(one,source,token));
 check(r.retire(one,h1));check(!r.query(one,source,token));
 auto old=t1;h1=0;t1=0;check(!r.actor(one,row.enemy.uid,0,1,t1,h1,e));check(t1==0&&h1==0);
 check(r.actor(one,row.enemy.uid,0,2,t1,h1,e));check(t1>old&&t1!=t2);
 check(r.retire(one,h1));check(r.retire(two,h2));check(r.retireGenerator(gen,gh));
 check(r.install(std::string(64,'b'),{row},yes,e));check(r.generator(gen,row.enemy.uid,gh,e));
 check(r.actor(one,row.enemy.uid,0,1,t1,h1,e));check(t1>t2);
 check(r.retire(one,h1));check(r.retireGenerator(gen,gh));
 check(!r.actor(nullptr,row.enemy.uid,0,1,t1,h1,e));
 source=777;token=888;check(!r.query(nullptr,source,token));check(source==777&&token==888);
 // Actual reserved5 RAM semantics: save group counters, unload both surviving
 // native associations, decode, advance course activation without source
 // respawn, and regenerate the remaining group under fresh transient handles.
 const std::string course(64,'c');check(r.install(course,{row},yes,e));check(r.generator(gen,row.enemy.uid,gh,e));
 check(r.actorActivation(one,row.enemy.uid,0,1,1,t1,h1,e));check(r.actorActivation(two,row.enemy.uid,1,1,1,t2,h2,e));
 InstanceIdentity previous;check(r.query(one,source,token,&previous));const auto oldHandle=h1;const auto oldToken=t1;const auto oldGenerator=gh;
 GeneratorState cached;cached.uid=row.enemy.uid;cached.count=2;cached.reserved=5;cached.resurrectionDays=2;cached.dayNum=5;cached.epoch=1;cached.activation=1;
 std::string wire;check(encodeOriginalState(course,cached,wire,e));
 check(r.retire(one,h1)&&r.retire(two,h2)&&r.retireGenerator(gen,gh));
 GeneratorState loaded;check(decodeOriginalState(course,row.enemy.uid,2,wire,loaded,e));GenerationDecision remaining;check(decideOriginalGeneration(loaded,6,false,remaining,e));
 check(remaining.generate&&remaining.remaining==2&&remaining.next.epoch==1&&!remaining.resetDeaths);
 GeneratorState activation;check(beginOriginalActivation(remaining.next,activation,e));check(activation.activation==2&&activation.epoch==1);
 check(r.generator(gen,row.enemy.uid,gh,e));check(gh!=oldGenerator&&!r.retireGenerator(gen,oldGenerator));
 check(!r.actorActivation(one,row.enemy.uid,0,1,1,t1,h1,e));check(r.actorActivation(one,row.enemy.uid,0,1,2,t1,h1,e));
 check(r.actorActivation(two,row.enemy.uid,1,1,2,t2,h2,e));check(h1!=oldHandle&&t1!=oldToken&&!r.retire(one,oldHandle));
 InstanceIdentity current;check(r.query(one,source,token,&current));check(!(current==previous)&&current.epoch==previous.epoch&&current.activation==2);
 check(r.retire(one,h1));check(!r.actorActivation(one,row.enemy.uid,0,1,2,t1,h1,e));
 check(r.retire(two,h2)&&r.retireGenerator(gen,gh));
 std::cout<<"PASS original actor registry "<<checks<<" controls\n";
}
