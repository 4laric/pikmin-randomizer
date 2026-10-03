#pragma once
#include "pc_p2_campaign_treasure_config.h"
#include "pc_p2_original_manifest.h"
#include "pc_p2_original_onyon.h"
namespace p2treasureheld {
struct Row { unsigned uid=0,source=0;int code=0;std::string id,modelHash; };
struct Config {
    std::string identity,podHash,campaign,manifestHash,receiverManifestHash,receiverIdentity,course;
    unsigned receiver=0;std::vector<Row> rows;
};
inline const p2treasure::Entry* decode(const p2treasure::Catalog& catalog,int code) {
    if(code<=0||code>32767)return nullptr;
    const int kind=code>>8,index=code&255;
    if(kind!=3&&kind!=4)return nullptr;
    for(const auto& entry:catalog.entries)
        if(entry.kind==(kind==3?"otakara":"item")&&entry.index==index)return &entry;
    return nullptr;
}
inline bool parse(const std::string& bytes,const p2treasure::Catalog& catalog,Config& out) {
    if(bytes.empty()||bytes.size()>p2treasureplacements::MaxBytes||!p2treasurestate::catalog_valid(catalog))return false;
    std::istringstream in(bytes);Config next;std::string magic,retail,extra;unsigned long long receiver;int count;
    if(!(in>>magic>>retail>>next.podHash>>next.campaign>>next.manifestHash>>next.receiverManifestHash>>next.receiverIdentity>>receiver>>next.course>>count)
       ||magic!="P2_TREASURE_HELD_1"||retail!=p2treasure::RetailDigest||!p2treasurestate::digest(next.podHash)
       ||!p2treasurestate::digest(next.campaign)||!p2treasurestate::digest(next.manifestHash)
       ||!p2treasurestate::digest(next.receiverManifestHash)
       ||!receiver||receiver>UINT32_MAX||next.course!="tutorial"||count<1||count>201)return false;
    // Source receiver identity is exactly the typed Onyon adapter's SHA:key.
    const auto colon=next.receiverIdentity.find(':');
    if(colon!=64||!p2treasurestate::digest(next.receiverIdentity.substr(0,colon))
       ||next.receiverIdentity.substr(colon+1)!="tutorial/defaultgen.txt#0")return false;
    next.receiver=unsigned(receiver);std::set<unsigned> uids;std::set<std::string> ids;
    for(int i=0;i<count;++i) {
        Row row;unsigned long long uid,source;
        if(!(in>>uid>>source>>row.code>>row.id>>row.modelHash)||!uid||uid>UINT32_MAX
           ||source>255||uid==receiver||!uids.insert(unsigned(uid)).second||!ids.insert(row.id).second
           ||!p2treasurestate::digest(row.modelHash))return false;
        const auto* entry=decode(catalog,row.code);if(!entry||entry->id!=row.id)return false;
        row.uid=unsigned(uid);row.source=unsigned(source);next.rows.push_back(row);
    }
    if(in>>extra)return false;
    next.identity=p2treasureplacements::hash(bytes);out=std::move(next);return true;
}
inline const Row* find(const Config& config,const p2original::CatalogRow& original) {
    for(const auto& row:config.rows)if(row.uid==original.enemy.uid)
        return original.course==config.course&&original.enemy.source==row.source&&original.enemy.treasureCode==row.code?&row:nullptr;
    return nullptr;
}
// Literal source manifest parsing is independent of the mutable actor registry.
// The enclosing campaign owner still authenticates activation/card selection.
inline bool load_verified(p2treasure::Catalog& catalog,Config& config) {
    using namespace p2treasureplacements;
    p2treasure::Catalog nextCatalog;Config next;std::string bytes;
    const char* path=std::getenv("PIKMIN_P2_TREASURE_CATALOG");
    if(!nextCatalog.load_retail(path&&path[0]?path:"p2-treasure-catalog.txt")
       ||!bounded("p2-treasure-placements.txt",MaxBytes,bytes)||!parse(bytes,nextCatalog,next))return false;
    const char* directory=std::getenv("PIKMIN_P2_ORIGINAL_CATALOG");
    if(!directory||!*directory||!bounded(std::string(directory)+"/"+next.course+".p2c",4u*1024u*1024u,bytes)
       ||hash(bytes)!=next.manifestHash)return false;
    p2original::SourceManifest original;std::string error;
    if(!p2original::readSourceManifest(bytes,next.course,original,error)||original.fingerprint!=next.campaign)return false;
    if(!bounded(std::string(directory)+"/"+next.course+".p2on",4u*1024u*1024u,bytes)||hash(bytes)!=next.receiverManifestHash)return false;
    std::vector<p2original::OnyonRecord> receivers;
    if(!p2original::readOnyonsFromBytes(bytes,receivers,error))return false;
    bool receiver=false;
    for(const auto& source:receivers)if(source.uid==next.receiver) {
        if(source.index!=4||source.sourceSha+":"+source.sourceKey!=next.receiverIdentity)return false;
        receiver=true;
    }
    if(!receiver)return false;
    for(const auto& row:next.rows) {
        bool matched=false;
        for(const auto& source:original.rows)if(source.enemy.uid==row.uid){matched=find(next,source)==&row;break;}
        if(!matched||!bounded("assets/dataDir/courses/pikmin2treasures/"+row.id+".mod",32u*1024u*1024u,bytes)
           ||hash(bytes)!=row.modelHash)return false;
    }
    if(!bounded("assets/dataDir/courses/pikmin2treasures/pod.mod",32u*1024u*1024u,bytes)||hash(bytes)!=next.podHash)return false;
    catalog=std::move(nextCatalog);config=std::move(next);return true;
}
}
