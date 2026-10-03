#include "pc_p2_original_shijimi_state.h"
namespace p2original { namespace shijimi {
namespace {
bool reject(std::string& e,const char* message){e=message;return false;}
bool retire(ActorState& actor,StateEngine& engine,std::string& e){
 if(!engine.kill(actor,e))return false;
 actor.running=false;return true;
}
bool transition(ActorState& a,Phase phase,StateEngine& engine,std::string& e){
 a.phase=phase;
 switch(phase){
 case Phase::Fly:a.flyTime=0;a.flyTimer=0;return engine.nextGoal(a,e);
 case Phase::Fall:a.fallTimer=0;return engine.fallInit(a,e);
 case Phase::Dead:return engine.deadInit(a,e);
 case Phase::Leave:return engine.leaveInit(a,e);
 case Phase::Wait:return reject(e,"Wait initialization belongs to original onInit");
 }
 return reject(e,"unknown original Spectralid state");
}
}
bool update(ActorState& a,StateEngine& engine,std::string& e){
 if(!a.running){e.clear();return true;}
 switch(a.phase){
 case Phase::Wait:
  ++a.waitTimer;
  if(a.waitTimer>10){
   if(!a.leader||engine.nearestPikmin(a))return transition(a,Phase::Fly,engine,e);
  }else if(a.leader&&!engine.leaderInit(a,e))return false;
  return engine.fly(a,e);
 case Phase::Fly:
  if(a.leader||!engine.leaderWaiting(a))++a.flyTime;
  if(a.flyTimer==10){if(!engine.fade(a,e))return false;}else ++a.flyTimer;
  if(a.flyTime>250)return transition(a,Phase::Leave,engine,e);
  return engine.fly(a,e);
 case Phase::Fall:
  if(!engine.fall(a,e))return false;
  if(engine.fallEnd(a)){
   if(!engine.fade(a,e)||!transition(a,Phase::Dead,engine,e))return false;
  }else if(a.fallTimer>100&&!transition(a,Phase::Dead,engine,e))return false;
  ++a.fallTimer;e.clear();return true;
 case Phase::Dead:
  if(engine.deadEndKey(a)){
   if(!engine.drop(a,e)||!retire(a,engine,e))return false;
  }
  e.clear();return true;
 case Phase::Leave:return engine.leave(a,e);
 }
 return reject(e,"unknown original Spectralid state");
}
bool simulate(ActorState& a,StateEngine& engine,std::string& e){
 if(a.running&&engine.stuckPiki(a)&&!a.stuckToPiki&&a.phase!=Phase::Dead){
  if(a.leader)return reject(e,"hidden original leader cannot accept Pikmin attachment");
  if(!engine.latchEffectAndShrink(a,e))return false;
  a.stuckToPiki=true;
  return transition(a,Phase::Fall,engine,e);
 }
 e.clear();return true;
}
bool culled(ActorState& a,StateEngine& engine,std::string& e){
 if(a.running&&!a.leader&&(engine.leaderLeaving(a)||engine.outsideTerritory(a)))return retire(a,engine,e);
 e.clear();return true;
}
bool cluster(ActorState& a,StateEngine& engine,std::string& e){
 if(a.running&&a.leader&&a.groupCount<=1&&a.phase!=Phase::Wait)return retire(a,engine,e);
 e.clear();return true;
}
} }
