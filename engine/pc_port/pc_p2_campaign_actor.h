#pragma once
#include "pc_randomizer.h"
#include "teki.h"
#include "Generator.h"
#include <set>

// Retail generator _70 values can be zero or repeated. Seed slot UIDs are the
// stable identity for campaign actors; fixture-only actors retain their IDs.
inline unsigned pc_p2_campaign_source(const BTeki* actor) {
    if (!actor || !actor->mGenerator || !pc_randomizer_p2_bridge()) return 0;
    return pc_randomizer_p2_source_for_id(pc_randomizer_generator_id(actor->mGenerator));
}
inline unsigned pc_p2_campaign_token(const BTeki* actor) {
    if (!actor || !actor->mGenerator) return 0;
    if (pc_p2_campaign_source(actor)) return pc_randomizer_generator_id(actor->mGenerator);
    return actor->mGenerator->_70;
}
inline std::set<unsigned> pc_p2_campaign_ids(unsigned source) {
    std::set<unsigned> result;
    if (!tekiMgr || !pc_randomizer_p2_bridge()) return result;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        BTeki* actor = static_cast<BTeki*>(*it);
        if (pc_p2_campaign_source(actor) == source) result.insert(pc_p2_campaign_token(actor));
    }
    return result;
}
