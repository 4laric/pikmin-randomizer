#include "pc_blue_rescue.h"
#include "pc_p2_species.h"
#include "PikiAI.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include <map>

namespace {
std::map<const Piki*, Piki*> owners;
// Compare addresses against the current roster before dereferencing retained
// pointers. A removed rescuer cannot keep a victim held.
Piki* live(const Piki* address) {
    if (!address || !pikiMgr) return nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p == address) return p->isAlive() ? p : nullptr;
    }
    return nullptr;
}
bool valid(Piki* victim, const Piki* address) {
    Piki* rescuer = live(address);
    if (!rescuer || rescuer == victim || pc_p2_species(rescuer) != P2SpeciesBlue
        || rescuer->getState() != PIKISTATE_Normal || !rescuer->mActiveAction
        || rescuer->mActiveAction->mCurrActionIdx != PikiAction::Rescue) return false;
    auto* action = static_cast<ActRescue*>(rescuer->mActiveAction->getCurrAction());
    return action && action->holdsVictim(victim);
}
}

bool pc_blue_rescue_begin(Piki* victim, Piki* rescuer) {
    if (!live(victim) || victim->getState() != PIKISTATE_WaterHanged
        || !valid(victim, rescuer) || owners.count(victim)) return false;
    owners.emplace(victim, rescuer);
    return true;
}
bool pc_blue_rescue_tick(Piki* victim) {
    auto it = owners.find(victim);
    if (it == owners.end()) return false; // ordinary captain-held entry
    if (!valid(victim, it->second)) {
        owners.erase(it);
        victim->mFSM->transit(victim, PIKISTATE_Normal);
    }
    return true; // rescue-owned entry must never consult captain ThrowWait
}
void pc_blue_rescue_clear(Piki* victim) { owners.erase(victim); }
void pc_blue_rescue_release(Piki* victim, Piki* rescuer) {
    auto it = owners.find(victim);
    if (it == owners.end() || it->second != rescuer) return;
    owners.erase(it);
    if (Piki* body = live(victim)) {
        if (body->getState() == PIKISTATE_WaterHanged)
            body->mFSM->transit(body, PIKISTATE_Normal);
    }
}
bool pc_blue_rescue_owned(const Piki* victim, const Piki* rescuer) {
    auto it = owners.find(victim);
    return it != owners.end() && it->second == rescuer;
}
