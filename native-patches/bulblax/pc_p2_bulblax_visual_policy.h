#pragma once
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
namespace p2bulblax {
inline const char* species(int id){return id==30?"Queen":id==31?"Baby":id==53?"KingChappy":nullptr;}
inline bool clipName(int id,const std::string& name){
 const std::string names=id==30?" dead sleep wait1 damage flick rolling_l rolling_r born carry ":id==31?" dead deadpress move attack attackfail born ":id==53?" attack cry damage dead dive flick move1 type1 type2 type3 wait2 waitact1 waitact2 carry ":"";
 return !name.empty()&&name.size()<=24&&name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_")==std::string::npos&&names.find(" "+name+" ")!=std::string::npos;
}
struct Clip {int enemy=0,duration=0;std::string name;std::vector<int> frames;
 size_t index(float sourceFrame)const{if(!std::isfinite(sourceFrame))throw std::runtime_error("invalid frame");sourceFrame=std::fmod(std::fmax(0.f,sourceFrame),float(duration));size_t best=0;for(size_t i=1;i<frames.size();++i)if(std::fabs(frames[i]-sourceFrame)<std::fabs(frames[best]-sourceFrame))best=i;return best;}
};
struct Display{uint32_t id;size_t clip;float x,y,z,yaw;};
struct Profile{std::vector<Clip> clips;std::vector<Display> displays;};
inline Profile read(std::istream& in){
 auto fail=[](){throw std::runtime_error("invalid Bulblax display profile");};
 Profile p;std::string magic;int count;if(!(in>>magic>>count)||magic!="P2_BULBLAX_VISUAL_1"||count<1||count>29)fail();
 std::set<std::pair<int,std::string>> seen;
 for(int i=0;i<count;++i){Clip c;int n;if(!(in>>c.enemy>>c.name>>c.duration>>n)||!species(c.enemy)||!clipName(c.enemy,c.name)||!seen.insert({c.enemy,c.name}).second||c.duration<1||c.duration>10000||n<1||n>12)fail();
 for(int j=0;j<n;++j){int f;if(!(in>>f)||f<0||f>=c.duration||(j&&f<=c.frames.back()))fail();c.frames.push_back(f);}p.clips.push_back(c);}
 if(!(in>>count)||count<1||count>8)fail();
 std::set<uint32_t> ids;
 for(int i=0;i<count;++i){unsigned long long id;int enemy;std::string name;Display d{};
 if(!(in>>id>>enemy>>name>>d.x>>d.y>>d.z>>d.yaw)||id>0xffffffffULL||!ids.insert(uint32_t(id)).second||!std::isfinite(d.x)||!std::isfinite(d.y)||!std::isfinite(d.z)||!std::isfinite(d.yaw)||std::fabs(d.x)>100000||std::fabs(d.y)>100000||std::fabs(d.z)>100000||std::fabs(d.yaw)>360)fail();
 d.id=uint32_t(id);d.clip=p.clips.size();for(size_t k=0;k<p.clips.size();++k)if(p.clips[k].enemy==enemy&&p.clips[k].name==name)d.clip=k;if(d.clip==p.clips.size())fail();p.displays.push_back(d);}
 if(in>>magic)fail();
 return p;
}
}
