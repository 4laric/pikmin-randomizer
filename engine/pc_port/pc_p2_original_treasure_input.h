#pragma once
#include "pc_p2_original_session.h"
#include "pc_p2_retail_treasure_bank.h"

namespace p2originalsession {
// Input validation only. Physical actors and floor births retain their own
// admission rules; no card or treasury State is changed by this function.
inline bool treasureInput(const Bundle& bundle, const std::string& expectedSource,
                          p2treasure::Catalog& catalog, std::string& error) {
    auto fail=[&](const char* message){error=message;return false;};
    if(!p2treasurestate::digest(expectedSource))return fail("invalid selected treasure source");
    auto read=[&](const std::string& role,std::string& bytes,std::string& e){return input(bundle,role,bytes,e);};
    auto asset=[&](const std::string& role,std::size_t bound,const std::string& sha){
        std::string bytes;
        return read(role,bytes,error)&&bytes.size()<=bound&&p2treasureplacements::hash(bytes)==sha;
    };
    std::string source;
    if(!read("p2-treasure-placements.txt",source,error)||source.size()>65536
       ||p2treasureplacements::hash(source)!=expectedSource)return fail("selected treasure source differs");
    std::istringstream envelope(source);std::string magic;envelope>>magic;
    if(magic=="P2_TREASURE_RETAIL_1") {
        p2treasure::Catalog next;p2retailtreasure::AssetBank bank;
        if(!p2retailtreasure::verifyAssetBank(source,bundle.campaign,read,next,bank,error)
           ||bank.identity!=expectedSource)return false;
        catalog=std::move(next);return true;
    }
    std::string bytes;
    if(!read("p2-treasure-catalog.txt",bytes,error)||bytes.size()>32768
       ||p2treasureplacements::hash(bytes)!=p2treasure::RetailDigest)return fail("selected treasure catalog differs");
    p2treasure::Catalog next;std::istringstream text(bytes);
    if(!next.read(text)||!p2treasurestate::catalog_valid(next))return fail("selected treasure catalog invalid");
    if(magic=="P2_TREASURE_PLACEMENTS_1") {
        p2treasureplacements::Config config;
        if(!p2treasureplacements::parse(source,next,config)
           ||!asset("assets/dataDir/courses/pikmin2treasures/pod.mod",32u*1024u*1024u,config.podHash))
            return fail("selected loose treasure source invalid");
        const char* folders[]={"practice","stage1","stage2","stage3","last"};
        std::set<int> stages;
        for(const auto& row:config.rows) {
            if(!asset("assets/dataDir/courses/pikmin2treasures/"+row.id+".mod",32u*1024u*1024u,row.modelHash))
                return fail("selected loose treasure model differs");
            if(stages.insert(row.stage).second
               &&!asset(std::string("assets/dataDir/stages/")+folders[row.stage]+"/default.gen",4u*1024u*1024u,row.generatorHash))
                return fail("selected loose treasure generator differs");
        }
    } else if(magic=="P2_TREASURE_HELD_1") {
        p2treasureheld::Config config;
        if(!p2treasureheld::parse(source,next,config)||config.campaign!=bundle.campaign)
            return fail("selected held treasure campaign invalid");
        const auto manifest="p2-original/"+config.course+".p2c";
        if(!read(manifest,bytes,error)||bytes.size()>4u*1024u*1024u
           ||p2treasureplacements::hash(bytes)!=config.manifestHash)return fail("selected held source manifest differs");
        p2original::SourceManifest original;
        if(!p2original::readSourceManifest(bytes,config.course,original,error)
           ||original.fingerprint!=bundle.campaign)return fail("selected held source campaign differs");
        for(const auto& row:config.rows) {
            bool matched=false;
            for(const auto& actor:original.rows)if(actor.enemy.uid==row.uid){matched=p2treasureheld::find(config,actor)==&row;break;}
            if(!matched||!asset("assets/dataDir/courses/pikmin2treasures/"+row.id+".mod",32u*1024u*1024u,row.modelHash))
                return fail("selected held source row/model differs");
        }
        if(!read("p2-original/"+config.course+".p2on",bytes,error)||bytes.size()>4u*1024u*1024u
           ||p2treasureplacements::hash(bytes)!=config.receiverManifestHash)return fail("selected held receiver manifest differs");
        std::vector<p2original::OnyonRecord> receivers;
        if(!p2original::readOnyonsFromBytes(bytes,receivers,error))return false;
        bool matched=false;
        for(const auto& receiver:receivers)if(receiver.uid==config.receiver){
            if(receiver.index!=4||receiver.sourceSha+":"+receiver.sourceKey!=config.receiverIdentity)
                return fail("selected held receiver identity differs");
            matched=true;
        }
        if(!matched||!asset("assets/dataDir/courses/pikmin2treasures/pod.mod",32u*1024u*1024u,config.podHash))
            return fail("selected held receiver/asset missing");
    } else return fail("unsupported selected treasure source format");
    catalog=std::move(next);error.clear();return true;
}
}
