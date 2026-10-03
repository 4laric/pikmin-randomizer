#include "pc_p2_original_hanachirashi.h"
#include "pc_p2_original_hanachirashi_bank.h"
#include <sstream>
#include <fstream>
#include <cassert>
#include <iostream>
class Creature {};
class Generator {};
using namespace p2original;
struct Engine:hanachirashi::Engine {
 Creature physical[8];unsigned resourcesCalled=0,reserved=0,born=0,bound=0,killed=0;bool capacity=true,failBind=false,failCleanup=false,nullBirth=false,partialFailure=false;
 bool resources(const CatalogRow&,std::string&)override{++resourcesCalled;return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return capacity;}
 bool allocate(hanachirashi::Host& h,const Position& p,float f,std::string&)override{assert(p.x==42&&f==1.25f);if(!nullBirth)h.actor=&physical[born];++born;return !partialFailure;}
 bool bind(hanachirashi::Host& h,std::string&)override{assert(h.token&&h.row.enemy.source==55);++bound;return !failBind;}
 bool cleanup(hanachirashi::Host&,std::string&)override{if(failCleanup)return false;++killed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=3;r.enemy.deathCount=1;return r;}
int main(int argc,char** argv){
 std::string e;auto a=row(55,29),b=row(55,30),c=row(55,31);std::vector<CatalogRow> rows={a,b,c};
 for(const auto& r:rows){assert(hanachirashi::decode(r,e));assert(hanachirashi::nativeType(r.enemy.source)==16);}
 auto invalid=a;invalid.enemy.source=15;assert(!hanachirashi::decode(invalid,e));invalid=a;invalid.enemy.generatorVersion="0000";assert(!hanachirashi::decode(invalid,e));invalid=a;invalid.enemy.generatorTail={"0"};assert(!hanachirashi::decode(invalid,e));
 Engine engine;hanachirashi::Provider p(engine);auto bad=rows;bad.back()=invalid;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
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

 // Representative authored number-drop profile remains unchanged by admission.
 // This synthetic record exercises common fields, not a claim about source placement.
 auto original=a;original.enemy.count=1;original.enemy.deathCount=0;
 original.enemy.pelletSize=5;original.enemy.pelletMinimum=1;original.enemy.pelletMaximum=2;original.enemy.pelletProbability=0.5f;
 assert(hanachirashi::decode(original,e));assert(original.sourceKey=="tutorial/initgen.txt#29");
 std::ostringstream clocks;clocks<<"P2_FLYING_BANK_1\nspecies Hanachirashi clips 11\n";
 for(const auto& clip:hanachirashi::retailClocks())clocks<<"clip Hanachirashi "<<clip.first<<" "<<clip.second.duration<<" "<<clip.second.events<<" poses 2 status converted\n";
 auto valid=clocks.str();std::istringstream good(valid);assert(hanachirashi::validateBank(good,e));
 for(unsigned variant=0;variant<6;++variant){auto bad=valid;
  if(variant==0)bad.replace(bad.find("attack 105"),10,"attack 104");
  if(variant==1)bad.replace(bad.find("50:2"),4,"49:2");
  if(variant==2)bad.replace(bad.find("clips 11"),8,"54");
  if(variant==3)bad=bad.substr(0,bad.rfind("clip"));
  if(variant==4)bad.replace(bad.find("converted"),9,"missing");
  if(variant==5)bad+="AP_ACTOR 123\n";
  std::istringstream mutation(bad);assert(!hanachirashi::validateBank(mutation,e));
 }
 std::istringstream source55("P2_FLYING_BANK_1\nspecies Hanachirashi 55\n"+valid.substr(valid.find("clip Hanachirashi")));assert(hanachirashi::validateBank(source55,e));
 if(argc==2){std::ifstream actual(argv[1]);assert(hanachirashi::validateBank(actual,e));}
 std::cout<<"original Hanachirashi source/tail, grouped reservation, failed-bind cleanup and ordinal retirement passed\n";
}
