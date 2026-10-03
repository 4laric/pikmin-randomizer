#include "pc_p2_original_shijimi_group.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <set>
using namespace p2original;
using namespace p2original::shijimi;
namespace {
InstanceIdentity parent{std::string(64,'a'),0x1234,0,2,3};
struct TestEngine final:Engine {
 bool available=true,spicy=false,bitter=false,nullHoney=false;
 float leaderSelection=0.15f,selection=0.15f;
 unsigned draws=0,discard=0,honeyBirths=0;
 int failed=-1,initFailure=-1;unsigned aborts=0;std::set<unsigned> born;
 std::vector<std::string> events;
 bool parent(const InstanceIdentity& id,unsigned source,std::string&)override{return id==::parent&&(source==50||source==87);}
 bool emission(const Group& g,std::string&)override{return g.origin.x==1&&g.origin.z==3&&g.origin.y==(g.plantSource==50?87:72);}
 bool managerAvailable()const override{return available;}
 float randFloat()override{events.push_back("rng");++draws;return draws==4?leaderSelection:selection;}
 void discardRand()override{events.push_back("discard");++discard;}
 bool birth(Child& c,void*& out,std::string&)override{
  events.push_back("birth"+std::to_string(c.identity.child));out=nullptr;
  if(int(c.identity.child)==failed)return true;
  randFloat(); // EnemyBase birth -> Shijimi setParameters scale
  out=reinterpret_cast<void*>(std::uintptr_t(c.identity.child+1));born.insert(c.identity.child);return true;
 }
 bool init(Child& c,void*,void* leader,std::string&)override{
  if(int(c.identity.child)==initFailure)return false;
  assert(leader==reinterpret_cast<void*>(1));events.push_back("init"+std::to_string(c.identity.child));
  assert(c.identity.child==0||c.color==Color::Yellow);
  randFloat();randFloat();return true;
 }
 bool leaderInit(Child&,void*,std::string&)override{events.push_back("leader-init");return true;}
 bool leaderColor(Child& c,void*,std::string&)override{assert(c.color==(leaderSelection<0.5f?Color::Purple:Color::Red));events.push_back("leader-color");return true;}
 bool appear(Child& c,void*,std::string&)override{assert(c.color==c.appearance);events.push_back("appear"+std::to_string(c.identity.child));return true;}
 bool abort(const Group&,std::string&)override{++aborts;born.clear();return true;}
 bool sprayMade(Color c)const override{return c==Color::Red?spicy:bitter;}
 bool honey(const Child&,const Position& p,const Position& v,bool& out,std::string&)override{
  assert(p.y==12&&v.y==200&&v.x==v.z);++honeyBirths;out=!nullHoney;if(out)randFloat();return true;
 }
};
}
int main(){
 std::string e;Group g;TestEngine engine;PlantGroups groups;
 assert(groups.touch(parent,50,{1,2,3},85,engine,g,e));
 assert(g.complete&&g.consumed&&g.managerPresent&&g.children[0].color==Color::Purple&&g.sourceGroupCount==4);
 assert(engine.draws==24&&engine.discard==1&&engine.born.size()==5);
 const std::vector<std::string> first{"birth0","rng","init0","rng","rng","leader-init","discard","rng","leader-color",
  "rng","birth1","rng","rng","appear1","init1","rng","rng"};
 assert(std::vector<std::string>(engine.events.begin(),engine.events.begin()+first.size())==first);
 assert(g.children[0].position.y==87&&g.children[1].position.y==69.5f&&g.children[1].home.y==69.5f);
 assert(groups.touch(parent,50,{1,2,3},85,engine,g,e)&&engine.draws==24); // no duplicate emission
 assert(groups.drop(g.children[1].identity,{0,10,0},0,false,engine,e));
 assert(engine.draws==25&&engine.honeyBirths==1); // plant skips nectar-rate RNG
 assert(groups.drop(g.children[1].identity,{0,10,0},0,false,engine,e)&&engine.honeyBirths==1);
 assert(groups.drop(g.children[0].identity,{0,10,0},0,false,engine,e)&&engine.honeyBirths==1); // bitter gate
 assert(groups.consume(g.children[1].identity,e));assert(groups.retire(g.children[1].identity,e));
 auto saved=groups.snapshot();PlantGroups restored;
 assert(restored.restore(saved,engine,e)&&engine.draws==25);assert(restored.snapshot()[0].children[1].dropConsumed);
 auto bad=saved;bad[0].children[1].identity.child=2;PlantGroups malformed;assert(!malformed.restore(bad,engine,e)&&malformed.snapshot().empty());
 bad=saved;bad[0].plant.activation=4;assert(!malformed.restore(bad,engine,e));
 bad=saved;bad[0].children[2].color=Color::Red;assert(!malformed.restore(bad,engine,e));
 // Source intentionally tolerates every subset of failed follower births.
 for(int failed=0;failed<5;++failed){TestEngine partial;partial.failed=failed;PlantGroups p;
  assert(p.touch(parent,87,{1,2,3},70,partial,g,e));
  assert(!g.children[unsigned(failed)].born&&g.complete);
  assert(partial.draws==(failed==0?0:20));assert(partial.discard==unsigned(failed!=0));
  assert(g.sourceGroupCount==unsigned(failed==0?0:failed==4?3:4));
  PlantGroups again;assert(again.restore(p.snapshot(),partial,e));
 }
 TestEngine absent;absent.available=false;PlantGroups noManager;
 assert(noManager.touch(parent,50,{1,2,3},85,absent,g,e)&&absent.draws==0&&g.consumed&&g.complete&&!g.managerPresent);
 absent.available=true;assert(noManager.touch(parent,50,{1,2,3},85,absent,g,e)&&absent.draws==0);
 TestEngine nullDrop;nullDrop.nullHoney=true;PlantGroups nullGroups;
 assert(nullGroups.touch(parent,50,{1,2,3},85,nullDrop,g,e));
 assert(nullGroups.drop(g.children[2].identity,{0,10,0},0,false,nullDrop,e)&&nullDrop.draws==24);
 assert(nullGroups.drop(g.children[2].identity,{0,10,0},0,false,nullDrop,e)&&nullDrop.honeyBirths==1);
 assert(!nullGroups.consume(g.children[2].identity,e));
 TestEngine failedInit;failedInit.initFailure=2;PlantGroups failedGroups;
 assert(!failedGroups.touch(parent,50,{1,2,3},85,failedInit,g,e)&&failedInit.aborts==1&&failedInit.born.empty());
 auto draws=failedInit.draws;assert(!failedGroups.touch(parent,50,{1,2,3},85,failedInit,g,e)&&failedInit.draws==draws);
 PlantGroups pendingRestore;assert(!pendingRestore.restore(failedGroups.snapshot(),failedInit,e));
 std::string encoded;assert(groups.encode(engine,encoded,e));PlantGroups decoded;
 assert(decoded.decode(encoded,engine,e)&&engine.draws==25);
 std::string roundTrip;assert(decoded.encode(engine,roundTrip,e)&&roundTrip==encoded);
 PlantGroups trailing;assert(!trailing.decode(encoded+"extra",engine,e)&&trailing.snapshot().empty());
 auto originBad=saved;originBad[0].origin.y=100;PlantGroups originRejected;assert(!originRejected.restore(originBad,engine,e));
 assert(!failedGroups.encode(failedInit,roundTrip,e));
 for(float roll:{0.05f,0.15f,0.9f}){TestEngine variants;variants.selection=roll;variants.leaderSelection=0.9f;variants.spicy=true;PlantGroups v;
  assert(v.touch(parent,50,{1,2,3},85,variants,g,e)&&g.children[0].color==Color::Red);
  const auto expected=roll<0.1f?Color::Red:roll<0.2f?Color::Purple:Color::Yellow;
  for(unsigned n=1;n<5;++n)assert(g.children[n].appearance==expected&&g.children[n].color==Color::Yellow);
  assert(v.drop(g.children[0].identity,{0,10,0},0,false,variants,e)&&variants.honeyBirths==1&&variants.draws==25);
 }
 std::puts("P2_ORIGINAL_SHIJIMI_GROUP_TEST PASS source-order partial-birth one-shot gated-drop no-init-restore");
}
