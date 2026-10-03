#pragma once
#include "pc_p2_cave_campaign_party.h"
// Capture actual bodies/captains/stable planted heads. Refuse active work,
// transient head animations, captives or invalid flags; no actor is mutated.
bool pc_p2_cave_campaign_party_capture(P2CaveCampaignParty& party,bool inside);
// Cold-scene restoration of authenticated captured state, not fixture setup.
// Existing cache-created actors must match position/UID before being rebound.
void pc_p2_cave_campaign_party_restore(const P2CaveCampaignParty& party);
class Piki;
void pc_p2_cave_campaign_party_forget(Piki* body);
void pc_p2_cave_campaign_party_scene_exit();
// Original source owner supplies actual source record/attempt/activation only
// after a successful native birth. No pointer/position identity inference.
bool pc_p2_cave_campaign_party_associate_birth(Piki* body,const char* sourceKey,
    std::uint32_t recordUid,std::uint32_t attempt,std::uint64_t activation,
    const char* catalogFingerprint=nullptr);
