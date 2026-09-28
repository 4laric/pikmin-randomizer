#include "pc_p2_bluechappy.h"
#include "pc_p2_bluechappy_policy.h"
#include "pc_p2_enemy.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_sheargrub.h"
#include "teki.h"
#include "Generator.h"
#include <fstream>
#include <set>
#include <cstdio>
#include <cstdlib>

namespace {
std::set<PelletView*> actors;
p2bluechappy::Health health;
p2bluechappy::Params policy; // defaults are the audited retail BlueChappy block
bool policyLoaded = false;

bool claimedElsewhere(BTeki* actor)
{
    return pc_p2_enemy_name(actor) || pc_p2_kochappy_name(actor) || pc_p2_dwarf_orange_name(actor)
           || pc_p2_sheargrub_name(actor);
}

bool bindActor(BTeki* actor, unsigned generator)
{
    if (!actor || actor->mTekiType != TEKI_Chappy || actors.count(static_cast<PelletView*>(actor))) return false;
    if (claimedElsewhere(actor)) return false;
    health.configure(policy.health);
    health.activate();
    if (!health.bind(actor)) return false;
    actors.insert(static_cast<PelletView*>(actor));
    actor->mHealth = policy.health;
    const auto& pos = actor->getPosition();
    std::printf("P2_ENEMY_READY species=BlueChappy source_id=42 native_family=Chappy adult=1 generator=%u "
                "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=P1 host=TEKI_Chappy "
                "mouth_slots=5 attack_event_frames=%d/%d/%d source_bank=Chappy\n",
                generator, pos.x, pos.y, pos.z, actor->mHealth, actor->getParameterF(TPF_Life),
                p2bluechappy::AttackBiteFrame, p2bluechappy::AttackSwallowFrame, p2bluechappy::AttackEndFrame);
    std::printf("P2_BLUECHAPPY_BIND generator=%u source_id=42 policy_source=%s\n", generator,
                policyLoaded ? "p2-bluechappy-policy.txt" : "retail_defaults");
    std::fflush(stdout);
    return true;
}
}

void pc_p2_bluechappy_reset()
{
    actors.clear();
    health.reset();
    policy = p2bluechappy::Params{};
    policyLoaded = false;
}

void pc_p2_bluechappy_forget(BTeki* actor)
{
    const bool wasRegistered = actors.erase(static_cast<PelletView*>(actor)) != 0;
    if (wasRegistered) {
        std::printf("P2_BLUECHAPPY_FORGET registered=1\n");
        std::fflush(stdout);
    }
    health.forget(actor);
}

float pc_p2_bluechappy_max_health(const BTeki* actor, float fallback)
{
    return health.life(actor, fallback);
}

const char* pc_p2_bluechappy_name(PelletView* actor)
{
    return actors.count(actor) ? "Orange Bulborb" : nullptr;
}

bool pc_p2_bluechappy_registered(const BTeki* actor)
{
    return actors.count(const_cast<BTeki*>(actor)) != 0;
}

unsigned long pc_p2_bluechappy_count()
{
    return (unsigned long)actors.size();
}

void pc_p2_bluechappy_setup()
{
    pc_p2_bluechappy_reset();
    std::ifstream profile("p2-bluechappy-policy.txt"), bindings("p2-bluechappy-actors.txt");
    if (!profile && !bindings) return;
    if (!profile || !bindings || !tekiMgr) std::abort();
    if (!p2bluechappy::parseConfig(profile, policy)) std::abort();
    policyLoaded = true;
    std::string word;
    int count;
    if (!(bindings >> word >> count) || word != "P2_BLUECHAPPY_ACTORS_1" || count < 1 || count > 100) std::abort();
    std::set<std::uint32_t> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long id;
        if (!(bindings >> id) || id > 0xffffffffUL || !wanted.insert((std::uint32_t)id).second) std::abort();
    }
    if (bindings >> word) std::abort();
    std::set<std::uint32_t> seen;
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70)) continue;
        if (!seen.insert(actor->mGenerator->_70).second) std::abort();
        if (!bindActor(actor, actor->mGenerator->_70)) std::abort();
    }
    if (seen != wanted) std::abort();
}

bool pc_p2_bluechappy_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned sourceId)
{
    if (sourceId != 42) return false;
    if (!actor) return false;
    return bindActor(actor, generatorId);
}
