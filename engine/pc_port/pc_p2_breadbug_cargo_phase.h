#pragma once
#include <cmath>
namespace p2breadbugcargo {
enum Kind {Fallback=-1,Hidden=-2,Back=0,Hide=1};
struct Selection {Kind kind;float frame;};
inline float unit(float v){return v<0?0:(v>1?1:v);}
// P1's counter and key bounds are authoritative; repeated draws cannot advance time.
inline Selection select(int state,bool cargo,bool matchingMotion,float counter,int duration,float loopStart,float loopEnd){
 if(state==9)return {Hidden,0};
 if(!cargo||!matchingMotion||!std::isfinite(counter)||duration<2)return {Fallback,0};
 if(state==8)return {Hide,48.f*unit(counter/float(duration-1))};
 if(state!=5&&state!=6)return {Fallback,0};
 if(!std::isfinite(loopStart)||!std::isfinite(loopEnd)||loopStart<=0||loopEnd<=loopStart||loopEnd>=duration)return {Fallback,0};
 if(state==5)return {Back,10.f*unit(counter/loopStart)};
 return {Back,10.f+29.f*unit((counter-loopStart)/(loopEnd-loopStart))};
}
}
