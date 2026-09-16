#pragma once
#include "pc_p2_animation.h"
#include <istream>
#include <sstream>
#include <set>
#include <string>
#include <cstdint>

namespace p2dwarforange {
class Health {
    bool active=false;
    std::set<const void*> actors;
public:
    void reset(){active=false;actors.clear();}
    bool read(std::istream& in){
        reset();std::string header,key,species,health,value,extra;
        if(!(in>>header>>key>>species>>health>>value) || header!="P2_DWARF_ORANGE_PROFILE_1" || key!="species" || species!="BlueKochappy" || health!="health" || value!="250" || in>>extra)return false;
        active=true;return true;
    }
    bool bind(const void* actor){return active && actor && actors.insert(actor).second;}
    void forget(const void* actor){actors.erase(actor);}
    float life(const void* actor,float fallback)const{return active && actors.count(actor)?250.f:fallback;}
};
inline bool bank(std::istream& in,std::vector<p2animation::Clip>& clips){
    std::string header;if(!(in>>header) || header!="P2_DWARF_ORANGE_BANK_1")return false;
    // Shared timing syntax only. Species registration never enters the Snow registry.
    std::ostringstream normalized;normalized<<"P2_SNOW_2 "<<in.rdbuf();
    std::istringstream parsed(normalized.str());
    return p2animation::parse(parsed,clips);
}
inline bool bindings(std::istream& in,std::set<std::uint32_t>& ids){
    ids.clear();std::string word;int count;
    if(!(in>>word>>count) || word!="P2_DWARF_ORANGE_ACTORS_1" || count<1 || count>100)return false;
    for(int i=0;i<count;++i){
        if(!(in>>word) || word.empty() || word.size()>10 || word.find_first_not_of("0123456789")!=std::string::npos)return false;
        unsigned long long id=std::stoull(word);if(id>0xffffffffULL || !ids.insert(static_cast<std::uint32_t>(id)).second)return false;
    }
    return !(in>>word);
}
}
