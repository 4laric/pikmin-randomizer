#pragma once
#include "pc_p2_animation.h"
#include <set>
#include <sstream>
namespace p2qurione {
inline bool bank(std::istream& in,std::vector<p2animation::Clip>& clips){
 std::string word;if(!(in>>word)||word!="P2_QURIONE_BANK_1")return false;
 std::vector<p2animation::Clip> result;
 for(const char* name:{"waitl","damage","run","appear1","hide1"}){
  p2animation::Clip c;if(!(in>>c.name>>c.count>>c.duration)||c.name!=name||c.count<2||c.count>10||c.duration<1||c.duration>10000)return false;
  for(int i=0;i<c.count;++i){int f;if(!(in>>f)||f<0||f>=c.duration||(i&&f<=c.frames.back()))return false;c.frames.push_back(f);}
  if(c.frames.front()!=0||c.frames.back()!=c.duration-1)return false;result.push_back(c);
 }
 if(in>>word)return false;clips=result;return true;
}
inline bool bindings(std::istream& in,std::set<std::uint32_t>& ids){
 ids.clear();std::string w;int count;if(!(in>>w>>count)||w!="P2_QURIONE_ACTORS_1"||count<1||count>8)return false;
 for(int i=0;i<count;++i){if(!(in>>w)||w.empty()||w.size()>10||w.find_first_not_of("0123456789")!=std::string::npos)return false;auto n=std::stoull(w);if(n>0xffffffffULL||!ids.insert(std::uint32_t(n)).second)return false;}
 return !(in>>w);
}
// Host state IDs from TAI/Mizinko.h. Hidden/dead states consume no visible draw.
inline const char* motion(int state,bool wait,bool damage,bool dead){
 if(state==1||state==3||state==6)return "hidden";
 if(state==4&&damage)return "damage";
 if(state==5&&dead)return "run";
 if((state==0||state==2)&&wait)return "waitl";
 return nullptr; // unmatched host motion delegates to ordinary native shape
}
}
