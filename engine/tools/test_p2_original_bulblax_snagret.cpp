#include "pc_p2_original_bulblax_snagret.h"
#include "pc_p2_original_snagret_bank.h"
#include "pc_p2_original_snagret_death.h"

#include <sstream>
#include <fstream>
#include <cassert>
#include <iostream>
class Creature {};
class Generator {};
using namespace p2original;
struct Engine:bulblax_snagret::Engine {
 Creature physical[8];unsigned resourcesCalled=0,reserved=0,born=0,bound=0,killed=0;bool capacity=true,failBind=false,failCleanup=false,nullBirth=false,partialFailure=false,heldReady=false;
 bool resources(const CatalogRow& row,std::string& error)override{++resourcesCalled;if(row.enemy.treasureCode&&!heldReady){error="authenticated physical held treasure unavailable";return false;}return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return capacity;}
 bool allocate(bulblax_snagret::Host& h,const Position& p,float f,std::string&)override{assert(p.x==42&&f==1.25f);if(!nullBirth)h.actor=&physical[born];++born;return !partialFailure;}
 bool bind(bulblax_snagret::Host& h,std::string&)override{assert(h.token&&h.row.enemy.source>=33&&h.row.enemy.source<=34);++bound;return !failBind;}
 bool cleanup(bulblax_snagret::Host&,std::string&)override{if(failCleanup)return false;++killed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=3;r.enemy.deathCount=1;return r;}
int main(int argc,char** argv){
 std::string e;auto a=row(33,37),b=row(34,38),c=row(34,39);std::vector<CatalogRow> rows={a,b,c};
 // Literal day5 FireChappy watch must survive decode and reach resources.
 auto watch=row(33,17);watch.enemy.count=1;watch.enemy.deathCount=0;watch.enemy.treasureCode=841;
 assert(watch.enemy.uid==1382830758u&&bulblax_snagret::decode(watch,e));
 Engine held;bulblax_snagret::Provider heldProvider(held);
 assert(!heldProvider.preflight({watch},e)&&held.resourcesCalled==1&&!heldProvider.prepared());
 assert(!heldProvider.reserve({watch},e)&&held.reserved==0&&held.born==0);
 held.heldReady=true;assert(heldProvider.preflight({watch},e)&&heldProvider.prepared());
 auto unsupported=watch;unsupported.enemy.treasureCode=840;assert(!bulblax_snagret::decode(unsupported,e));
 unsupported=watch;unsupported.enemy.source=34;assert(!bulblax_snagret::decode(unsupported,e));
 for(const auto& r:rows){assert(bulblax_snagret::decode(r,e));assert(bulblax_snagret::nativeType(r.enemy.source)==(r.enemy.source==33?4:3));}
 auto invalid=a;invalid.enemy.source=15;assert(!bulblax_snagret::decode(invalid,e));invalid=a;invalid.enemy.generatorVersion="0000";assert(!bulblax_snagret::decode(invalid,e));invalid=a;invalid.enemy.generatorTail={"0"};assert(!bulblax_snagret::decode(invalid,e));
 Engine engine;bulblax_snagret::Provider p(engine);auto bad=rows;bad.back()=invalid;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
 assert(!p.preflight({},e)&&engine.resourcesCalled==0);bad=rows;bad.back().enemy.source=2;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
 for(unsigned variant=0;variant<5;++variant){bad=rows;auto& r=bad.back();
  if(variant==0)r.enemy.uid^=1;
  if(variant==1)r.sourceKey+="changed";
  if(variant==2)r.enemy.birthType=1;
  if(variant==3)r.enemy.treasureCode=7;
  if(variant==4)r.enemy.pelletColor=4;
  assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
 }
 assert(p.preflight(rows,e)&&engine.resourcesCalled==3);
 auto changed=rows;changed[0].enemy.pelletMinimum=2;assert(!p.reserve(changed,e)&&engine.reserved==0);
 assert(!p.reserve({a,b},e));engine.capacity=false;assert(!p.reserve(rows,e));engine.capacity=true;assert(p.reserve(rows,e)&&engine.reserved==6);
 Generator gen;Creature* actor=nullptr;Position pos{42,0,0};
 changed=rows;changed[0].sourceKey+="tampered";assert(!p.birth(changed[0],&gen,0,pos,1.25f,actor,e)&&!actor&&engine.born==0);
 assert(!p.birth(a,&gen,2,pos,1.25f,actor,e)&&engine.born==0);
 assert(p.birth(a,&gen,0,pos,1.25f,actor,e)&&actor==&engine.physical[0]);Creature* first=actor;
 assert(!p.birth(a,&gen,0,pos,1.25f,actor,e)&&!actor&&engine.born==1);
 assert(!p.bind(changed[0],first,700,e));engine.failBind=true;assert(!p.bind(a,first,700,e));
 // Failed bind retains the registry token for coordinated cleanup.
 assert(!p.release(first,0,e));engine.failCleanup=true;assert(!p.release(first,700,e)&&p.lookup(first));engine.failCleanup=false;assert(p.release(first,700,e)&&!p.lookup(first));
 assert(p.birth(a,&gen,1,pos,1.25f,actor,e));engine.failBind=false;assert(p.bind(a,actor,701,e));p.retired(actor);assert(!p.lookup(actor));
 assert(!p.birth(a,&gen,0,pos,1.25f,actor,e)&&engine.born==2); // reservation exhausted
 assert(engine.killed==1&&engine.bound==2);
 engine.nullBirth=true;assert(p.birth(b,&gen,0,pos,1.25f,actor,e)&&!actor);assert(!p.birth(b,&gen,0,pos,1.25f,actor,e));
 engine.nullBirth=false;engine.partialFailure=true;assert(!p.birth(b,&gen,1,pos,1.25f,actor,e)&&actor&&p.lookup(actor));assert(engine.killed==1);assert(p.release(actor,0,e)&&engine.killed==2);
 engine.partialFailure=false;assert(p.birth(c,&gen,0,pos,1.25f,actor,e));p.retired(actor);assert(!p.birth(c,&gen,0,pos,1.25f,actor,e)); // address retirement never authorizes ordinal reuse
 assert(!p.reserve(rows,e));assert(!p.birth(c,&gen,0,pos,1.25f,actor,e)); // repeated reservation cannot reopen attempts

 if(argc==2){std::ifstream bank(argv[1]);std::ostringstream bytes;bytes<<bank.rdbuf();
  std::istringstream valid(bytes.str());assert(bulblax_snagret::validateSnagretBank(valid,e));
  auto changed=bytes.str();changed.replace(changed.find("34:3"),4,"35:3");std::istringstream badTiming(changed);assert(!bulblax_snagret::validateSnagretBank(badTiming,e));
  changed=bytes.str();changed.replace(changed.find("dead 165"),8,"dead 166");std::istringstream badDuration(changed);assert(!bulblax_snagret::validateSnagretBank(badDuration,e));
  std::istringstream truncated(bytes.str().substr(0,200));assert(!bulblax_snagret::validateSnagretBank(truncated,e));
 }
 // Source death ordering: no drops before131; one atKEYEVENT3; END165
 // remains a separate corpse/retirement event. Crossed timesteps keep order.
 bulblax_snagret::DeathItems death;unsigned emitted=0;
 for(unsigned frame=1;frame<=180;++frame){const bool fired=death.advance(true,float(frame-1)/30,float(frame)/30);
  assert(fired==(frame==131));emitted+=fired;}
 assert(emitted==1);
 bulblax_snagret::DeathItems crossed;assert(!crossed.advance(true,0,130.0f/30));
 assert(crossed.advance(true,130.0f/30,140.0f/30));assert(!crossed.advance(true,140.0f/30,165.0f/30));
 bulblax_snagret::DeathItems ap;assert(!ap.advance(false,0,165.0f/30)&&!ap.emitted);
 bulblax_snagret::DeathItems invalidClock;assert(!invalidClock.advance(true,5,4)&&!invalidClock.emitted);
 std::cout<<"original Bulblax/Snagret literal admission, reservation, ordinal permanence and cleanup passed\n";
}
