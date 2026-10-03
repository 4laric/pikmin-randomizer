#include "pc_p2_original_uji.h"
#include <cassert>
#include <iostream>
class Creature {};
class Generator {};
using namespace p2original;
struct Engine:uji::Engine {
 Creature physical[8];unsigned resourcesCalled=0,reserved=0,born=0,bound=0,killed=0;bool capacity=true,failBind=false,failCleanup=false,nullBirth=false,partialFailure=false;
 bool resources(const CatalogRow&,std::string&)override{++resourcesCalled;return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return capacity;}
 bool allocate(uji::Host& h,const Position& p,float f,std::string&)override{assert(p.x==42&&f==1.25f);if(!nullBirth)h.actor=&physical[born];++born;return !partialFailure;}
 bool bind(uji::Host& h,std::string&)override{assert(h.token&&h.row.enemy.source>=12&&h.row.enemy.source<=14);++bound;return !failBind;}
 bool cleanup(uji::Host&,std::string&)override{if(failCleanup)return false;++killed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="default.gen";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=3;r.enemy.deathCount=1;return r;}
int main(){
 std::string e;auto a=row(12,100),b=row(13,200),c=row(14,300);std::vector<CatalogRow> rows={a,b,c};
 for(const auto& r:rows){assert(uji::decode(r,e));assert(uji::nativeType(r.enemy.source)==int(r.enemy.source)+6);}
 auto invalid=a;invalid.enemy.source=3;assert(!uji::decode(invalid,e));invalid=a;invalid.enemy.generatorVersion="0000";assert(!uji::decode(invalid,e));invalid=a;invalid.enemy.generatorTail={"0"};assert(!uji::decode(invalid,e));
 Engine engine;uji::Provider p(engine);auto bad=rows;bad.back()=invalid;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
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
 std::cout<<"original Uji source/tail admission, whole-row reservation, grouped births and failed-bind cleanup passed\n";
}
