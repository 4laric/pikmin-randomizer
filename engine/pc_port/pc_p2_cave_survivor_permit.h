#pragma once
#include "pc_p2_cave_campaign_party.h"
#include "pc_p2_original_piki_origin.h"
#include <array>
#include <cstring>

// Read-only admission against a completed, authenticated selected checkpoint.
// Source authority stays with OriginalPikiOrigin; origins alone are tombstones.
inline bool p2CaveSurvivorPermit(const P2CaveCampaignParty& party,bool scoped,
    std::uint64_t proofGeneration,std::uint64_t activeGeneration,
    const std::array<std::uint8_t,32>& digest,const std::string& sourceKey,
    std::uint32_t recordUid,std::uint32_t attempt,std::uint64_t activation,
    const std::string& catalogFingerprint,std::uint64_t* generation,std::uint8_t sha[32]){
    if(!scoped||!proofGeneration||proofGeneration!=activeGeneration
        ||!party.present||!party.resumeLiving||!party.valid()||sourceKey.empty())return false;
    bool nonzero=false;for(auto byte:digest)nonzero|=byte!=0;if(!nonzero)return false;
    const P2CavePartyBody* survivor=nullptr;
    for(const auto& body:party.bodies)if(body.sourceKey==sourceKey&&body.sourceRecord==recordUid
        &&body.sourceAttempt==attempt&&body.sourceActivation==activation&&body.catalogFingerprint==catalogFingerprint){
        if(survivor)return false;
        survivor=&body;
    }
    if(!survivor)return false;
    if(generation)*generation=proofGeneration;
    if(sha)std::memcpy(sha,digest.data(),digest.size());
    return true;
}

// Exact selected living body state. Tuple authority alone never grants flags.
inline bool p2CaveSurvivorBody(const P2CaveCampaignParty& party,bool scoped,
    std::uint64_t proofGeneration,std::uint64_t activeGeneration,
    const std::array<std::uint8_t,32>& digest,const std::string& sourceKey,
    std::uint32_t recordUid,std::uint32_t attempt,std::uint64_t activation,
    const std::string& catalogFingerprint,OriginalPikiBodyState& state,
    std::uint64_t* generation,std::uint8_t sha[32]){
    if(!p2CaveSurvivorPermit(party,scoped,proofGeneration,activeGeneration,digest,
        sourceKey,recordUid,attempt,activation,catalogFingerprint,nullptr,nullptr))return false;
    const P2CavePartyBody* selected=nullptr;
    for(const auto& body:party.bodies)if(body.sourceKey==sourceKey&&body.sourceRecord==recordUid
        &&body.sourceAttempt==attempt&&body.sourceActivation==activation&&body.catalogFingerprint==catalogFingerprint)selected=&body;
    if(!selected)return false;
    const OriginalPikiBodyState authenticated{std::uint8_t(selected->species),selected->wild,selected->wasWild};
    state=authenticated;
    if(generation)*generation=proofGeneration;
    if(sha)std::memcpy(sha,digest.data(),digest.size());
    return true;
}
