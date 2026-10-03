#pragma once
#include <cmath>
#include <vector>
namespace p2original { namespace wisp {
struct Key {int frame=0,type=0;};
// SysShape::Animator::animate: strict integer key comparison, discard loop
// overshoot, and END at authored duration. FSM reads the last event that tick.
struct Clock {
 float frame=0;unsigned next=0;bool stopped=false,completed=false;
 void start(bool stop){frame=0;next=0;stopped=stop;completed=false;}
 int advance(float dt,int duration,const std::vector<Key>& keys){
  if(stopped||completed)return -1;
  frame+=dt*30;int event=-1;int loopStart=-1;
  for(unsigned i=0;i<next;++i)if(keys[i].type==0)loopStart=keys[i].frame;
  while(next<keys.size()&&keys[next].frame<int(frame)){
   const Key key=keys[next++];event=key.type;
   if(key.type==0)loopStart=key.frame;
   if(key.type==1){frame=float(loopStart<0?0:loopStart);next=0;while(next<keys.size()&&keys[next].frame<frame)++next;return event;}
  }
  if(frame>=duration){frame=float(duration-1);completed=true;event=1000;}
  return event;
 }
};
} }
