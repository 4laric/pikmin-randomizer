#include "pc_p2_original_tank.h"
#include "pc_p2_original_tank_bank.h"
#include <sstream>
#include <fstream>
#include <cassert>
#include <iostream>
class Creature {};
class Generator {};
using namespace p2original;
struct Engine:tank::Engine {
 Creature physical[8];unsigned resourcesCalled=0,reserved=0,born=0,bound=0,killed=0;bool capacity=true,failBind=false,failCleanup=false,nullBirth=false,partialFailure=false;
 bool resources(const CatalogRow&,std::string&)override{++resourcesCalled;return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return capacity;}
 bool allocate(tank::Host& h,const Position& p,float f,std::string&)override{assert(p.x==42&&f==1.25f);if(!nullBirth)h.actor=&physical[born];++born;return !partialFailure;}
 bool bind(tank::Host& h,std::string&)override{assert(h.token&&h.row.enemy.source>=24&&h.row.enemy.source<=25);++bound;return !failBind;}
 bool cleanup(tank::Host&,std::string&)override{if(failCleanup)return false;++killed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=3;r.enemy.deathCount=1;return r;}
int main(int argc,char** argv){
 std::string e;auto a=row(24,29),b=row(24,30),c=row(25,31);std::vector<CatalogRow> rows={a,b,c};
 for(const auto& r:rows){assert(tank::decode(r,e));assert(tank::nativeType(r.enemy.source)==15);}
 auto invalid=a;invalid.enemy.source=15;assert(!tank::decode(invalid,e));invalid=a;invalid.enemy.generatorVersion="0000";assert(!tank::decode(invalid,e));invalid=a;invalid.enemy.generatorTail={"0"};assert(!tank::decode(invalid,e));
 Engine engine;tank::Provider p(engine);auto bad=rows;bad.back()=invalid;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
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

 // Actual day-5 corpus shape: Tank24 rows29/30, Wtank25 row31, ???? tail,
 // count1, birthType0, pellet5 min1/max2 p0.5. Admission does not discard drops.
 auto original=a;original.enemy.count=1;original.enemy.deathCount=0;
 original.enemy.pelletSize=5;original.enemy.pelletMinimum=1;original.enemy.pelletMaximum=2;original.enemy.pelletProbability=0.5f;
 assert(tank::decode(original,e));assert(original.sourceKey=="tutorial/initgen.txt#29");
 std::ostringstream bank;bank<<"P2_ORIGINAL_TANK_BANK_1\n";
 for(unsigned kind=0;kind<2;++kind){bank<<(kind?"Wtank 25":"Tank 24")<<"\n";
  const int durations[]={90,55,95,95,35,50,40};unsigned index=0;
  for(const char* name:{"dead","move1","flick","attack","waitact1","waitact2","type5"}){
   if(std::string(name)=="attack")bank<<"attack 3 95 0 55 94\n";
   else bank<<name<<" 2 "<<durations[index]<<" 0 "<<durations[index]-1<<"\n";
   ++index;
  }
 }
 tank::Banks parsed;std::istringstream valid(bank.str());assert(tank::parseBank(valid,parsed,e)&&parsed[0].size()==7&&parsed[1].size()==7);
 const auto fingerprint=parsed[0][3].frames;
 std::string badBank=bank.str();badBank.replace(badBank.find("Tank 24"),7,"Tank 15");std::istringstream wrongSpecies(badBank);assert(!tank::parseBank(wrongSpecies,parsed,e)&&parsed[0][3].frames==fingerprint);
 badBank=bank.str();badBank.replace(badBank.find("0 55 94"),7,"0 54 94");std::istringstream wrongEvent(badBank);assert(!tank::parseBank(wrongEvent,parsed,e));
 badBank=bank.str();badBank.replace(badBank.find("dead 2 90 0 89"),14,"dead 2 80 0 79");std::istringstream wrongDuration(badBank);assert(!tank::parseBank(wrongDuration,parsed,e));
 std::istringstream trailing(bank.str()+"AP_ACTOR 123");assert(!tank::parseBank(trailing,parsed,e));
 std::istringstream truncated(bank.str().substr(0,bank.str().size()/2));assert(!tank::parseBank(truncated,parsed,e));
 if(argc==2){std::ifstream actual(argv[1]);assert(tank::parseBank(actual,parsed,e));assert(parsed[0][3].duration==95&&parsed[1][3].duration==95);}
 std::cout<<"original Tank source/tail admission, whole-row reservation, grouped births and failed-bind cleanup passed\n";
}
