#include "pc_p2_original_gate.h"
#include <cmath>
namespace p2original {
GateState gateInitial(const GateRecord& r){GateState s;s.health=r.segmentLife;return s;}
bool gateStateValid(const GateRecord& r,const GateState& s,std::string& e){
 if(!validateGate(r,e))return false;
 if(s.segmentsDown>3||!std::isfinite(s.health)||!std::isfinite(s.damage)||s.damage<0
  ||!std::isfinite(s.animationFrame)||s.animationFrame<0||s.animationFrame>65536
  ||(s.damageAnimationFinished&&s.phase!=GatePhase::Damaged)
  ||(s.phase==GatePhase::Wait&&s.damage!=0)
  ||(s.phase==GatePhase::Down&&s.health>=0)
  ||s.health>r.segmentLife||unsigned(s.phase)>unsigned(GatePhase::Open)
  ||(s.phase==GatePhase::Open)!=(s.segmentsDown==3)
  ||(s.phase==GatePhase::Open&&s.health!=r.segmentLife)
  ||(s.phase!=GatePhase::Down&&s.health<0)){
  e="invalid original gate physical state";return false;
 }
 e.clear();return true;
}
GateAction gateDamage(GateState& s,float value){
 if(s.phase==GatePhase::Open||!std::isfinite(value)||value<=0||!std::isfinite(s.damage+value))return GateAction::None;
 s.damage+=value;
 if(s.phase==GatePhase::Wait){s.phase=GatePhase::Damaged;s.damageAnimationFinished=false;s.animationFrame=0;return GateAction::DamageMotion;}
 return GateAction::None;
}
GateAction gateExec(GateState& s){
 if(s.phase!=GatePhase::Damaged)return GateAction::None;
 s.health-=s.damage;s.damage=0;
 if(s.health<0){s.phase=GatePhase::Down;s.damageAnimationFinished=false;s.animationFrame=0;return GateAction::DownMotion;}
 if(s.damageAnimationFinished){s.phase=GatePhase::Wait;s.damageAnimationFinished=false;s.animationFrame=0;return GateAction::Idle;}
 return GateAction::None;
}
GateAction gateAnimationKey(const GateRecord& r,GateState& s){
 if(s.phase==GatePhase::Damaged){s.damageAnimationFinished=true;return GateAction::None;}
 if(s.phase!=GatePhase::Down)return GateAction::None;
 ++s.segmentsDown;s.health=r.segmentLife;s.damageAnimationFinished=false;s.animationFrame=0;
 if(s.segmentsDown==3){s.phase=GatePhase::Open;return GateAction::Open;}
 if(s.damage>0){s.phase=GatePhase::Damaged;return GateAction::DamageMotion;}
 s.phase=GatePhase::Wait;return GateAction::Idle;
}
bool gateSettled(const GateRecord& r,const GateState& s,std::string& e){
 if(!gateStateValid(r,s,e))return false;
 if((s.phase!=GatePhase::Wait&&s.phase!=GatePhase::Open)
  ||(s.phase==GatePhase::Wait&&(s.damage!=0||s.damageAnimationFinished))
  ||(s.phase==GatePhase::Open&&s.health!=r.segmentLife)){e="gate save requires settled native animation state";return false;}
 e.clear();return true;
}
}
