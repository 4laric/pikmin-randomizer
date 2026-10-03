#pragma once
#include <algorithm>
#include <cmath>
#include <array>
#include <map>
#include <istream>
#include <string>
#include <vector>
#include "pc_p2_original_hanachirashi_bank.h"
namespace p2hana {
constexpr float Pi=3.14159265358979323846f;
struct V {float x=0,y=0,z=0;};
inline V add(V a,V b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline V sub(V a,V b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
inline float dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline V mul(V a,float b){return {a.x*b,a.y*b,a.z*b};}
inline V unit(V a){float n=std::sqrt(dot(a,a));return n>0?mul(a,1/n):V{};}
inline float wrap(float a){while(a>Pi)a-=2*Pi;while(a< -Pi)a+=2*Pi;return a;}
inline V yaw(V a,float h){float c=std::cos(h),s=std::sin(h);return {c*a.x+s*a.z,a.y,-s*a.x+c*a.z};}
inline bool wind(V emitter,float heading,V target,float radius,bool captain,V& result){
 V direction=unit({std::sin(heading),-.85f,std::cos(heading)}),normal=unit({-direction.z,0,direction.x});
 V cross=unit({normal.y*direction.z-normal.z*direction.y,normal.z*direction.x-normal.x*direction.z,normal.x*direction.y-normal.y*direction.x});
 V separation=sub(target,emitter);float forward=dot(direction,separation);
 if(forward<=0||forward>=radius)return false;
 float cone=forward*std::tan(20.f*Pi/180),x=dot(normal,separation),y=dot(cross,separation),square=x*x+y*y;
 if(square>=cone*cone)return false;
 float slide=std::sqrt(square)/cone;V flat=unit({direction.x,0,direction.z});
 float strength=captain?slide*.2f+(1-slide):(1-slide)*5+slide;
 result={strength*(flat.x*y+normal.x*x),captain?0.f:(1-slide)*50+slide*10,strength*(flat.z*y+normal.z*x)};return true;
}
enum State{Dead=0,Wait=1,Move=2,Chase=3,ChaseInside=4,Attack=5,Fall=6,Land=7,Ground=8,TakeOff=9,FlyFlick=10,GroundFlick=11,Laugh=12};
inline int flyingNext(float health,unsigned stuck,unsigned purple,float timer){if(health<=0)return Dead;if(purple)return Fall;if(timer>1.f||stuck>=4)return stuck<4?FlyFlick:Fall;return -1;}
inline bool airborne(State state,float time){return state==Fall?time<=.75f:state==TakeOff?time>=1.f:(state==Wait||state==Move||state==Chase||state==ChaseInside||state==Attack||state==FlyFlick||state==Laugh||state==Dead);}
struct Clock {bool key2=false,end=false;};
inline Clock advanceClock(const std::string& motion,float& frame,bool finished,bool& event2,float dt,unsigned duration){
 Clock result;float prior=frame;frame+=dt*30;
 int key=-1;if(motion=="attack")key=50;else if(motion=="damage")key=15;else if(motion=="flick")key=25;else if(motion=="type1")key=30;
 if(key>=0&&!event2&&prior<float(key)&&frame>=float(key)){event2=true;result.key2=true;}
 if(!finished){int first=-1,last=-1;if(motion=="move1"||motion=="wait2"){first=0;last=39;}else if(motion=="type2"){first=5;last=19;}
  if(last>=0&&frame>=float(last))frame=float(first)+std::fmod(frame-float(first),float(last-first));
 }
 if(frame>=float(duration)){frame=float(duration-1);result.end=true;}
 return result;
}
struct Joint{V centre;std::array<float,9> rotation{};};
struct Sample{V emitter;std::array<Joint,9> parts;};
using JointBank=std::map<std::string,std::vector<Sample>>;
inline bool readJoints(std::istream& in,JointBank& bank,std::string& error){
 auto fail=[&](const char* e){error=e;return false;};std::string word;unsigned source=0,count=0,parts=0;
 if(!(in>>word>>source>>count>>parts)||word!="P2_HANACHIRASHI_JOINTS_1"||source!=55||count!=11||parts!=9)return fail("source55 complete joint bank header missing");
 JointBank staged;
 for(unsigned clip=0;clip<count;++clip){std::string name;int duration=0;if(!(in>>word>>name>>duration)||word!="clip")return fail("joint clip header missing");
  auto literal=p2original::hanachirashi::retailClocks().find(name);if(literal==p2original::hanachirashi::retailClocks().end()||duration!=literal->second.duration||staged.count(name))return fail("joint bank literal duration changed");
  auto& frames=staged[name];
  for(int frame=0;frame<duration;++frame){unsigned index=0;Sample sample;if(!(in>>word>>index)||word!="frame"||index!=unsigned(frame))return fail("joint bank frame identity changed");
   auto scalar=[&](float& n){return bool(in>>n)&&std::isfinite(n)&&std::fabs(n)<=10000;};
   if(!scalar(sample.emitter.x)||!scalar(sample.emitter.y)||!scalar(sample.emitter.z))return fail("joint emitter sample missing");
   for(auto& part:sample.parts){if(!scalar(part.centre.x)||!scalar(part.centre.y)||!scalar(part.centre.z))return fail("joint collider centre missing");for(float& n:part.rotation)if(!scalar(n))return fail("joint rotation missing");}
   frames.push_back(sample);
  }
 }
 if(in>>word)return fail("trailing joint bank data");bank=std::move(staged);error.clear();return true;
}
inline Sample sample(const JointBank& bank,const std::string& clip,float frame){
 const auto& frames=bank.at(clip);float f=std::max(0.f,std::min(frame,float(frames.size()-1)));auto a=size_t(f),b=std::min(a+1,frames.size()-1);float ratio=f-float(a);Sample result=frames[a];
 auto lerp=[&](float x,float y){return x+(y-x)*ratio;};result.emitter={lerp(result.emitter.x,frames[b].emitter.x),lerp(result.emitter.y,frames[b].emitter.y),lerp(result.emitter.z,frames[b].emitter.z)};
 for(size_t i=0;i<9;++i){auto& p=result.parts[i];const auto& q=frames[b].parts[i];p.centre={lerp(p.centre.x,q.centre.x),lerp(p.centre.y,q.centre.y),lerp(p.centre.z,q.centre.z)};for(size_t j=0;j<9;++j)p.rotation[j]=lerp(p.rotation[j],q.rotation[j]);}return result;
}
}
