#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
// Fixture-only captured-pose admission reserve. No future animation sweep claim.
class PcPurplePoseEnvelope {
public:
 struct Part {unsigned id=0;std::uintptr_t key=0;float horizontal=0,low=0,high=0,radius=0,lowX=0,highX=0,lowZ=0,highZ=0;};
 bool observe(std::uintptr_t owner,std::uintptr_t key,unsigned id,float x,float y,float z,float radius,float yaw=0) {
  if(failed_||!owner||!key||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||!std::isfinite(radius)||radius<=0||!std::isfinite(yaw))return fail();
  if(owner_&&owner_!=owner)return fail();
  owner_=owner;
  const float horizontal=std::hypot(x,z),localX=std::cos(yaw)*x-std::sin(yaw)*z,localZ=std::sin(yaw)*x+std::cos(yaw)*z;
  if(!std::isfinite(horizontal)||!std::isfinite(localX)||!std::isfinite(localZ))return fail();
  for(unsigned i=0;i<count_;++i)if(parts_[i].id==id){
   Part& p=parts_[i];if(p.key!=key)return fail();
   p.horizontal=std::max(p.horizontal,horizontal);p.low=std::min(p.low,y);p.high=std::max(p.high,y);p.radius=std::max(p.radius,radius);
   p.lowX=std::min(p.lowX,localX);p.highX=std::max(p.highX,localX);p.lowZ=std::min(p.lowZ,localZ);p.highZ=std::max(p.highZ,localZ);return true;
  }
  if(count_==parts_.size())return fail();
  parts_[count_++]={id,key,horizontal,y,y,radius,localX,localX,localZ,localZ};return true;
 }
 const Part* find(unsigned id,std::uintptr_t key) const {
  if(failed_)return nullptr;
  for(unsigned i=0;i<count_;++i)if(parts_[i].id==id&&parts_[i].key==key)return &parts_[i];
  return nullptr;
 }
 static bool projectedRadius(const Part& p,float relativeY,float otherRadius,float& radius,float halfArc=3.141592654f/8.f) {
  if(!std::isfinite(halfArc)||halfArc<0||halfArc>3.141592654f||!std::isfinite(relativeY)||!std::isfinite(otherRadius)||otherRadius<=0
   ||!std::isfinite(p.horizontal)||p.horizontal<0||!std::isfinite(p.low)||!std::isfinite(p.high)||p.low>p.high
   ||!std::isfinite(p.radius)||p.radius<=0||!std::isfinite(p.lowX)||!std::isfinite(p.highX)||p.lowX>p.highX
   ||!std::isfinite(p.lowZ)||!std::isfinite(p.highZ)||p.lowZ>p.highZ)return false;
  const float dy=std::max(0.f,std::max(p.low-relativeY,relativeY-p.high)-.1f),sum=p.radius+otherRadius+1.f;
  if(!std::isfinite(dy)||!std::isfinite(sum))return false;
  const float spread=std::hypot((p.highX-p.lowX)*.5f,(p.highZ-p.lowZ)*.5f);
  const float centre=std::hypot((p.highX+p.lowX)*.5f,(p.highZ+p.lowZ)*.5f);
  // Three yaw samples at -halfArc,0,+halfArc. Any intermediate offset lies
  // within this chord reserve of a sample. Captured animation box only.
  const float chord=2.f*centre*std::sin(halfArc/4.f);
  radius=dy>=sum?0.f:std::sqrt(sum*sum-dy*dy)+spread+chord;return std::isfinite(radius);
 }
 static bool rotatedOffset(const Part& p,float yaw,float& x,float& z){
  if(!std::isfinite(yaw)||!std::isfinite(p.lowX)||!std::isfinite(p.highX)||!std::isfinite(p.lowZ)||!std::isfinite(p.highZ))return false;
  const float lx=(p.lowX+p.highX)*.5f,lz=(p.lowZ+p.highZ)*.5f;
  x=std::cos(yaw)*lx+std::sin(yaw)*lz;z=-std::sin(yaw)*lx+std::cos(yaw)*lz;
  return std::isfinite(x)&&std::isfinite(z);
 }
private:
 bool fail(){failed_=true;return false;}
 std::array<Part,32> parts_{};unsigned count_=0;std::uintptr_t owner_=0;bool failed_=false;
};

// Native classic cursor displacement and source tangent projection at its cap.
inline bool pcPurpleCursorStep(float x,float z,float dx,float dz,float speed,float dt,float cap,float& nextX,float& nextZ){
 if(!std::isfinite(x)||!std::isfinite(z)||!std::isfinite(dx)||!std::isfinite(dz)||std::fabs(std::hypot(dx,dz)-1.f)>.001f
  ||!std::isfinite(speed)||speed<0||!std::isfinite(dt)||dt<=0||dt>1.f/30.f||!std::isfinite(cap)||cap<=0)return false;
 float vx=dx*speed,vz=dz*speed;nextX=x+vx*dt;nextZ=z+vz*dt;
 const float length=std::hypot(nextX,nextZ);if(!std::isfinite(length))return false;
 if(length>=cap){if(length<=0)return false;const float ux=nextX/length,uz=nextZ/length,dot=ux*vx+uz*vz;
  vx-=dot*ux;vz-=dot*uz;nextX=x+vx*dt;nextZ=z+vz*dt;}
 return std::isfinite(nextX)&&std::isfinite(nextZ)&&std::hypot(nextX,nextZ)>0;
}

// navi.cpp movement-neutral classic cursor: displacement <=speed*dt,
// then yaw +=0.2*shortest(cursor angle-yaw). Tangent clipping is a projection.
inline bool pcPurpleCursorYawBound(float yaw,float cursorX,float cursorZ,float speed,float dt,float& halfArc){
 if(!std::isfinite(yaw)||!std::isfinite(cursorX)||!std::isfinite(cursorZ)||!std::isfinite(speed)||speed<0
  ||!std::isfinite(dt)||dt<=0||dt>1.f/30.f)return false;
 const float cursor=std::hypot(cursorX,cursorZ),step=speed*dt;
 if(!std::isfinite(cursor)||cursor<=0||!std::isfinite(step)||step>=cursor)return false;
 halfArc=.2f*(std::fabs(std::remainder(std::atan2(cursorX,cursorZ)-yaw,6.283185307f))+std::asin(step/cursor));
 return std::isfinite(halfArc)&&halfArc>=0&&halfArc<=3.141592654f;
}

constexpr float PcPurplePulseYawHalfArc=3.141592654f/8.f;
inline bool pcPurplePulseYawEligible(float yaw,float targetX,float targetZ,float cursorX,float cursorZ,float cursorSpeed,float faceAdjust,float maximumDt){
 if(!std::isfinite(yaw)||!std::isfinite(targetX)||!std::isfinite(targetZ)||!std::isfinite(cursorX)||!std::isfinite(cursorZ)
  ||!std::isfinite(cursorSpeed)||cursorSpeed<0||!std::isfinite(faceAdjust)||faceAdjust<0||!std::isfinite(maximumDt)
  ||maximumDt<=0||maximumDt>1.f/30.f)return false;
 const float factor=faceAdjust*maximumDt*10.f,target=std::hypot(targetX,targetZ),cursor=std::hypot(cursorX,cursorZ),step=cursorSpeed*maximumDt;
 if(!std::isfinite(factor)||factor>1||!std::isfinite(target)||target<=0||!std::isfinite(cursor)||cursor<=0||!std::isfinite(step)||step>=cursor)return false;
 const float movement=std::fabs(std::remainder(std::atan2(targetX,targetZ)-yaw,6.283185307f));
 const float neutral=std::fabs(std::remainder(std::atan2(cursorX,cursorZ)-yaw,6.283185307f))+std::asin(step/cursor);
 // Creature::moveRotation interpolates with factor[0,1]; the native
 // neutral cursor turn uses0.2. Both stay in this qualified shortest arc.
 // Tangent clamping cannot increase the one-tick cursor displacement.
 return std::isfinite(movement)&&std::isfinite(neutral)&&movement<=PcPurplePulseYawHalfArc&&neutral<=PcPurplePulseYawHalfArc;
}

// Retain compatible observed animation families rather than a lifetime union.
// This remains captured evidence, not an unseen animation/transition proof.
class PcPurpleMotionPoseCatalog {
 struct Entry {int upper=-1,lower=-1;PcPurplePoseEnvelope poses;};
 struct Identity {unsigned id=0;std::uintptr_t key=0;};
 std::array<Entry,16> entries_{};std::array<Identity,32> identities_{};
 unsigned count_=0,identityCount_=0,current_=0;std::uintptr_t owner_=0;bool selected_=false,failed_=false;
 bool fail(){failed_=true;return false;}
public:
 bool select(std::uintptr_t owner,int upper,int lower){
  if(failed_||!owner||upper<0||upper>=256||lower<0||lower>=256||(owner_&&owner_!=owner))return fail();
  owner_=owner;
  for(unsigned i=0;i<count_;++i)if(entries_[i].upper==upper&&entries_[i].lower==lower){current_=i;selected_=true;return true;}
  if(count_==entries_.size())return fail();
  current_=count_++;entries_[current_].upper=upper;entries_[current_].lower=lower;selected_=true;return true;
 }
 bool observe(std::uintptr_t owner,std::uintptr_t key,unsigned id,float x,float y,float z,float radius,float yaw=0){
  if(failed_||!selected_||owner!=owner_||!key)return fail();
  bool known=false;
  for(unsigned i=0;i<identityCount_;++i)if(identities_[i].id==id){if(identities_[i].key!=key)return fail();known=true;break;}
  if(!known){if(identityCount_==identities_.size())return fail();identities_[identityCount_++]={id,key};}
  return entries_[current_].poses.observe(owner,key,id,x,y,z,radius,yaw)?true:fail();
 }
 const PcPurplePoseEnvelope::Part* find(unsigned id,std::uintptr_t key)const{
  return failed_||!selected_?nullptr:entries_[current_].poses.find(id,key);
 }
};

// Fail closed on finite-input float overflow in fixture segment admission.
inline bool pcPurpleSegmentCircleClear(float ax,float az,float bx,float bz,float cx,float cz,float radius,float margin){
 if(!std::isfinite(ax)||!std::isfinite(az)||!std::isfinite(bx)||!std::isfinite(bz)||!std::isfinite(cx)||!std::isfinite(cz)
   ||!std::isfinite(radius)||radius<0||!std::isfinite(margin)||margin<0)return false;
 const float dx=bx-ax,dz=bz-az,ox=cx-ax,oz=cz-az,sum=radius+margin;
 if(!std::isfinite(dx)||!std::isfinite(dz)||!std::isfinite(ox)||!std::isfinite(oz)||!std::isfinite(sum))return false;
 const float square=dx*dx+dz*dz,numerator=ox*dx+oz*dz;
 if(!std::isfinite(square)||square<0||!std::isfinite(numerator))return false;
 const float ratio=square>0?numerator/square:0;
 if(!std::isfinite(ratio))return false;
 const float t=std::max(0.f,std::min(1.f,ratio)),x=ax+dx*t,z=az+dz*t;
 const float ex=x-cx,ez=z-cz;
 if(!std::isfinite(x)||!std::isfinite(z)||!std::isfinite(ex)||!std::isfinite(ez))return false;
 const float distance=std::hypot(ex,ez);
 return std::isfinite(distance)&&distance>=sum;
}
