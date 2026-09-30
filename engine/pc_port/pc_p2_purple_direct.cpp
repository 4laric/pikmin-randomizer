#include "pc_p2_purple_direct.h"
#include "pc_p2_purple_direct_policy.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_chappy.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_purple_impact.h"
#include "Generator.h"
#include "Interactions.h"
#include "Piki.h"
#include "TAI/Chappy.h"
#include "teki.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <string>
namespace {
std::set<BTeki*> adults;
bool enabled = false;
p2purpledirect::Config campaign;
unsigned campaignSource(const BTeki* actor) {
    if (!enabled || !campaign.campaign || !pc_randomizer_purple_campaign()) return 0;
    return campaign.source(pc_p2_campaign_token(actor), pc_p2_campaign_source(actor));
}
}

void pc_p2_purple_direct_reset()
{
    adults.clear();
    enabled = false;
    campaign = {};
}

void pc_p2_purple_direct_setup()
{
    pc_p2_purple_direct_reset();
    std::ifstream in("p2-purple-direct.txt");
    if (!in) return;
    p2purpledirect::Config config;
    if (!p2purpledirect::parse(in, config) || !tekiMgr) std::abort();
    if (config.campaign) {
        if (!pc_randomizer_purple_campaign() || !pc_randomizer_p2_bridge()) std::abort();
        for (const auto& binding : config.bindings)
            if (pc_randomizer_p2_source_for_id(binding.first) != binding.second) std::abort();
        campaign = config;
        enabled = true;
        std::printf("P2_PURPLE_DIRECT_SETUP mode=campaign bindings=%zu live_identity_validation=1\n", campaign.bindings.size());
        return;
    }
    std::set<std::uint32_t> wanted = config.adultGenerators;
    Iterator iterator(tekiMgr);
    CI_LOOP(iterator) {
        BTeki* actor = static_cast<BTeki*>(*iterator);
        if (!actor || !actor->mGenerator || !wanted.erase(actor->mGenerator->_70)) continue;
        if (actor->mTekiType != TEKI_Swallow || !adults.insert(actor).second) std::abort();
        std::printf("P2_PURPLE_DIRECT_BIND family=adult_bulborb generator=%u native_family=Swallow fp36=50 source=Chappy\n",
            actor->mGenerator->_70);
    }
    if (!wanted.empty()) std::abort();
    enabled = true;
}

void pc_p2_purple_direct_forget(BTeki* actor)
{
    adults.erase(actor);
}

bool pc_p2_purple_direct_enabled() { return enabled; }
bool pc_p2_purple_direct_adult_registered(const BTeki* actor)
{
    return campaign.campaign ? campaignSource(actor) == 2 && pc_p2_chappy_registered(actor)
                             : adults.count(const_cast<BTeki*>(actor)) != 0;
}

PcP2PurpleDirectHit pc_p2_purple_direct_begin(Piki* source, Creature* target, CollPart* part)
{
    PcP2PurpleDirectHit result;
    if (!enabled || !source || !target || source->mVelocity.y >= 0.0f || target->mObjType != OBJTYPE_Teki) return result;
    BTeki* teki = static_cast<BTeki*>(target);
    const bool dwarf = pc_p2_kochappy_registered(teki)
        && (!campaign.campaign || campaignSource(teki) == 1);
    const bool adult = pc_p2_purple_direct_adult_registered(teki);
    if ((!dwarf && !adult) || teki->mDeadState || !teki->isAlive()
        || teki->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)
        || (dwarf && (teki->mStateID < 4 || teki->mStateID == 13 || teki->mStateID == 14
            || teki->mStateID > CHAPPYSTATE_P2PurpleImpact))
        || !pc_p2_purple_impact_claim_direct(source)) return result;
    result.handled = true;
    result.family = dwarf ? PcP2PurpleDirectHit::RedDwarf : PcP2PurpleDirectHit::AdultBulborb;
    const float health = teki->mHealth;
    const float queued = teki->mStoredDamage;
    const int state = teki->mStateID;
    if (dwarf) {
        InteractPress press(source, 20.0f);
        target->stimulate(press);
        result.accepted = teki->mStateID == CHAPPYSTATE_Unk2;
    } else {
        InteractAttack damage(source, part, p2purpledirect::AdultHipdropDamage, false);
        result.damageApplied = target->stimulate(damage);
    }
    std::printf("P2_PURPLE_DIRECT stage=hipdrop family=%s source=%p target=%p accepted=%d damage_applied=%d pre_health=%.1f post_health=%.1f pre_state=%d post_state=%d part=%p seed_uid=%u source_id=%u queued_before=%.3f queued_after=%.3f hipdrop_payload=%.1f\n",
        dwarf ? "red_dwarf" : "adult_bulborb", static_cast<void*>(source), static_cast<void*>(target),
        result.accepted ? 1 : 0, result.damageApplied ? 1 : 0, health, teki->mHealth,
        state, teki->mStateID, static_cast<void*>(part), pc_p2_campaign_token(teki), pc_p2_campaign_source(teki),
        queued, teki->mStoredDamage, dwarf ? 20.0f : p2purpledirect::AdultHipdropDamage);
    return result;
}

void pc_p2_purple_direct_finish(Piki* source, Creature* target, CollPart* part, PcP2PurpleDirectHit& result)
{
    if (!result.handled || !source || !target || source->mVelocity.y >= 0.0f) return;
    BTeki* teki = static_cast<BTeki*>(target);
    const float health = teki->mHealth;
    const int state = teki->mStateID;
    bool accepted = false;
    if (result.family == PcP2PurpleDirectHit::RedDwarf) {
        InteractPress press(source, 10.0f);
        target->stimulate(press);
        accepted = teki->mStateID == CHAPPYSTATE_Unk2;
        // P2 assigns the second callback result over the first when this
        // descending stage runs; attachment follows the final interaction.
        result.accepted = accepted;
    }
    std::printf("P2_PURPLE_DIRECT stage=press family=%s source=%p target=%p accepted=%d aggregate=%d pre_health=%.1f post_health=%.1f pre_state=%d post_state=%d part=%p\n",
        result.family == PcP2PurpleDirectHit::RedDwarf ? "red_dwarf" : "adult_bulborb",
        static_cast<void*>(source), static_cast<void*>(target), accepted ? 1 : 0, result.accepted ? 1 : 0,
        health, teki->mHealth, state, teki->mStateID, static_cast<void*>(part));
}
