#pragma once
#include "pc_p2_campaign_treasure_config.h"
#include <cmath>
#include <map>

namespace p2retailtreasure {
// Literal GPVE01 raw configuration, supplied as bytes by the authenticated
// selected-input owner. This parser does not open paths or activate resources.
constexpr const char* otakaraProfileSha="36de6f3b05065913464d256bd2745a2ef3a6948f96f0729c6b0ee51771b7f24a";
constexpr const char* itemProfileSha="fb69ac3f3736d83a7f62154c7592bc7fcd1eef456336320ba6b3ca80941c6b85";
struct OriginalProfile {
    float radius=0,carryRadius=0,height=0,inertiaScaling=0,friction=0;
    std::string dynamics,archive,model;
};
inline bool originalProfile(const std::string& bytes,const p2treasure::Entry& entry,
                            OriginalProfile& out,std::string& error) {
    const char* pin=entry.kind=="otakara"?otakaraProfileSha:entry.kind=="item"?itemProfileSha:nullptr;
    auto fail=[&](const char* message){error=message;return false;};
    if(!pin||bytes.empty()||bytes.size()>128u*1024u||p2treasureplacements::hash(bytes)!=pin)
        return fail("original treasure profile source hash mismatch");
    // Comments can contain CP932 text; parameter tokens remain ASCII.
    std::istringstream lines(bytes);std::string line,tokens;
    while(std::getline(lines,line)) {
        line=line.substr(0,line.find('#'));
        for(char c:line){if(c=='{'||c=='}')tokens+=' ';tokens+=c;if(c=='{'||c=='}')tokens+=' ';}
        tokens+='\n';
    }
    std::istringstream in(tokens);unsigned count=0;std::string token;
    if(!(in>>count)||!count||count>201||entry.index<0||unsigned(entry.index)>=count)
        return fail("invalid original treasure profile count/index");
    std::map<std::string,std::string> selected;
    for(unsigned index=0;index<count;++index) {
        if(!(in>>token)||token!="{")return fail("invalid original profile block");
        std::map<std::string,std::string> fields;
        while(in>>token) {
            if(token=="end")break;
            std::string value;
            if(token=="{"||token=="}"||!(in>>value)||!fields.emplace(token,value).second)
                return fail("invalid original profile field");
            if(token=="offset") { // Three components, retained in the source bytes.
                if(!(in>>value>>value))return fail("invalid original profile offset");
            }
        }
        if(token!="end"||!(in>>token)||token!="}")return fail("invalid original profile terminator");
        if(index==unsigned(entry.index))selected=std::move(fields);
    }
    if(in>>token)return fail("trailing original profile data");
    auto integer=[&](const char* key,int expected){
        const auto found=selected.find(key);if(found==selected.end())return false;
        std::istringstream value(found->second);int number=0;std::string extra;
        return bool(value>>number)&&!(value>>extra)&&number==expected;
    };
    if(selected["name"]!=entry.id||!integer("dictionary",entry.dictionary)
       ||!integer("money",entry.value)||!integer("min",entry.strength)||!integer("max",entry.slots))
        return fail("original treasure profile/catalog identity mismatch");
    OriginalProfile next;
    auto number=[&](const char* key,float& destination,bool zeroAllowed=false){
        const auto found=selected.find(key);if(found==selected.end())return false;
        std::istringstream value(found->second);std::string extra;
        return bool(value>>destination)&&!(value>>extra)&&std::isfinite(destination)
            &&(zeroAllowed?destination>=0:destination>0);
    };
    if(!number("radius",next.radius)||!number("p_radius",next.carryRadius)||!number("height",next.height)
       ||!number("inertiascaling",next.inertiaScaling)||!number("friction",next.friction,true))
        return fail("invalid original treasure physics");
    next.dynamics=selected["dynamics"];next.archive=selected["archive"];next.model=selected["bmd"];
    if(next.dynamics.empty()||next.archive.empty()||next.model.empty())return fail("missing original treasure resource identity");
    out=std::move(next);error.clear();return true;
}
} // namespace p2retailtreasure
