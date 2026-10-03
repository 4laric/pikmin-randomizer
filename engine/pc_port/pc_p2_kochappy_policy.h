#pragma once
#include "pc_p2_animation.h"
#include <istream>
#include <sstream>
#include <set>
#include <string>
#include <cstdint>

namespace p2kochappy {
class Health {
    bool active=false;
    std::set<const void*> actors;
public:
    void reset(){active=false;actors.clear();}
    bool read(std::istream& in){
        reset();std::string header,key,species,health,value,extra;
        if(!(in>>header>>key>>species>>health>>value) || header!="P2_KOCHAPPY_PROFILE_1" || key!="species" || species!="Kochappy" || health!="health" || value!="200" || in>>extra)return false;
        active=true;return true;
    }
    bool bind(const void* actor){return active && actor && actors.insert(actor).second;}
    void forget(const void* actor){actors.erase(actor);}
    float life(const void* actor,float fallback)const{return active && actors.count(actor)?200.f:fallback;}
};
inline bool bank(std::istream& in,std::vector<p2animation::Clip>& clips){
    std::string header;if(!(in>>header) || header!="P2_KOCHAPPY_BANK_1")return false;
    // Shared timing syntax only. Species registration never enters the Snow registry.
    std::ostringstream normalized;normalized<<"P2_SNOW_2 "<<in.rdbuf();
    std::istringstream parsed(normalized.str());
    return p2animation::parse(parsed,clips);
}
inline bool originalPressAccepted(unsigned source,bool registered,float health,bool ownerPiki,bool ownerAlive,bool bittered){
 return (source==1||source==45)&&registered&&std::isfinite(health)&&health>0&&ownerPiki&&ownerAlive&&!bittered;
}
inline const char* originalClip(int state){
 switch(state){case 0:return "wait1";case 1:return "dead";case 2:case 6:return "waitact1";case 3:case 7:return "move1";case 4:return "attack";case 5:return "flick";case 8:return "type1";default:return nullptr;}
}
inline bool originalFrame(int state,float seconds,bool corpse,const char*& clip,float& frame){
 if(!std::isfinite(seconds)||seconds<0)return false;
 clip=corpse?"dead":originalClip(state);if(!clip)return false;
 const int duration=corpse||state==1?90:state==0?75:state==2||state==6?25:state==3||state==7?55:state==4?90:state==5?80:105;
 frame=corpse?float(duration-1):seconds*30;
 if(!std::isfinite(frame))return false;
 if(!corpse&&(state==0||state==3||state==7))frame=std::fmod(frame,float(duration));
 frame=std::min(frame,float(duration-1));return true;
}
// Original Red source motions, including Turn/Press rather than visual aliases.
inline bool originalBank(std::istream& in,std::vector<p2animation::Clip>& out){
 std::string magic;if(!(in>>magic)||magic!="P2_KOCHAPPY_BANK_2")return false;
 const char* names[]={"wait1","move1","attack","dead","flick","waitact1","type1"};
 const int durations[]={75,55,90,90,80,25,105};std::vector<p2animation::Clip> next;
 for(int n=0;n<7;++n){p2animation::Clip clip;
  if(!(in>>clip.name>>clip.count>>clip.duration)||clip.name!=names[n]||clip.duration!=durations[n]||clip.count<2||clip.count>64)return false;
  for(int j=0;j<clip.count;++j){int frame;if(!(in>>frame)||frame<0||frame>=clip.duration||(j&&frame<=clip.frames.back()))return false;clip.frames.push_back(frame);}
  if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)return false;next.push_back(std::move(clip));
 }
 if(in>>magic)return false;out=std::move(next);return true;
}
inline bool bindings(std::istream& in,std::set<std::uint32_t>& ids){
    ids.clear();std::string word;int count;
    if(!(in>>word>>count) || word!="P2_KOCHAPPY_ACTORS_1" || count<1 || count>100)return false;
    for(int i=0;i<count;++i){
        if(!(in>>word) || word.empty() || word.size()>10 || word.find_first_not_of("0123456789")!=std::string::npos)return false;
        unsigned long long id=std::stoull(word);if(id>0xffffffffULL || !ids.insert(static_cast<std::uint32_t>(id)).second)return false;
    }
    return !(in>>word);
}
}
