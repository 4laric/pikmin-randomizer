#pragma once
#include "pc_p2_animation.h"
#include <map>
#include <set>
#include <limits>
namespace p2kogane {
struct Config{int karada=-1;std::map<std::uint32_t,int> ids;std::vector<p2animation::Clip> clips;};
inline bool read(std::istream& in,Config& out){
 Config c;std::string s;int count;
 if(!(in>>s)||s!="P2_KOGANE_NATIVE_1"||!(in>>s>>c.karada)||s!="karada"||c.karada<0||c.karada>64||!(in>>s>>count)||s!="actors"||count<1||count>100)return false;
 for(int i=0;i<count;++i){unsigned long long id;int species;if(!(in>>id>>species)||id>0xffffffffULL||species<9||species>11||!c.ids.emplace(std::uint32_t(id),species).second)return false;}
 std::set<std::string> seen;
 for(int n=0;n<3;++n){p2animation::Clip clip;if(!(in>>clip.name>>clip.count>>clip.duration)||!seen.insert(clip.name).second||(clip.name!="move"&&clip.name!="wait"&&clip.name!="damage")||clip.count<2||clip.count>24||clip.duration<1||clip.duration>10000)return false;
 for(int i=0;i<clip.count;++i){int f;if(!(in>>f)||f<0||f>=clip.duration||(i&&f<=clip.frames.back()))return false;clip.frames.push_back(f);}
 if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)return false;c.clips.push_back(clip);}
 if(in>>s)return false;out=c;return true;
}
inline int karada(int id){return id==9?60:id==10?100:id==11?15:-1;}
}
