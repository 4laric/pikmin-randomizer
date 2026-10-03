#include "pc_p2_original_armor.h"
#include <cassert>
#include <iostream>
class Creature{};class Generator{};
using namespace p2original;using namespace p2original::armor;
struct Control:Engine {
 Creature actor;unsigned resourcesCalled=0,reserved=0,births=0,cleanups=0;bool nullBirth=false,partial=false,bindFailure=false,cleanupFailure=false;
 bool resources(const std::set<unsigned>& s,std::string&)override{++resourcesCalled;return s==std::set<unsigned>({15});}
 bool commonResources(const CatalogRow&,std::string&)override{return true;}
 bool reserve(const std::vector<CatalogRow>&,unsigned n,std::string&)override{reserved=n;return true;}
 bool allocate(Host& h,const Position& p,float angle,std::string&)override{assert(p.x==10&&angle==.5f);++births;h.actor=nullBirth?nullptr:&actor;return !partial;}
 bool bind(Host& h,std::string&)override{assert(h.token==100);return !bindFailure;}
 bool cleanup(Host&,std::string&)override{++cleanups;return !cleanupFailure;}
};
CatalogRow retail(unsigned source=15){CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=32;r.sourceKey="tutorial/initgen.txt#32";r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=1;r.enemy.directionDegrees=0;r.enemy.generatorVersion="????";r.enemy.position={532.630676f,106.218262f,45.448071f};r.enemy.pelletMaximum=3;r.enemy.pelletProbability=.5f;return r;}
int main(){
 std::string e;auto r=retail();assert(admits(r,e));auto invalid=r;invalid.enemy.generatorVersion="0000";assert(!admits(invalid,e));
 invalid=r;invalid.enemy.generatorTail={"0"};assert(!admits(invalid,e));invalid=r;invalid.enemy.enemySize=2;assert(admits(invalid,e));
 invalid=r;invalid.enemy.birthType=1;assert(!admits(invalid,e));invalid=r;invalid.enemy.treasureCode=5;assert(!admits(invalid,e));
 invalid=r;invalid.enemy.uid++;assert(!admits(invalid,e));invalid=r;invalid.enemy.source=1;assert(!admits(invalid,e));
 invalid=r;invalid.member="different.txt";assert(!admits(invalid,e));invalid=r;invalid.index++;assert(!admits(invalid,e));invalid=r;invalid.course.clear();assert(!admits(invalid,e));invalid=r;invalid.enemy.source=1;
 Control c;Provider p(c);Generator g;Creature* out=nullptr;
 assert(!p.preflight({r,invalid},e)&&c.resourcesCalled==0);assert(!p.birth(r,&g,0,{10,0,0},.5f,out,e));
 assert(p.preflight({r},e));auto changed=r;changed.enemy.pelletProbability=.7f;assert(!p.reserve({changed},e));assert(p.reserve({r},e)&&c.reserved==1);
 assert(!p.birth(changed,&g,0,{10,0,0},.5f,out,e));assert(p.birth(r,&g,0,{10,0,0},.5f,out,e)&&out==&c.actor);
 assert(!p.birth(r,&g,0,{10,0,0},.5f,out,e));assert(p.bind(r,&c.actor,100,e));assert(!p.bind(r,&c.actor,100,e));
 assert(!p.release(&c.actor,101,e));c.cleanupFailure=true;assert(!p.release(&c.actor,100,e)&&p.size()==1);c.cleanupFailure=false;assert(p.release(&c.actor,100,e)&&p.size()==0);
 assert(!p.birth(r,&g,0,{10,0,0},.5f,out,e)); // A retired ordinal cannot be retried in an activation.
 Control nullEngine;nullEngine.nullBirth=true;Provider np(nullEngine);assert(np.preflight({r},e)&&np.reserve({r},e));
 assert(np.birth(r,&g,0,{10,0,0},.5f,out,e)&&!out);assert(!np.birth(r,&g,0,{10,0,0},.5f,out,e)&&nullEngine.births==1);
 Control broken;broken.partial=true;Provider bp(broken);assert(bp.preflight({r},e)&&bp.reserve({r},e));
 assert(!bp.birth(r,&g,0,{10,0,0},.5f,out,e)&&out==&broken.actor&&bp.size()==1);assert(bp.release(out,0,e));
 Control failedNull;failedNull.partial=true;failedNull.nullBirth=true;Provider fp(failedNull);
 assert(fp.preflight({r},e)&&fp.reserve({r},e));assert(!fp.birth(r,&g,0,{10,0,0},.5f,out,e)&&!out);
 assert(!fp.birth(r,&g,0,{10,0,0},.5f,out,e)&&failedNull.births==1);
 auto second=r;second.index=99;second.sourceKey="tutorial/initgen.txt#99";second.enemy.uid=originalGeneratorUid(second.sourceKey);
 Control entire;Provider ep(entire);assert(ep.preflight({r,second},e));assert(!ep.reserve({r},e));assert(ep.reserve({r,second},e)&&entire.reserved==2);
 Control binding;binding.bindFailure=true;Provider b(binding);assert(b.preflight({r},e)&&b.reserve({r},e));assert(b.birth(r,&g,0,{10,0,0},.5f,out,e));
 assert(!b.bind(r,out,100,e));assert(b.release(out,100,e));
 Control retired;Provider rp(retired);assert(rp.preflight({r},e)&&rp.reserve({r},e));assert(rp.birth(r,&g,0,{10,0,0},.5f,out,e));rp.retired(out);rp.retired(out);assert(rp.size()==0);
 std::cout<<"P2_ORIGINAL_ARMOR_CONTRACT PASS (controlled engine; no gameplay claim)\n";
}
