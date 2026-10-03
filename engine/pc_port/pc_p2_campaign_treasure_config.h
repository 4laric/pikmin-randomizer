#pragma once
#include "pc_p2_campaign_treasure_state.h"
#include "netplay/pc_netplay_sha256.h"
#include <fstream>
#include <map>
#include <cstdlib>
namespace p2treasureplacements {
constexpr std::size_t MaxBytes = 65536;
struct Row { int stage=-1; std::uint32_t cargo=0, receiver=0; std::string id, modelHash, generatorHash; };
struct Config { std::string source, podHash; std::vector<Row> rows; };
inline std::string hash(const std::string& bytes) {
    std::uint8_t value[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),value);
    return pc_netplay_sha::hex(value,32);
}
inline bool bounded(const std::string& path,std::size_t maximum,std::string& out) {
    std::ifstream in(path,std::ios::binary);if(!in)return false;
    std::string next;char buffer[4096];
    while(in.read(buffer,sizeof(buffer))||in.gcount()) {
        const auto count=static_cast<std::size_t>(in.gcount());
        if(count>maximum-next.size())return false;
        next.append(buffer,count);
    }
    if(!in.eof()||next.empty())return false;
    out=std::move(next);return true;
}
// Exact input bytes are the placement identity authenticated by the card owner.
// This parser does not activate the feature or authenticate an enclosing card.
inline bool parse(const std::string& bytes,const p2treasure::Catalog& catalog,Config& out) {
    if(bytes.empty()||bytes.size()>MaxBytes||!p2treasurestate::catalog_valid(catalog))return false;
    std::istringstream in(bytes);std::string magic,catalogHash,extra;int count=0;Config next;
    if(!(in>>magic>>catalogHash>>next.podHash>>count)||magic!="P2_TREASURE_PLACEMENTS_1"
       ||catalogHash!=p2treasure::RetailDigest||!p2treasurestate::digest(next.podHash)||count<1||count>201)return false;
    std::set<std::pair<int,std::uint32_t>> actors;std::set<std::string> ids;
    std::set<std::pair<int,std::uint32_t>> receivers;
    std::map<int,std::string> stageHashes;
    for(int i=0;i<count;++i) {
        Row row;unsigned long long cargo=0,receiver=0;
        if(!(in>>row.stage>>cargo>>receiver>>row.id>>row.modelHash>>row.generatorHash)||row.stage<0||row.stage>4
           ||!cargo||cargo>UINT32_MAX||!receiver||receiver>UINT32_MAX||cargo==receiver
           ||!p2treasurestate::digest(row.modelHash)||!p2treasurestate::digest(row.generatorHash)
           ||!catalog.find(row.id)||!ids.insert(row.id).second)return false;
        const auto previous=stageHashes.find(row.stage);
        if(previous!=stageHashes.end()&&previous->second!=row.generatorHash)return false;
        stageHashes[row.stage]=row.generatorHash;
        row.cargo=static_cast<std::uint32_t>(cargo);row.receiver=static_cast<std::uint32_t>(receiver);
        if(!actors.insert({row.stage,row.cargo}).second)return false;
        receivers.insert({row.stage,row.receiver});next.rows.push_back(row);
    }
    if(in>>extra)return false;
    for(const auto& actor:actors)if(receivers.count(actor))return false;
    next.source=hash(bytes);out=std::move(next);return true;
}
inline bool read(const p2treasure::Catalog& catalog,Config& out) {
    std::string bytes;return bounded("p2-treasure-placements.txt",MaxBytes,bytes)&&parse(bytes,catalog,out);
}
// Bootstrap/card selection calls this before binding state. All staged physical
// inputs are verified, not just the mutable descriptor. Publication is atomic.
inline bool load_verified(p2treasure::Catalog& catalog,Config& config) {
    p2treasure::Catalog nextCatalog;Config next;
    const char* path=std::getenv("PIKMIN_P2_TREASURE_CATALOG");
    if(!nextCatalog.load_retail(path&&path[0]?path:"p2-treasure-catalog.txt")||!read(nextCatalog,next))return false;
    std::string bytes;
    if(!bounded("assets/dataDir/courses/pikmin2treasures/pod.mod",32u*1024u*1024u,bytes)||hash(bytes)!=next.podHash)return false;
    const char* folders[]={"practice","stage1","stage2","stage3","last"};
    std::set<int> verifiedStages;
    for(const auto& row:next.rows) {
        if(!bounded("assets/dataDir/courses/pikmin2treasures/"+row.id+".mod",32u*1024u*1024u,bytes)||hash(bytes)!=row.modelHash)return false;
        if(verifiedStages.insert(row.stage).second) {
            if(!bounded(std::string("assets/dataDir/stages/")+folders[row.stage]+"/default.gen",4u*1024u*1024u,bytes)||hash(bytes)!=row.generatorHash)return false;
        }
    }
    catalog=std::move(nextCatalog);config=std::move(next);return true;
}
}
