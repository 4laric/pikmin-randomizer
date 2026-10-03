#pragma once
#include "pc_p2_retail_treasure_profile.h"
#include "pc_p2_campaign_treasure_held_config.h"
#include "pc_p2_original_pod_sources.h"
#include <functional>

namespace p2retailtreasure {
struct AssetRow {
    std::string id,modelHash,archiveHash,originalModelHash;
    OriginalProfile profile;
};
struct AssetBank {
    std::string identity,campaign;
    p2treasureheld::Config held;
    std::vector<AssetRow> rows;
};
// The enclosing owner supplies authenticated selected-input buffers. This
// verifier does not select a session, bind treasury State or authorize births.
using ReadInput=std::function<bool(const std::string&,std::string&,std::string&)>;
inline bool verifyAssetBank(const std::string& master,const std::string& expectedCampaign,
                           ReadInput read,p2treasure::Catalog& catalog,AssetBank& out,std::string& error) {
    auto fail=[&](const char* message){error=message;return false;};
    if(!read||master.empty()||master.size()>65536||!p2treasurestate::digest(expectedCampaign))
        return fail("invalid aggregate source input");
    std::istringstream in(master);AssetBank next;std::string magic,retail,leafHash,extra;unsigned count=0;
    if(!(in>>magic>>retail>>next.campaign>>leafHash>>count)||magic!="P2_TREASURE_RETAIL_1"
       ||retail!=p2treasure::RetailDigest||next.campaign!=expectedCampaign
       ||!p2treasurestate::digest(leafHash)||!count||count>201)return fail("invalid aggregate source envelope");
    auto input=[&](const std::string& role,std::size_t bound,std::string& bytes){
        std::string nextBytes;
        if(!read(role,nextBytes,error)||nextBytes.empty()||nextBytes.size()>bound)return false;
        bytes=std::move(nextBytes);return true;
    };
    std::string bytes;
    if(!input("p2-treasure-catalog.txt",32768,bytes)||p2treasureplacements::hash(bytes)!=p2treasure::RetailDigest)
        return fail("aggregate retail catalog hash mismatch");
    p2treasure::Catalog nextCatalog;std::istringstream catalogText(bytes);
    if(!nextCatalog.read(catalogText)||!p2treasurestate::catalog_valid(nextCatalog))return fail("aggregate catalog invalid");
    const std::string base="p2-original/retail-cargo/";
    if(!input(base+"held.txt",65536,bytes)||p2treasureplacements::hash(bytes)!=leafHash
       ||!p2treasureheld::parse(bytes,nextCatalog,next.held)||next.held.campaign!=expectedCampaign)
        return fail("aggregate held source mismatch");
    if(!input("p2-original/"+next.held.course+".p2c",4u*1024u*1024u,bytes)
       ||p2treasureplacements::hash(bytes)!=next.held.manifestHash)return fail("aggregate original source hash mismatch");
    p2original::SourceManifest original;
    if(!p2original::readSourceManifest(bytes,next.held.course,original,error)||original.fingerprint!=expectedCampaign)
        return fail("aggregate original source campaign mismatch");
    for(const auto& held:next.held.rows) {
        bool matched=false;
        for(const auto& row:original.rows)if(row.enemy.uid==held.uid){matched=p2treasureheld::find(next.held,row)==&held;break;}
        if(!matched)return fail("aggregate literal held source row mismatch");
    }
    if(!input("p2-original/"+next.held.course+".p2on",4u*1024u*1024u,bytes)
       ||p2treasureplacements::hash(bytes)!=next.held.receiverManifestHash)return fail("aggregate receiver source hash mismatch");
    std::vector<p2original::OnyonRecord> receivers;
    if(!p2original::readOnyonsFromBytes(bytes,receivers,error))return false;
    bool receiver=false;
    for(const auto& row:receivers)if(row.uid==next.held.receiver){
        if(row.index!=4||row.sourceSha+":"+row.sourceKey!=next.held.receiverIdentity)return fail("aggregate receiver identity mismatch");
        receiver=true;
    }
    if(!receiver)return fail("aggregate literal ship missing");
    if(!input("assets/dataDir/courses/pikmin2treasures/pod.mod",32u*1024u*1024u,bytes)
       ||p2treasureplacements::hash(bytes)!=next.held.podHash)return fail("aggregate historical held dependency mismatch");
    if(!input("assets/dataDir/courses/pikmin2retailpod/pod.mod",32u*1024u*1024u,bytes)
       ||p2treasureplacements::hash(bytes)!=p2originalpod::convertedModelSha256)return fail("aggregate original Pod model mismatch");
    for(const auto& role:std::vector<std::pair<std::string,std::string>>{
        {base+"pod/arc.szs",p2originalpod::archiveSha256},
        {base+"pod/pot.bmd",p2originalpod::originalModelSha256},
        {base+"pod/coll.txt",p2originalpod::originalCollisionSha256},
        {base+"pod/texts.szs",p2originalpod::originalTextsSha256}}) {
        if(!input(role.first,32u*1024u*1024u,bytes)||p2treasureplacements::hash(bytes)!=role.second)
            return fail("aggregate original Pod source bytes changed");
    }
    std::map<std::string,std::string> configs;
    for(const char* kind:{"otakara","item"}) {
        if(!input(base+"source/user/Abe/Pellet/us/"+kind+"_config.txt",128u*1024u,bytes))return fail("aggregate original profile missing");
        const char* pin=std::string(kind)=="item"?itemProfileSha:otakaraProfileSha;
        if(p2treasureplacements::hash(bytes)!=pin)return fail("aggregate original profile hash mismatch");
        configs.emplace(kind,std::move(bytes));
    }
    std::set<std::string> ids;
    for(unsigned i=0;i<count;++i) {
        AssetRow row;std::string kind;int index=-1;
        if(!(in>>row.id>>kind>>index>>row.modelHash>>row.archiveHash>>row.originalModelHash)
           ||!p2treasure::safe_id(row.id)||!ids.insert(row.id).second
           ||!p2treasurestate::digest(row.modelHash)||!p2treasurestate::digest(row.archiveHash)
           ||!p2treasurestate::digest(row.originalModelHash))return fail("invalid aggregate asset row");
        const auto* entry=nextCatalog.find(row.id);
        if(!entry||entry->kind!=kind||entry->index!=index
           ||!originalProfile(configs[kind],*entry,row.profile,error))return fail("aggregate source profile/catalog mismatch");
        for(const auto& role:std::vector<std::pair<std::string,std::string>>{
            {"assets/dataDir/courses/pikmin2treasures/"+row.id+".mod",row.modelHash},
            {base+row.id+"/arc.szs",row.archiveHash},{base+row.id+"/original.bmd",row.originalModelHash}}) {
            if(!input(role.first,32u*1024u*1024u,bytes)||p2treasureplacements::hash(bytes)!=role.second)
                return fail("aggregate asset bytes changed");
        }
        next.rows.push_back(std::move(row));
    }
    if(in>>extra)return fail("trailing aggregate source data");
    for(const auto& held:next.held.rows) {
        bool found=false;
        for(const auto& row:next.rows)if(row.id==held.id){found=row.modelHash==held.modelHash;break;}
        if(!found)return fail("aggregate missing or differing held model");
    }
    next.identity=p2treasureplacements::hash(master);
    next.held.identity=next.identity; // One selected treasury SOURCE for both providers.
    catalog=std::move(nextCatalog);out=std::move(next);error.clear();return true;
}
}
