#include "pc_p2_retail_treasure_engine.h"
#include "pc_p2_retail_treasure_policy.h"
#include "pc_p2_original_progress.h"

// Exact strong foundation ABI, published #1229 at 1cb934c6e5e7e191f47d28cbd781274c0ea394e6.
// Composition must provide the real owner implementation; no weak fallback.
std::string pc_randomizer_original_campaign();
bool pc_randomizer_original_session();
std::string pc_randomizer_campaign_treasure_source();
std::string pc_randomizer_session_fingerprint();

bool pc_p2_retail_treasure_session_matches(const p2retail::SceneIdentity& scene) {
    if(!pc_randomizer_original_session()
       ||!p2retailtreasure::selectedScene(scene,pc_randomizer_session_fingerprint()))return false;
    const auto campaign=pc_randomizer_original_campaign();
    const auto source=pc_randomizer_campaign_treasure_source();
    const auto& progress=p2original::originalProgress();
    return p2retail::hex64(campaign)&&progress.ready()&&progress.context().campaign==campaign
        &&p2treasurestate::digest(source)&&p2treasurestate::state.active()
        &&p2treasurestate::state.source()==source;
}
