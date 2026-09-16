#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2material {
struct Key { double frame=0,value=0,in=0,out=0; };
using Curve=std::vector<Key>;
struct Track { std::string material; unsigned slot=0; std::array<double,3> center{}; std::array<Curve,5> curves; };
struct Bank { std::string source; unsigned duration=0,attribute=0,shift=0; std::vector<Track> tracks; };
struct Sample { double sx=1,sy=1,tx=0,ty=0,cx=0,cy=0; std::int16_t rotation=0; };
inline bool bounded(double v){return std::isfinite(v)&&std::abs(v)<=1e6;}
inline bool valid(const Bank& b){
 if(b.source.size()!=64||b.source.find_first_not_of("0123456789abcdef")!=std::string::npos||b.duration<1||b.duration>32767||(b.attribute!=0&&b.attribute!=2)||b.shift>15||b.tracks.empty()||b.tracks.size()>128)return false;
 std::set<std::pair<std::string,unsigned>> identities;
 std::size_t total=0;
 for(const auto& t:b.tracks){
  if(t.material.empty()||t.material.size()>128||t.material.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")!=std::string::npos||t.slot>9||!identities.insert({t.material,t.slot}).second)return false;
  for(double v:t.center)if(!bounded(v))return false;
  for(const auto& c:t.curves){
   if(c.empty()||c.size()>4096||(total+=c.size())>65536)return false;
   double prior=-1;
   for(const auto& k:c){if(!bounded(k.frame)||k.frame<0||k.frame>b.duration||k.frame<=prior||!bounded(k.value)||!bounded(k.in)||!bounded(k.out))return false;prior=k.frame;}
  }
 }
 return true;
}
inline Bank read(std::istream& in){
 auto bad=[](){throw std::runtime_error("Invalid P2 material SRT bank");};
 Bank b;std::string header;unsigned count;
 if(!(in>>header>>b.source>>b.duration>>b.attribute>>b.shift>>count)||header!="P2_MATERIAL_SRT_1"||count<1||count>128)bad();
 b.tracks.resize(count);
 std::size_t total=0;
 for(auto& t:b.tracks){
  if(!(in>>t.material>>t.slot>>t.center[0]>>t.center[1]>>t.center[2]))bad();
  for(auto& c:t.curves){unsigned n;if(!(in>>n)||n<1||n>4096||(total+=n)>65536)bad();c.resize(n);
   for(auto& k:c)if(!(in>>k.frame>>k.value>>k.in>>k.out))bad();
  }
 }
 std::string extra;if(in>>extra||!in.eof()||!valid(b))bad();return b;
}
inline double evaluate(const Curve& c,double frame){
 if(frame<=c.front().frame)return c.front().value;
 if(frame>=c.back().frame)return c.back().value;
 std::size_t hi=1;while(c[hi].frame<=frame)++hi;
 const Key& a=c[hi-1];const Key& b=c[hi];
 const double span=b.frame-a.frame,t=(frame-a.frame)/span,t2=t*t,t3=t2*t;
 return (2*t3-3*t2+1)*a.value+(t3-2*t2+t)*span*a.out+(-2*t3+3*t2)*b.value+(t3-t2)*span*b.in;
}
// Banks must be validated once and kept immutable. Frame comes from the actor's
// authoritative clock; this layer does not advance, loop, seek or infer pause.
inline bool sample(const Bank& b,std::size_t track,double frame,Sample& output){
 if(track>=b.tracks.size()||!std::isfinite(frame)||frame<0||frame>b.duration||b.shift>15)return false;
 const Track& t=b.tracks[track];for(const auto& c:t.curves)if(c.empty())return false;
 Sample s;s.sx=evaluate(t.curves[0],frame);s.sy=evaluate(t.curves[1],frame);
 const double rotation=evaluate(t.curves[2],frame);
 s.tx=evaluate(t.curves[3],frame);s.ty=evaluate(t.curves[4],frame);s.cx=t.center[0];s.cy=t.center[1];
 if(!bounded(s.sx)||!bounded(s.sy)||!bounded(rotation)||!bounded(s.tx)||!bounded(s.ty)||!bounded(s.cx)||!bounded(s.cy))return false;
 // J3D truncates interpolated rotation before scaling, then stores signed16.
 const auto units=static_cast<std::int64_t>(rotation)*(std::int64_t(1)<<b.shift);
 const auto wrapped=(units%65536+65536)%65536;
 s.rotation=static_cast<std::int16_t>(wrapped>=32768?wrapped-65536:wrapped);
 output=s;return true;
}
inline bool matrix(const Sample& s,double (&m)[2][3]){
 if(!bounded(s.sx)||!bounded(s.sy)||!bounded(s.tx)||!bounded(s.ty)||!bounded(s.cx)||!bounded(s.cy))return false;
 // JMath indexes a 2048-entry short-angle table. Quantize the same way;
 // host sin/cos can differ from the retail table by floating-point rounding.
 const unsigned index=static_cast<std::uint16_t>(s.rotation)>>5;
 const double angle=index*(6.2831853071795864769/2048.0),sn=std::sin(angle),cs=std::cos(angle);
 double candidate[2][3]={{s.sx*cs,-s.sx*sn,0},{s.sy*sn,s.sy*cs,0}};
 candidate[0][2]=-candidate[0][0]*s.cx-candidate[0][1]*s.cy+s.cx+s.tx;
 candidate[1][2]=-candidate[1][0]*s.cx-candidate[1][1]*s.cy+s.cy+s.ty;
 for(int i=0;i<2;++i)for(int j=0;j<3;++j)if(!bounded(candidate[i][j]))return false;
 for(int i=0;i<2;++i)for(int j=0;j<3;++j)m[i][j]=candidate[i][j];
 return true;
}
}
