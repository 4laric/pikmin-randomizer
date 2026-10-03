#include "pc_p2_original_catfish.h"
#include "pc_p2_original_catfish_bank.h"

#include <sstream>
#include <fstream>
#include <cassert>
#include <iostream>
class Creature {};
class Generator {};
using namespace p2original;
struct Engine:catfish::Engine {
 Creature physical[8];unsigned resourcesCalled=0,reserved=0,born=0,bound=0,killed=0;bool capacity=true,failBind=false,failCleanup=false,nullBirth=false,partialFailure=false;
 bool resources(const CatalogRow&,std::string&)override{++resourcesCalled;return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return capacity;}
 bool allocate(catfish::Host& h,const Position& p,float f,std::string&)override{assert(p.x==42&&f==1.25f);if(!nullBirth)h.actor=&physical[born];++born;return !partialFailure;}
 bool bind(catfish::Host& h,std::string&)override{assert(h.token&&h.row.enemy.source==26);++bound;return !failBind;}
 bool cleanup(catfish::Host&,std::string&)override{if(failCleanup)return false;++killed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=3;r.enemy.deathCount=1;return r;}
int main(int argc,char** argv){
 std::string e;auto a=row(26,25),b=row(26,26),c=row(26,27);std::vector<CatalogRow> rows={a,b,c};
 for(const auto& r:rows){assert(catfish::decode(r,e));assert(catfish::nativeType(r.enemy.source)==30);}
 auto invalid=a;invalid.enemy.source=15;assert(!catfish::decode(invalid,e));invalid=a;invalid.enemy.generatorVersion="0000";assert(!catfish::decode(invalid,e));invalid=a;invalid.enemy.generatorTail={"0"};assert(!catfish::decode(invalid,e));
 Engine engine;catfish::Provider p(engine);auto bad=rows;bad.back()=invalid;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
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

 // Actual day-5 source26 rows25-28: ???? tail,
 // birthType0, pellet1 min1/max2 p0.4. Admission does not discard drops.
 auto original=a;original.enemy.count=1;original.enemy.deathCount=0;
 original.enemy.pelletSize=1;original.enemy.pelletMinimum=1;original.enemy.pelletMaximum=2;original.enemy.pelletProbability=0.4f;
 assert(catfish::decode(original,e));assert(original.sourceKey=="tutorial/initgen.txt#25");

 std::string bank="P2_AQUATIC_BANK_1\nspecies Catfish 26\n";
 const char* names[]={"attack","dead","flick","move1","type5","wait1","waitact2"};
 const unsigned durations[]={85,95,70,25,40,30,16};
 const char* events[]={"17:2,75:3","-","25:2,47:3","0:0,24:1","10:0,29:1","-","-"};
 for(unsigned i=0;i<7;++i)bank+="clip Catfish "+std::string(names[i])+" "+std::to_string(durations[i])+" "+events[i]+" poses 2 converted frames 0,"+std::to_string(durations[i]-1)+"\n";
 std::istringstream authored(bank);assert(catfish::validateCatfishBank(authored,e));
 for(unsigned variant=0;variant<4;++variant){std::string changedBank=bank;
  if(variant==0)changedBank.replace(changedBank.find("Catfish 26"),10,"Catfish 25");
  if(variant==1)changedBank.replace(changedBank.find("attack 85"),9,"attack 84");
  if(variant==2)changedBank.replace(changedBank.find("17:2"),4,"17:3");
  if(variant==3)changedBank.resize(changedBank.find("clip Catfish waitact2"));
  std::istringstream badBank(changedBank);assert(!catfish::validateCatfishBank(badBank,e));
 }
 if(argc==2){std::ifstream actual(argv[1]);assert(catfish::validateCatfishBank(actual,e));}
 std::cout<<"P2_ORIGINAL_CATFISH_PROVIDER PASS\n";
}
