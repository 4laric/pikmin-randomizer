#include "pc_p2_original_group_engine.h"
#include "pc_p2_original_group.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_course.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_retail_cave_native.h"
#include "Generator.h"
#include "MapMgr.h"
#include "gameflow.h"
#include "netplay/pc_sim_rng.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
p2original::GroupCourse& groupCourse(){static p2original::GroupCourse course(p2original::originalActors());return course;}
void mirror(Generator* generator){
 p2original::GeneratorState state;unsigned alive=0;
 if(!pc_p2_original_groups().state(generator,state,alive))return;
 // These compatibility fields are observations only. Original death/respawn
 // behavior is owned by the typed state, not P1 latest-spawn-on-last-death.
 generator->mAliveCount=int(alive);generator->mLatestSpawnDay=int(state.dayNum);
 generator->mRespawnInterval=state.resurrectionDays;generator->mDayLimit=state.dayLimit;
 generator->mCarryOverFlags=state.reserved;generator->mLatestSpawnCreature=nullptr;
}
}
const p2original::GroupCourse& pc_p2_original_groups(){return groupCourse();}
bool pc_p2_original_course_install(const std::vector<p2original::GroupBinding>& bindings,p2original::GroupProvider& provider,std::string& error,bool selectedInventory){
 // Real engine entry cannot bypass common physical-drop admission. All rows
 // are checked before provider reservation, RNG, actor construction or bind.
 for(const auto& binding:bindings){const auto* row=p2original::originalActors().find(binding.state.uid);if(!row||!pc_p2_original_drop_resources(*row,error))return false;}
 return groupCourse().install(bindings,provider,error,selectedInventory);
}
bool pc_p2_original_course_unload(std::string& error){return groupCourse().unload(error);}
bool pc_p2_original_incarnation_encode(std::string& bytes,std::string& error){return groupCourse().encodeFrontier(bytes,error);}
bool pc_p2_original_incarnation_initialize(const std::string& campaign,std::string& error){return groupCourse().initializeFrontier(campaign,error);}
bool pc_p2_original_incarnation_next(unsigned uid,std::uint64_t& activation,std::string& error){return groupCourse().nextActivation(uid,activation,error);}
bool pc_p2_original_incarnation_decode(const std::string& campaign,const std::string& bytes,std::string& error){return groupCourse().decodeFrontier(campaign,bytes,error);}
bool pc_p2_original_generator_init(Generator* generator,bool& handled,std::string& error){
 if(pc_p2_original_course_shadow(generator)){handled=true;error.clear();return true;}
 handled=pc_p2_original_groups().owns(generator);if(!handled)return true;
 p2original::Math math;
 math.draw=[](float& out,std::string&){out=pc_sim_randf(1.0f);return true;};
 math.sinCos=[](float angle,float& sine,float& cosine,std::string&){sine=std::sin(angle);cosine=std::cos(angle);return true;};
 math.squareRoot=[](float squared,float& out,std::string&){out=std::sqrt(squared);return true;};
 // Original map-null semantics preserve authored height; otherwise query the
 // actual installed terrain per actor immediately before its physical birth.
 auto floor=[](const p2original::Position& position,float& y,std::string&){y=mapMgr?mapMgr->getMinY(position.x,position.z,true):position.y;return true;};
 const unsigned day=pc_p2_original_course_prepared()?p2original::originalProgress().context().day:unsigned(gameflow.mWorldClock.mCurrentDay);
 if(!groupCourse().initialize(generator,day,!Generator::ramMode,math,floor,error))return false;
 mirror(generator);return true;
}
bool pc_p2_original_generator_death(Generator* generator,Creature* creature,bool& handled,std::string& error){
 handled=pc_p2_original_groups().owns(generator);if(!handled)return true;
 if(!groupCourse().death(generator,creature,error))return false;
 mirror(generator);return true;
}

void pc_p2_original_native_retired(Creature* creature){
 std::string error;
 if(!groupCourse().retiredNative(creature,error)){
  std::fprintf(stderr,"P2_ORIGINAL_NATIVE_RETIRE_FAIL %s\n",error.c_str());std::abort();
 }
 pc_p2_original_course_retired(creature);
 if(!pc_p2_retail_cave_native_retired(creature,error)){
  std::fprintf(stderr,"P2_RETAIL_NATIVE_RETIRE_FAIL %s\n",error.c_str());std::abort();
 }
}
