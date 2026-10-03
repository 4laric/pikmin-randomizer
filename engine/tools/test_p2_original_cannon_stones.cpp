#include "pc_p2_kabuto_stone_fleet.h"
#include "pc_p2_original_cannon_combat.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace p2kabutostone;
void tick(Fleet& fleet,const Target* target,int count,std::uint64_t active=0){
 Strike hits[64];DeadEvent deads[kFleetCapacity];Released releases[kFleetCapacity];int h=0,d=0,r=0;
 fleet.tick(0,nullptr,nullptr,target,count,hits,64,h,deads,kFleetCapacity,d,releases,kFleetCapacity,r,active);
}
int main(){
 // Check resulting receiver velocity, including wrap across zero, against
 // the source rule: faceDir + PI causes forward ejection, not its inverse.
 for(float face:{0.0f,.7f,3.2f,6.0f}){
  const float angle=p2original::cannon::pikminFlickAngle(face,false,1000.0f);
  assert(std::fabs(-std::sin(angle)-std::sin(face))<1e-5f);
  assert(std::fabs(-std::cos(angle)-std::cos(face))<1e-5f);
  assert(p2original::cannon::pikminFlickAngle(face,true,1000.0f)==1000.0f);
 }
 using p2original::cannon::FlickKey;using p2original::cannon::flickKey;
 assert(flickKey(false,30.0f/30.0f,0.0f)==FlickKey::None);
 assert(flickKey(false,31.0f/30.0f,0.0f)==FlickKey::FlickDead);
 assert(flickKey(false,31.0f/30.0f,1.0f)==FlickKey::Flick);
 assert(flickKey(true,32.0f/30.0f,0.0f)==FlickKey::None);
 Fleet fleet;std::uint32_t id=0;
 int homing=fleet.fire(9,{0,0,0},0,id,true,71.0f/30.0f);assert(homing>=0&&fleet.stone(homing).homing());
 Target targets[2];targets[0].token=10;targets[0].alive=targets[0].homingSearchable=true;targets[0].position={-100,0,100};targets[0].centre={-100,0,100};
 targets[1]=targets[0];targets[1].token=11;targets[1].position={1000,0,1000};targets[1].centre={1000,0,1000};
 tick(fleet,targets,2,11);assert(fleet.stone(homing).faceDir()>0); // active captain wins even outside search radius
 assert(std::fabs(fleet.stone(homing).targetVelocity().x)>0&&std::fabs(fleet.stone(homing).targetVelocity().z)<101);
 int straight=fleet.fire(9,{0,0,0},0,id,false,71.0f/30.0f);tick(fleet,targets,2,11);assert(!fleet.stone(straight).homing()&&std::fabs(fleet.stone(straight).faceDir())<1e-6f);
 assert(fleet.forgetOwner(9)==2);assert(fleet.stone(homing).sourceToken()==0&&!fleet.stone(homing).shouldIgnoreAtari(9)); // recycled shooter address receives no grace
 fleet.stone(homing);fleet.reset();
 homing=fleet.fire(9,{0,0,0},0,id,true);tick(fleet,targets,2);assert(std::sin(fleet.stone(homing).faceDir())<0); // no active captain: nearest searchable live target
 fleet.reset();targets[0].homingSearchable=false;targets[1].homingSearchable=false;
 homing=fleet.fire(9,{0,0,0},0,id,true);tick(fleet,targets,2);assert(std::fabs(fleet.stone(homing).faceDir())<1e-6f); // sprouts/dead/swallowed candidates never steer
 fleet.reset();
 for(int i=0;i<Fleet::capacity();++i)assert(fleet.fire(9,{0,0,0},0,id,true)>=0);
 assert(fleet.fire(9,{0,0,0},0,id,true)==-1);fleet.reset();assert(fleet.active()==0&&fleet.fire(9,{0,0,0},0,id,true)>=0);
 std::cout<<"original cannon homing, active captain, straight variant, orphan/reuse, capacity/reentry PASS\n";
}
