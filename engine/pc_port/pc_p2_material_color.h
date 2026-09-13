#pragma once
#include "pc_p2_material_srt.h"
#include <algorithm>
#include <sstream>
#include <tuple>

namespace p2color {
struct Track {std::string material;unsigned kind=0,reg=0;std::array<p2material::Curve,4> curves;};
struct Bank {std::string source;unsigned duration=0,attribute=0;std::vector<Track> tracks;};
using Sample=std::array<std::int16_t,4>;
inline bool valid(const Bank& b){
 if(b.source.size()!=64||b.source.find_first_not_of("0123456789abcdef")!=std::string::npos||b.duration<1||b.duration>32767||(b.attribute!=0&&b.attribute!=2)||b.tracks.empty()||b.tracks.size()>128)return false;
 std::set<std::tuple<std::string,unsigned,unsigned>> ids;size_t total=0;
 for(const auto& t:b.tracks){
  if(t.material.empty()||t.material.size()>128||t.material.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")!=std::string::npos||t.kind>1||t.reg>(t.kind?3u:2u)||!ids.insert({t.material,t.kind,t.reg}).second)return false;
  for(const auto& c:t.curves){if(c.empty()||c.size()>4096||(total+=c.size())>65536)return false;double prior=-1;
   for(const auto& k:c){if(!std::isfinite(k.frame)||k.frame<0||k.frame>b.duration||k.frame<=prior)return false;prior=k.frame;
    for(double v:{k.value,k.in,k.out})if(!std::isfinite(v)||v<-32768||v>32767)return false;}
  }
 }return true;
}
inline Bank read(std::istream& source){
 auto bad=[](){throw std::runtime_error("Invalid P2 material color bank");};std::string bytes;char ch;
 while(source.get(ch)){if(bytes.size()>=4*1024*1024)bad();bytes+=ch;}if(!source.eof())bad();std::istringstream in(bytes);
 Bank b;std::string header;unsigned count;if(!(in>>header>>b.source>>b.duration>>b.attribute>>count)||header!="P2_MATERIAL_COLOR_1"||count<1||count>128)bad();b.tracks.resize(count);size_t total=0;
 for(auto& t:b.tracks){if(!(in>>t.material>>t.kind>>t.reg))bad();for(auto& c:t.curves){unsigned n;if(!(in>>n)||n<1||n>4096||(total+=n)>65536)bad();c.resize(n);for(auto& k:c)if(!(in>>k.frame>>k.value>>k.in>>k.out))bad();}}
 std::string extra;if(in>>extra||!in.eof()||!valid(b))bad();return b;
}
// Validated immutable bank; caller owns loop/pause. J3D constant channels bypass
// interpolation clamps: konst assignment wraps to u8, CReg preserves signed16.
inline bool sample(const Bank& b,size_t index,double frame,Sample& out){
 if(index>=b.tracks.size()||!std::isfinite(frame)||frame<0||frame>b.duration)return false;
 const auto& t=b.tracks[index];if(t.kind>1)return false;Sample next;
 for(size_t i=0;i<4;++i){const auto& c=t.curves[i];if(c.empty())return false;double v=p2material::evaluate(c,frame);if(!std::isfinite(v)||std::fabs(v)>1e9)return false;
  if(c.size()==1){if(v<-32768||v>32767)return false;auto n=static_cast<std::int16_t>(v);next[i]=t.kind?static_cast<std::uint8_t>(n):n;}
  else next[i]=static_cast<std::int16_t>(std::max(t.kind?0.0:-1024.0,std::min(t.kind?255.0:1023.0,v)));
 }out=next;return true;
}
}
