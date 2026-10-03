#pragma once
#include "pc_p2_retail_cave_context.h"
#include "pc_p2_campaign_treasure_state.h"

// Read-only source/profile checks for the retail floor provider (#1232/#1274).
// These do not authenticate a scene, birth actors, grant receipts or implement
// a cave Pod. The caller must load_retail the exact catalogue and obtain
// expectedFloor, expectedBirth and selectedSource from its authenticated
// campaign/floor/SAVE owner, never reconstruct this evidence from input rows.
namespace p2retailtreasure {
// selectedFingerprint must come from pc_randomizer_session_fingerprint().
// Matching is necessary, but does not replace authenticated floor/card proof.
inline bool selectedScene(const p2retail::SceneIdentity& scene,
                          const std::string& selectedFingerprint) {
    return p2retail::hex64(selectedFingerprint)&&scene.seed==selectedFingerprint;
}
inline const p2treasure::Entry* looseSource(const p2treasure::Catalog& catalog,
    const p2retail::CaveDescriptor& supplied,unsigned floor,
    const p2retail::BirthIdentity& birth,const p2retail::SceneIdentity& scene,
    const p2retail::Snapshot& expectedFloor,const p2retail::BirthIdentity& expectedBirth) {
    if(!p2treasurestate::catalog_valid(catalog)||!(scene==expectedFloor.scene)
       ||scene.seed.empty()||scene.visit.empty()||!scene.serial
       ||!p2retail::hex64(scene.layoutSha256)||!birth.epoch||!birth.activation||!expectedFloor.inCave
       ||!(birth==expectedBirth))return nullptr;
    const auto* cave=p2retail::descriptor(supplied.cave);
    if(!cave||cave->source!=supplied.source||cave->sourceSha256!=supplied.sourceSha256
       ||cave->catalogSha256!=supplied.catalogSha256||cave->maxFloor!=supplied.maxFloor
       ||expectedFloor.cave!=cave->cave||expectedFloor.floor!=floor
       ||expectedFloor.source!=cave->source||expectedFloor.sourceSha256!=cave->sourceSha256
       ||expectedFloor.catalogSha256!=cave->catalogSha256||expectedFloor.maxFloor!=cave->maxFloor)return nullptr;
    // Resolve the immutable source definition, not supplied.rows/catalogId.
    const auto* definition=p2retail::definition(*cave,floor);
    if(!definition||birth.row>=definition->rows.size())return nullptr;
    const auto& row=definition->rows[birth.row];
    if(row.kind!="loose_treasure"||row.boss||!row.heldTreasure.empty()
       ||birth.ordinal>=row.minimum()
       ||birth.instance!=p2retail::instanceKey(*cave,floor,row,birth.ordinal))return nullptr;
    return catalog.find(row.catalogId); // Original strength/slots; no boss adjustment.
}

inline bool consumed(const p2treasure::Catalog& catalog,const p2treasurestate::State& state,
    const std::string& selectedSource,const p2retail::CaveDescriptor& cave,unsigned floor,
    const p2retail::BirthIdentity& birth,const p2retail::SceneIdentity& scene,
    const p2retail::Snapshot& expectedFloor,const p2retail::BirthIdentity& expectedBirth,
    const std::string& receipt) {
    const auto* entry=looseSource(catalog,cave,floor,birth,scene,expectedFloor,expectedBirth);
    return entry&&receipt==entry->id&&p2treasurestate::digest(selectedSource)
        &&state.active()&&state.source()==selectedSource&&state.seen(catalog,entry->id);
}
} // namespace p2retailtreasure
