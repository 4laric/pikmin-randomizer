#pragma once
#include "pc_randomizer.h"
#include "pc_p2_original_actor.h"
#include "teki.h"
#include "Generator.h"
#include <set>

// Retail generator _70 values can be zero or repeated. Seed slot UIDs are the
// stable identity for campaign actors; fixture-only actors retain their IDs.
inline unsigned pc_p2_campaign_source(const BTeki* actor) {
    unsigned original = 0;
    if (actor && pc_p2_original_actor_source(static_cast<const Creature*>(actor), original)) return original;
    if (!actor || !actor->mGenerator || !pc_randomizer_p2_bridge()) return 0;
    return pc_randomizer_p2_source_for_id(pc_randomizer_generator_id(actor->mGenerator));
}
inline unsigned pc_p2_campaign_token(const BTeki* actor) {
    if (!actor) return 0;
    const unsigned original = pc_p2_original_actor_token(static_cast<const Creature*>(actor));
    if (original) return original;
    if (!actor->mGenerator) return 0;
    if (pc_p2_campaign_source(actor)) return pc_randomizer_generator_id(actor->mGenerator);
    return actor->mGenerator->_70;
}
inline std::set<unsigned> pc_p2_campaign_ids(unsigned source) {
    std::set<unsigned> result;
    if (!tekiMgr) return result;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        BTeki* actor = static_cast<BTeki*>(*it);
        unsigned original = 0;
        if (actor && pc_p2_original_actor_source(static_cast<const Creature*>(actor), original)) {
            if (original == source) result.insert(pc_p2_campaign_token(actor));
        } else if (source && pc_randomizer_p2_bridge() && pc_p2_campaign_source(actor) == source) {
            result.insert(pc_p2_campaign_token(actor));
        }
    }
    return result;
}
