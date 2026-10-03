#include "pc_p2_original_snow.h"
#include "pc_p2_original_snow_bank.h"
#include <cassert>
#include <cstdio>
#include "pc_p2_kochappy_policy.h"
#include "pc_p2_kochappy_fsm_policy.h"
#include <sstream>
#include <fstream>
#include "pc_p2_pose_bank.h"
using namespace p2original;
struct Fake: snow::Engine {
 int prepares=0,allocations=0,attached=0,destroyed=0;unsigned reserved=0;bool attachment=true,allocation=true;
 bool prepare(const std::vector<CatalogRow>&,std::string&)override{++prepares;return true;}
 bool reserve(unsigned n,std::string&)override{reserved=n;return true;}
 bool allocate(const CatalogRow&,Generator*,const Position&,float,Creature*& out,std::string&)override{out=reinterpret_cast<Creature*>(0x100+16*++allocations);return allocation;}
 bool attach(const CatalogRow&,Creature*,unsigned,unsigned,std::string&)override{++attached;return attachment;}
 bool destroy(Creature*,std::string&)override{++destroyed;return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="defaultgen.txt";r.index=index;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=2;return r;}
int main(int argc,char** argv){
 std::string e;auto a=row(45,1),b=row(45,2);assert(snow::capability(a,e)&&snow::capability(b,e));
 auto invalid=b;invalid.enemy.generatorTail={"0"};Fake engine;snow::Provider provider(engine);
 assert(!provider.preflight({a,invalid},e)&&engine.prepares==0);
 invalid=b;invalid.enemy.generatorVersion="0000";assert(!snow::capability(invalid,e));
 invalid=b;invalid.enemy.enemySize=2;assert(snow::capability(invalid,e));
 invalid=b;invalid.enemy.uid++;assert(!snow::capability(invalid,e));
 invalid=b;invalid.enemy.treasureCode=1;assert(!snow::capability(invalid,e));
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
 engine.allocation=false;assert(provider.preflight({a,b},e)&&provider.reserve({a,b},e));
 assert(!provider.birth(a,generator,0,{},0,actor,e)&&actor);assert(provider.release(actor,0,e));
 engine.allocation=true;assert(!provider.birth(a,generator,0,{},0,actor,e));
 assert(p2kochappy::originalPressAccepted(45,true,200,true,true,false));
 assert(!p2kochappy::originalPressAccepted(44,true,200,true,true,false));
 assert(!p2kochappy::originalPressAccepted(45,false,200,true,true,false));
 assert(!p2kochappy::originalPressAccepted(45,true,0,true,true,false));
 assert(!p2kochappy::originalPressAccepted(45,true,200,false,true,false));
 assert(!p2kochappy::originalPressAccepted(45,true,200,true,false,false));
 assert(!p2kochappy::originalPressAccepted(45,true,200,true,true,true));
 auto params=p2kochappyfsm::snowDefaults();assert(params.health==150&&params.moveSpeed==50&&params.sight==95&&params.attackDamage==10);
 std::ostringstream bank;bank<<"P2_SNOW_BANK_1\n";
 const char* names[]={"wait1","move1","attack","dead","flick","waitact1","type1"};const int durations[]={75,55,90,90,80,25,105};
 for(int n=0;n<7;++n)bank<<names[n]<<" 2 "<<durations[n]<<" 0 "<<durations[n]-1<<"\n";
 std::vector<p2animation::Clip> parsed;std::istringstream valid(bank.str());assert(p2original::snow::bank(valid,parsed)&&parsed.size()==7);
 auto incomplete=bank.str();incomplete.erase(incomplete.find("waitact1"));std::istringstream partial(incomplete);assert(!p2original::snow::bank(partial,parsed)&&parsed.size()==7);
 auto wrong=bank.str();wrong.replace(wrong.find("25"),2,"26");std::istringstream changed(wrong);assert(!p2original::snow::bank(changed,parsed));
 std::istringstream legacy("P2_KOCHAPPY_BANK_1");assert(!p2original::snow::bank(legacy,parsed));
 const char* clip=nullptr;float frame=0;
 assert(p2kochappy::originalFrame(4,8.f/30,false,clip,frame)&&std::string(clip)=="attack"&&std::abs(frame-8)<0.001f);
 assert(p2kochappy::originalFrame(2,0.5f,false,clip,frame)&&std::string(clip)=="waitact1"&&frame==15);
 assert(p2kochappy::originalFrame(8,1,false,clip,frame)&&std::string(clip)=="type1"&&frame==30);
 assert(p2kochappy::originalFrame(3,60.f/30,false,clip,frame)&&std::string(clip)=="move1"&&frame==5);
 assert(p2kochappy::originalFrame(-1,0,true,clip,frame)&&std::string(clip)=="dead"&&frame==89);
 assert(!p2kochappy::originalFrame(4,-1,false,clip,frame));
 if(argc==2){const std::string directory=argv[1];std::ifstream index(directory+"/p2-snow.txt");std::vector<p2animation::Clip> bank;
  assert(index&&p2original::snow::bank(index,bank));std::vector<unsigned char> reference,topology;std::size_t total=0,poses=0;
  for(const auto& motion:bank){std::size_t clipBytes=0;for(int n=0;n<motion.count;++n){char filename[96];std::snprintf(filename,sizeof(filename),"/snow_%s_%02d.mod",motion.name.c_str(),n);
   std::ifstream file(directory+filename,std::ios::binary|std::ios::ate);assert(file);auto size=file.tellg();assert(size>0);file.seekg(0);
   std::vector<unsigned char> data(static_cast<std::size_t>(size),0),resources;assert(file.read(reinterpret_cast<char*>(data.data()),size));
   assert(p2animation::resources(data,resources));assert(reference.empty()||reference==resources);reference=resources;
   p2pose::Baked pose;assert(p2pose::decodeBaked(data,pose));assert(topology.empty()||topology==pose.topology);topology=pose.topology;
   clipBytes+=data.size();total+=data.size();++poses;
  }assert(clipBytes<=p2animation::ClipBytes);}assert(total<=p2animation::TotalBytes);std::printf("P2_ORIGINAL_SNOW_ACTUAL_BANK_PASS poses=%zu bytes=%zu resources_closed=1 baked_geometry=1\n",poses,total);
 }
 std::puts("P2_ORIGINAL_SNOW_CONTRACT_PASS");
}
