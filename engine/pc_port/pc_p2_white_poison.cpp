#include "pc_p2_white_poison.h"
#include "pc_p2_white_poison_policy.h"
#include "pc_p2_white.h"
#include "Piki.h"
#include "Generator.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <string>
#include <limits>

namespace {
bool enabled = false;
float poisonDamage = 0.0f;
std::set<unsigned> predatorGenerators;
std::set<const BTeki*> predators;
P2WhitePoisonEvents events;
}

void pc_p2_white_poison_setup() {
    enabled = false;
    poisonDamage = 0.0f;
    predatorGenerators.clear();
    predators.clear();
    events.reset();
    if (!pc_p2_whites_enabled()) return;
    std::ifstream in("p2-white-poison.txt");
    if (!in) return;
    std::string word;
    int count = 0;
    if (!(in >> word) || word != "P2_WHITE_POISON_1"
        || !(in >> word >> poisonDamage) || word != "damage"
        || !std::isfinite(poisonDamage) || poisonDamage != 750.0f
        || !(in >> word >> count) || word != "predator_generators" || count < 1 || count > 32) std::abort();
    for (int i = 0; i < count; ++i) {
        std::string token;
        if (!(in >> token) || token.empty() || token.find_first_not_of("0123456789") != std::string::npos) std::abort();
        unsigned long long wide;
        try { wide = std::stoull(token); } catch (...) { std::abort(); }
        if (wide > std::numeric_limits<unsigned>::max() || !predatorGenerators.insert(static_cast<unsigned>(wide)).second) std::abort();
    }
    if (in >> word) std::abort();
    std::set<unsigned> unmatched = predatorGenerators;
    Iterator actors(tekiMgr);
    CI_LOOP(actors) {
        Teki* actor = static_cast<Teki*>(*actors);
        if (!actor || !actor->mGenerator || !unmatched.erase(actor->mGenerator->_70)) continue;
        if (actor->mTekiType != TEKI_Swallow || !predators.insert(actor).second) std::abort();
    }
    if (!unmatched.empty()) std::abort();
    enabled = true;
    std::printf("P2_WHITE_POISON_READY damage=%.3f predators=%d source=ChappyBase_fp02 boundary=mouth_consumption\n",
                poisonDamage, count);
}

void pc_p2_white_poison_forget(BTeki* predator) {
    predators.erase(predator);
    events.forgetPredator(predator);
}

bool pc_p2_white_poison_predator(BTeki* predator) {
    return enabled && predator && predator->isAlive() && predators.count(predator);
}

bool pc_p2_white_poison_prepare(BTeki* predator, Creature* victim) {
    if (!pc_p2_white_poison_predator(predator) || !victim || !victim->isAlive()
        || !victim->isPiki() || !victim->isStickToMouth() || victim->getStickObject() != predator) return false;
    Piki* piki = static_cast<Piki*>(victim);
    return pc_p2_is_white(piki) && events.prepare(predator, victim);
}

bool pc_p2_white_poison_finish(BTeki* predator, const Creature* victim, bool consumed) {
    // The victim has already passed through kill(false); do not dereference it.
    if (!events.commit(predator, victim) || !consumed || !pc_p2_white_poison_predator(predator)) return false;
    // P2 EnemyBase::addDamage queues HP loss without counting a melee hit or
    // retaining the consumed Piki as an attack owner. Match that narrow part
    // of the source callback; the native damage state applies it next tick.
    if (predator->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)) return false;
    predator->mStoredDamage += poisonDamage;
    std::printf("P2_WHITE_POISON_CONSUMED predator=%p victim=%p damage=%.3f queued_health=%.3f\n",
                static_cast<void*>(predator), static_cast<const void*>(victim), poisonDamage, predator->mHealth);
    return true;
}
