#include "pc_p2_original_group_engine.h"
#include "pc_p2_original_group.h"
#include "Generator.h"
#include "MapMgr.h"
#include "gameflow.h"
#include "netplay/pc_sim_rng.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
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
p2original::GroupCourse& pc_p2_original_groups(){static p2original::GroupCourse course(p2original::originalActors());return course;}
bool pc_p2_original_generator_init(Generator* generator,bool& handled,std::string& error){
 handled=pc_p2_original_groups().owns(generator);if(!handled)return true;
 p2original::Math math;
 math.draw=[](float& out,std::string&){out=pc_sim_randf(1.0f);return true;};
 math.sinCos=[](float angle,float& sine,float& cosine,std::string&){sine=std::sin(angle);cosine=std::cos(angle);return true;};
 math.squareRoot=[](float squared,float& out,std::string&){out=std::sqrt(squared);return true;};
 // Original map-null semantics preserve authored height; otherwise query the
 // actual installed terrain per actor immediately before its physical birth.
 auto floor=[](const p2original::Position& position,float& y,std::string&){y=mapMgr?mapMgr->getMinY(position.x,position.z,true):position.y;return true;};
 if(!pc_p2_original_groups().initialize(generator,unsigned(gameflow.mWorldClock.mCurrentDay),!Generator::ramMode,math,floor,error))return false;
 mirror(generator);return true;
}
bool pc_p2_original_generator_death(Generator* generator,Creature* creature,bool& handled,std::string& error){
 handled=pc_p2_original_groups().owns(generator);if(!handled)return true;
 if(!pc_p2_original_groups().death(generator,creature,error))return false;
 mirror(generator);return true;
}

void pc_p2_original_native_retired(Creature* creature){
 std::string error;
 if(!pc_p2_original_groups().retiredNative(creature,error)){
  std::fprintf(stderr,"P2_ORIGINAL_NATIVE_RETIRE_FAIL %s\n",error.c_str());std::abort();
 }
}
