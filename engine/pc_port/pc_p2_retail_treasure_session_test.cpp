#include "pc_p2_retail_treasure_engine.h"
#include "pc_p2_campaign_treasure_state.h"
#include "pc_p2_original_progress.h"
#include <cassert>
#include <iostream>
// Getter doubles exist only in this control target. Never link this file into
// pikmin_pc or use it to claim foundation/production/gameplay qualification.
namespace {bool original=false;std::string campaign,source,fingerprint;}
std::string pc_randomizer_original_campaign(){return campaign;}
bool pc_randomizer_original_session(){return original;}
std::string pc_randomizer_campaign_treasure_source(){return source;}
std::string pc_randomizer_session_fingerprint(){return fingerprint;}
int main() {
    p2retail::SceneIdentity scene{std::string(64,'a'),"synthetic-visit",std::string(64,'b'),9};
    campaign=std::string(64,'c');source=std::string(64,'d');fingerprint=scene.seed;
    assert(!pc_p2_retail_treasure_session_matches(scene));
    original=true;assert(!pc_p2_retail_treasure_session_matches(scene));
    std::string error;assert(p2original::originalProgress().initialize(campaign,error));
    assert(!pc_p2_retail_treasure_session_matches(scene));
    assert(p2treasurestate::state.bind(source));
    assert(pc_p2_retail_treasure_session_matches(scene));
    fingerprint.clear();assert(!pc_p2_retail_treasure_session_matches(scene));
    fingerprint=std::string(64,'e');assert(!pc_p2_retail_treasure_session_matches(scene));
    fingerprint=scene.seed;
    auto process=scene;process.seed="process-token";fingerprint=process.seed;
    assert(!pc_p2_retail_treasure_session_matches(process));
    fingerprint=scene.seed;
    const auto actualCampaign=campaign;campaign=std::string(64,'f');
    assert(!pc_p2_retail_treasure_session_matches(scene));campaign=actualCampaign;
    source=std::string(64,'e');assert(!pc_p2_retail_treasure_session_matches(scene));
    source=std::string(64,'d');assert(pc_p2_retail_treasure_session_matches(scene));
    original=false;assert(!pc_p2_retail_treasure_session_matches(scene));
    std::cout<<"PASS selected session/original context/source guard controls (getter doubles only)\n";
}
