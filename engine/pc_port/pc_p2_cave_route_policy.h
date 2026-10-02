#pragma once
#include "pc_p2_cave_anchor.h"
#include "pc_p2_cave_transfer.h"
#include <iomanip>
#include <cstdio>
#include <fstream>
#include <map>
#include <set>
#include "pc_p2_white_policy.h"
#include "netplay/pc_netplay_sha256.h"

// Opt-in surface route presentation plus a live-party checkpoint. Distinct from
// cave floor entry: a surface does not instantiate a generated floor or receipts.
struct P2CaveSurfaceRoute {
    int wireVersion=1; // Custom surface1 stays base-only; surface2 adds real P/W.
    P2CaveAnchor entrance;
    P2CaveEntry party;
};

inline bool p2_cave_route_hex(const std::string& s,size_t length){
    return s.size()==length && s.find_first_not_of("0123456789abcdef")==std::string::npos;
}
inline std::string p2_cave_route_hash(const std::string& bytes){
    uint8_t digest[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),digest);
    return pc_netplay_sha::hex(digest,32);
}

// Derive the complete base pose bank before loading shapes or restoring actors.
// Auxiliary Purple impact/motion profiles are outside ordinary route activation.
inline bool p2_cave_route_bank_files(std::istream& in,int species,std::set<std::string>& result){
    if(species!=P2SpeciesPurple && species!=P2SpeciesWhite)return false;
    const std::string prefix=species==P2SpeciesPurple?"purple":"white";
    std::string word;float values[9];
    if(!(in>>word) || word!=(species==P2SpeciesPurple?"P2_PURPLE_1":"P2_WHITE_1")
        || !(in>>word) || word!="stats")return false;
    for(float& v:values)if(!(in>>v) || !std::isfinite(v) || v<0 || v>1000)return false;
    if(species==P2SpeciesWhite){
        P2WhiteStats s{values[0],values[1],values[2],values[3],values[4],values[5],values[6],values[7],values[8]};
        if(!p2_white_stats_valid(s))return false;
        int count;std::set<unsigned> ids;
        if(!(in>>word>>count) || word!="ivory_generators" || count<1 || count>32)return false;
        for(int i=0;i<count;++i){
            std::string text;if(!(in>>text) || text.empty() || text.find_first_not_of("0123456789")!=std::string::npos)return false;
            try{const auto id=std::stoull(text);if(id>0xffffffffULL || !ids.insert(static_cast<unsigned>(id)).second)return false;}
            catch(...){return false;}
        }
    }
    std::map<std::string,int> counts;std::set<std::pair<std::string,int>> attachments;
    std::set<std::string> files{"p2-"+prefix+".txt"};
    for(const char* name:{"wait","walk","attack1"}){
        int count;float seconds;
        if(!(in>>word>>count>>seconds) || word!=name || count<1 || count>32 || !std::isfinite(seconds) || seconds<=0)return false;
        counts[word]=count;
        for(int i=0;i<count;++i){
            const std::string suffix="_"+std::string(i<10?"0":"")+std::to_string(i);
            files.insert("assets/dataDir/courses/pikmin2room/"+prefix+"_"+word+suffix+".mod");}
    }
    while(in>>word){
        std::string clip;int index;
        if(word!="happa" || !(in>>clip>>index) || !counts.count(clip) || index<0 || index>=counts[clip]
            || !attachments.insert({clip,index}).second)return false;
        for(int i=0;i<12;++i){float value;if(!(in>>value) || !std::isfinite(value))return false;}
    }
    if(!in.eof())return false;
    for(const auto& count:counts)for(int i=0;i<count.second;++i)if(!attachments.count({count.first,i}))return false;
    for(int i=0;i<3;++i)files.insert("assets/dataDir/courses/pikmin2room/"+prefix+"_happa_"+std::to_string(i)+".mod");
    result=std::move(files);return true;
}

struct P2CaveRouteActivation {
    std::string token,routeHash,seed,slot,receipt;
    std::set<int> species;
    std::map<std::string,std::string> files;
};
inline bool p2_cave_route_asset_path(const std::string& name){
    if(name=="p2-white.txt" || name=="p2-purple.txt" || name=="p2-cave-route-identity.txt")return true;
    const std::string base="assets/dataDir/courses/pikmin2room/";
    if(name.compare(0,base.size(),base)!=0)return false;
    const std::string leaf=name.substr(base.size());
    return leaf.size()>4 && leaf.substr(leaf.size()-4)==".mod"
        && (leaf.compare(0,6,"white_")==0 || leaf.compare(0,7,"purple_")==0)
        && leaf.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_.")==std::string::npos
        && leaf.find("..") == std::string::npos;
}
inline bool p2_cave_route_activation_read(std::istream& in,P2CaveRouteActivation& out){
    P2CaveRouteActivation a;std::string word,surface,cave;int version,count;
    if(!(in>>word) || word!="P2_CAVE_ROUTE_SPECIES_1" || !(in>>word>>surface>>cave>>a.token>>version>>a.routeHash)
        || word!="route" || surface!="tutorial" || cave!="forest_1" || version!=2
        || !p2_cave_token_valid(a.token) || !p2_cave_route_hex(a.routeHash,64))return false;
    if(!(in>>word>>a.seed>>a.slot>>a.receipt) || word!="identity" || a.seed.empty()
        || a.seed.find_first_not_of("0123456789")!=std::string::npos || (a.seed.size()>1 && a.seed[0]=='0')
        || a.seed.size()>20 || !p2_cave_route_hex(a.slot,64) || !p2_cave_route_hex(a.receipt,64))return false;
    // Canonical uint64, including overflow rejection.
    try{size_t end=0;(void)std::stoull(a.seed,&end);if(end!=a.seed.size())return false;}catch(...){return false;}
    if(!(in>>word>>count) || word!="species" || count<1 || count>2)return false;
    int previous=0;
    for(int i=0;i<count;++i){
        int species;
        if(!(in>>species) || (species!=P2SpeciesPurple && species!=P2SpeciesWhite)
            || species<=previous || !a.species.insert(species).second)return false;
        previous=species;
    }
    if(!(in>>word>>count) || word!="files" || count<1 || count>203)return false;
    std::string previousName;
    for(int i=0;i<count;++i){
        std::string name,hash;
        if(!(in>>name>>hash) || !p2_cave_route_asset_path(name) || !p2_cave_route_hex(hash,64)
            || name<=previousName || !a.files.emplace(name,hash).second)return false;
        previousName=name;
    }
    if(in>>word || !in.eof())return false;
    out=std::move(a);return true;
}
inline bool p2_cave_route_activation_valid(const P2CaveRouteActivation& a,const P2CaveSurfaceRoute& route,
        const std::string& routeBytes,const std::map<std::string,std::string>& bytes){
    if(route.wireVersion!=2 || route.party.token!=a.token || p2_cave_route_hash(routeBytes)!=a.routeHash)return false;
    std::set<int> requested;
    for(const auto& p:route.party.squad)if(p.species==P2SpeciesPurple || p.species==P2SpeciesWhite)requested.insert(p.species);
    if(requested!=a.species || bytes.size()!=a.files.size())return false;
    for(const auto& file:a.files){auto value=bytes.find(file.first);
        if(value==bytes.end() || value->second.empty() || p2_cave_route_hash(value->second)!=file.second)return false;}
    auto identity=bytes.find("p2-cave-route-identity.txt");if(identity==bytes.end())return false;
    std::istringstream id(identity->second);std::string header,seed,slot,receipt,cave,surface,extra;
    if(!(id>>header>>seed>>slot>>receipt>>cave>>surface) || header!="P2_CAVE_ROUTE_IDENTITY_1"
        || seed!=a.seed || slot!=a.slot || receipt!=a.receipt || cave!="forest_1" || surface!="tutorial"
        || id>>extra || !id.eof())return false;
    std::set<std::string> expected{"p2-cave-route-identity.txt"};
    for(int species:a.species){
        const std::string config=species==P2SpeciesPurple?"p2-purple.txt":"p2-white.txt";
        auto content=bytes.find(config);if(content==bytes.end())return false;
        std::istringstream input(content->second);std::set<std::string> files;
        if(!p2_cave_route_bank_files(input,species,files))return false;
        expected.insert(files.begin(),files.end());
    }
    std::set<std::string> actual;for(const auto& file:a.files)actual.insert(file.first);
    return actual==expected;
}

inline bool p2_cave_surface_route_read(std::istream& in, P2CaveSurfaceRoute& out) {
    std::string header, extra;
    P2CaveSurfaceRoute value;
    int count=0;
    if (!(in>>header>>value.party.token>>value.entrance.x>>value.entrance.y
          >>value.entrance.z>>value.entrance.radius>>value.party.health>>count)
        || (header!="P2_CAVE_ROUTE_SURFACE_1" && header!="P2_CAVE_ROUTE_SURFACE_2") || !p2_cave_token_valid(value.party.token)
        || !std::isfinite(value.party.health) || value.party.health<=0 || value.party.health>1
        || count<1 || count>P2CaveMaxSurvivors) return false;
    const auto& a=value.entrance;
    if (!std::isfinite(a.x) || !std::isfinite(a.y) || !std::isfinite(a.z)
        || !std::isfinite(a.radius) || a.radius<20 || a.radius>150
        || std::fabs(a.x)>100000 || std::fabs(a.y)>100000 || std::fabs(a.z)>100000) return false;
    value.wireVersion=header=="P2_CAVE_ROUTE_SURFACE_2"?2:1;
    const int maxSpecies=value.wireVersion==2?P2SpeciesWhite:P2SpeciesYellow;
    for(int i=0;i<count;++i) {
        P2CaveSurvivor p;
        if (!(in>>p.species>>p.maturity) || p.species<0 || p.species>maxSpecies
            || p.maturity<0 || p.maturity>2) return false;
        value.party.squad.push_back(p);
    }
    if ((in>>extra) || !in.eof()) return false;
    value.entrance.enabled=true;value.entrance.kind="hole";
    value.party.schema=2;value.party.floor=1;
    out=value;return true;
}

inline bool p2_cave_surface_route_eligible(const P2CaveAnchor& entrance,
        float x,float y,float z,bool walking,bool paused,bool ui,bool movie,
        bool dayEnd,bool online,float health) {
    return entrance.contains(x,y,z) && walking && !paused && !ui && !movie
        && !dayEnd && !online && std::isfinite(health) && health>1;
}

// Ordinary White acquisition can upgrade a bounded forest entry from wire1.
// Incoming wire1 still rejects White; the existing live writer promotes to2.
// Other profiles and Bulbmin retain their prior admission behavior.
inline bool p2_cave_bounded_live_species_supported(int entrySchema,int species,
        bool boundedForest,bool whiteAssets) {
    return p2_schema_supports(entrySchema,species)
        || (boundedForest && whiteAssets && entrySchema==P2SpeciesSchemaPurple
            && species==P2SpeciesWhite);
}

inline std::string p2_cave_surface_route_transfer(const P2CaveEntry& party,
        float x,float y,float z,int wireVersion=1) {
    if(!p2_cave_token_valid(party.token) || party.squad.empty()
        || party.squad.size()>P2CaveMaxSurvivors || !std::isfinite(party.health)
        || party.health<=0 || party.health>1 || !std::isfinite(x)
        || !std::isfinite(y) || !std::isfinite(z) || (wireVersion!=1 && wireVersion!=2)) return {};
    std::ostringstream out;
    out<<std::setprecision(9)<<"P2_CAVE_ROUTE_TRANSFER_"<<wireVersion<<'\n'<<party.token<<'\n'
       <<x<<' '<<y<<' '<<z<<' '<<party.health<<' '<<party.squad.size()<<'\n';
    for(const auto& p:party.squad) {
        if(p.species<0 || p.species>(wireVersion==2?P2SpeciesWhite:P2SpeciesYellow) || p.maturity<0 || p.maturity>2)return {};
        out<<p.species<<' '<<p.maturity<<'\n';
    }
    return out.str();
}
