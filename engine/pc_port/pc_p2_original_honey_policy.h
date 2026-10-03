#pragma once
#include "pc_p2_original_resource_contents.h"
#include <cmath>
namespace p2originalresource { namespace honey {
enum class Phase { Fall, Bounce, Wait, Shrink, Touch, Dead };
// Source itemHoney.cpp/Honey.h state table. Shrink remains absorbable until
// its real animation key event kills the body, allowing shared nectar/spray.
struct Policy {
 Phase phase=Phase::Fall; HoneyKind kind=HoneyKind::Nectar; bool jiggling=false;
 bool alive()const{return phase!=Phase::Dead;}
 bool absorbable()const{return phase==Phase::Wait||phase==Phase::Touch||phase==Phase::Shrink;}
 unsigned motion()const{return phase==Phase::Fall?0:phase==Phase::Bounce?3:phase==Phase::Wait?4:phase==Phase::Touch?5:6;}
 bool bounce(){if(phase!=Phase::Fall)return false;phase=Phase::Bounce;return true;}
 bool absorb(){if(!absorbable())return false;phase=Phase::Shrink;return true;}
 bool key(){if(phase==Phase::Bounce||phase==Phase::Touch){phase=Phase::Wait;return true;}if(phase==Phase::Shrink){phase=Phase::Dead;return true;}return false;}
 bool contact(float vx,float vz,bool piki,bool navi,bool otherHoney){
  if(phase==Phase::Touch&&navi&&!jiggling){jiggling=true;return false;}
  if(phase!=Phase::Wait||vx*vx+vz*vz<100)return false;
  if((kind==HoneyKind::Nectar?!piki:!navi)&&!otherHoney){phase=Phase::Touch;jiggling=false;return true;}return false;
 }
};
// Retail Absorb receiver protocol, independent of native P1 WaterItem.
struct Drink {
 bool loop=false,absorbed=false,finishing=false;unsigned ticks=0;
 bool shouldAbsorb(bool live)const{return loop&&live&&!absorbed;}
 void absorbedOnce(){absorbed=true;}
 void pikiTick(){if(!absorbed&&++ticks>180){absorbed=true;ticks=180;}}
 void loopStart(){loop=true;}
 bool pikiLoopEnd(bool alive,bool shrinking){if(!alive||absorbed||!shrinking){loop=false;finishing=true;return true;}return false;}
 bool naviLoopEnd(bool alive,bool shrinking){if(!alive||!shrinking){loop=false;finishing=true;return true;}return false;}
};
struct SourceKey {float frame=0;int type=0;};
struct ReceiverClip {
 float duration=0,loopStart=-1,loopEnd=-1;std::vector<SourceKey> keys;
 bool valid()const{
  if(!std::isfinite(duration)||duration<=0||duration>10000||keys.size()>4096)return false;
  if((loopStart<0)!=(loopEnd<0)||!std::isfinite(loopStart)||!std::isfinite(loopEnd))return false;
  if(loopStart>=0&&!(loopStart<loopEnd&&loopEnd<=duration))return false;
  float previous=-1;bool start=false,end=false;
  for(const auto& k:keys){if(!std::isfinite(k.frame)||k.frame<0||k.frame>=duration||k.frame<previous||k.type<0||k.type>=1000)return false;previous=k.frame;if(k.type==0&&k.frame==loopStart)start=true;if(k.type==1&&k.frame==loopEnd)end=true;}
  return loopStart<0||(start&&end);
 }
};
// Mechanical clock uses actual P2 authored keys (0/1/2/1000); P1 character
// animation is presentation only. A loop-end handler can finish the source
// loop during this advance. SysShape::Animator::animate (0x80428F78) uses
// key.frame < int(timer), discards overshoot on an unfinished loop, and emits
// synthetic END1000 exactly once when timer>=duration.
struct ReceiverClock {
 float frame=0;std::size_t next=0;bool complete=false;
 void reset(){frame=0;next=0;complete=false;}
 template<class Emit>bool advance(const ReceiverClip& clip,float amount,bool& finishing,Emit emit){
  if(!clip.valid()||!std::isfinite(amount)||amount<0)return false;
  if(complete)return true;
  frame+=amount;
  if(!std::isfinite(frame)||frame>1000000)return false;
  while(next<clip.keys.size()&&clip.keys[next].frame<static_cast<int>(frame)){
   int type=clip.keys[next++].type;if(!emit(type))return true;
   if(type==1&&!finishing&&clip.loopStart>=0){frame=clip.loopStart;next=0;while(next<clip.keys.size()&&clip.keys[next].frame<frame)++next;return true;}
  }
  if(frame>=clip.duration){frame=clip.duration-1;complete=true;(void)emit(1000);}
  return true;
 }
};
} }
