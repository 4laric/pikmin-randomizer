#include "pc_p2_original_frog.h"
#include <cassert>
#include <cstdio>
using namespace p2original;
struct Fake: frog::Engine {
 int prepares=0,allocations=0,attached=0,destroyed=0;unsigned reserved=0;bool attachment=true;
 bool prepare(const std::vector<CatalogRow>&,std::string&)override{++prepares;return true;}
 bool reserve(unsigned n,std::string&)override{reserved=n;return true;}
 bool allocate(const CatalogRow&,Generator*,const Position&,float,Creature*& out,std::string&)override{out=reinterpret_cast<Creature*>(0x100+16*++allocations);return true;}
 bool attach(const CatalogRow&,Creature*,unsigned,unsigned,std::string&)override{++attached;return attachment;}
 bool destroy(Creature*,std::string&)override{++destroyed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="defaultgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=2;return r;}
int main(){
 std::string e;auto a=row(17,1),b=row(18,2);assert(frog::capability(a,e)&&frog::capability(b,e));
 auto invalid=b;invalid.enemy.generatorTail={"0"};Fake engine;frog::Provider provider(engine);
 assert(!provider.preflight({a,invalid},e)&&engine.prepares==0);
 invalid=b;invalid.enemy.generatorVersion="0000";assert(!frog::capability(invalid,e));
 invalid=b;invalid.enemy.enemySize=2;assert(frog::capability(invalid,e));
 invalid=b;invalid.enemy.uid++;assert(!frog::capability(invalid,e));
 invalid=b;invalid.enemy.treasureCode=1;assert(!frog::capability(invalid,e));
 assert(provider.preflight({a,b},e)&&engine.prepares==1);
 invalid=b;invalid.enemy.directionDegrees=45;assert(!provider.reserve({a,invalid},e)&&engine.reserved==0);
 assert(provider.reserve({b,a},e)&&engine.reserved==4);
 Creature* actor=nullptr;auto* generator=reinterpret_cast<Generator*>(0x40);
 assert(!provider.birth(invalid,generator,0,{},0,actor,e)&&engine.allocations==0);
 assert(provider.birth(a,generator,0,{1,2,3},0.5f,actor,e)&&actor);
 Creature* repeated=nullptr;assert(!provider.birth(a,generator,0,{},0,repeated,e));
 assert(provider.bind(a,actor,0x53000001,e));
 assert(!provider.preflight({a,b},e));assert(!provider.release(actor,9,e));
 assert(provider.release(actor,0x53000001,e)&&engine.destroyed==1);
 assert(provider.release(actor,0x53000001,e)&&engine.destroyed==1);
 assert(provider.birth(b,generator,1,{},0,actor,e));engine.attachment=false;
 assert(!provider.bind(b,actor,0x53000002,e));assert(provider.release(actor,0x53000002,e)&&engine.destroyed==2);
 assert(provider.preflight({a,b},e)&&provider.reserve({a,b},e));
 assert(provider.birth(a,generator,0,{},0,actor,e));provider.retired(actor);
 assert(provider.release(actor,0,e)&&engine.destroyed==2);
 std::puts("P2_ORIGINAL_FROG_CONTRACT_PASS");
}
