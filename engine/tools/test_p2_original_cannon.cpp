#include "pc_p2_original_cannon.h"
#include "pc_p2_original_cannon_bank.h"
#include "pc_p2_attachments.h"
#include <sstream>
#include <fstream>
#include <cassert>
#include <iostream>
class Creature {};
class Generator {};
using namespace p2original;
struct Engine:cannon::Engine {
 Creature physical[8];unsigned resourcesCalled=0,reserved=0,born=0,bound=0,killed=0;bool capacity=true,failBind=false,failCleanup=false,nullBirth=false,partialFailure=false;
 bool resources(const CatalogRow&,std::string&)override{++resourcesCalled;return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return capacity;}
 bool allocate(cannon::Host& h,const Position& p,float f,std::string&)override{assert(p.x==42&&f==1.25f);if(!nullBirth)h.actor=&physical[born];++born;return !partialFailure;}
 bool bind(cannon::Host& h,std::string&)override{assert(h.token&&h.row.enemy.source>=95&&h.row.enemy.source<=96);++bound;return !failBind;}
 bool cleanup(cannon::Host&,std::string&)override{if(failCleanup)return false;++killed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=3;r.enemy.deathCount=1;return r;}
int main(int argc,char** argv){
 std::string e;auto a=row(95,29),b=row(95,30),c=row(96,31);std::vector<CatalogRow> rows={a,b,c};
 for(const auto& r:rows){assert(cannon::decode(r,e));assert(cannon::nativeType(r.enemy.source)==17);}
 auto invalid=a;invalid.enemy.source=15;assert(!cannon::decode(invalid,e));invalid=a;invalid.enemy.generatorVersion="0000";assert(!cannon::decode(invalid,e));invalid=a;invalid.enemy.generatorTail={"0"};assert(!cannon::decode(invalid,e));
 Engine engine;cannon::Provider p(engine);auto bad=rows;bad.back()=invalid;assert(!p.preflight(bad,e)&&engine.resourcesCalled==0);
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


 std::ostringstream bank;bank<<"P2_ORIGINAL_CANNON_BANK_1\n";
 const char* names[]={"dead","move","flick","attack","pivot","wait","K_pivot","K_wait","K_attack","K_flick","K_dead","K_appear","K_hide","carry"};
 const int durations[]={90,55,82,95,35,50,35,50,95,82,90,36,18,40};
 for(int k=0;k<2;++k){bank<<(k?"Fkabuto 96\n":"Rkabuto 95\n");for(int i=0;i<14;++i)bank<<names[i]<<" 2 "<<durations[i]<<" 0 "<<durations[i]-1<<"\n";}
 cannon::Banks parsed;std::istringstream valid(bank.str());assert(cannon::parseBank(valid,parsed,e)&&parsed[0].size()==14&&parsed[1].size()==14);
 std::string badBank=bank.str();badBank.replace(badBank.find("Rkabuto 95"),10,"Rkabuto 75");std::istringstream badSource(badBank);assert(!cannon::parseBank(badSource,parsed,e)&&parsed[0].size()==14);
 badBank=bank.str();badBank.replace(badBank.find("K_attack 2 95"),13,"K_attack 2 94");std::istringstream badDuration(badBank);assert(!cannon::parseBank(badDuration,parsed,e));
 if(argc==4){
  std::ifstream originalBank(argv[1]),stoneBank(argv[2]),sockets(argv[3]);assert(cannon::parseBank(originalBank,parsed,e));std::vector<p2animation::Clip> stone;assert(cannon::parseStoneBank(stoneBank,stone,e));
  auto bank=p2attach::read(sockets);assert(bank&&bank->joint("mouth")>=0);p2attach::Instance instance;auto token=instance.bind(bank);assert(token);
  for(const char* clip:{"attack","K_attack"}){p2attach::Affine world,mouth;const float frame=std::string(clip)=="attack"?51.0f:56.0f;assert(instance.sample(token,bank->clip(clip),frame,world,unsigned(frame)));assert(instance.socket(token,bank->joint("mouth"),mouth));std::cout<<clip<<" posed_frame="<<frame<<" mouth="<<mouth.m[0][3]<<","<<mouth.m[1][3]<<","<<mouth.m[2][3]<<"\n";}
 }
 std::cout<<"original cannon strict admission, lifecycle ownership and authored banks PASS\n";
}
