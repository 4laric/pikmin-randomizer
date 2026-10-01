#include "pc_p2_sarai_capture_bridge.h"
#include "pc_p2_sarai_capture.h"
#include "Piki.h"
#include "Creature.h"
#include "Collision.h"
#include "Interactions.h"
#include <map>
#include <vector>

namespace {
struct Binding {
    Piki* piki = nullptr;
    std::uint64_t ownerToken = 0;
    Creature* owner = nullptr;
    CollPart* mouth = nullptr;
    unsigned slot = 0;
};
std::map<Piki*, Binding> bindings;

bool current(const Piki* piki) { return piki && bindings.count(const_cast<Piki*>(piki)) != 0; }

// Detach one bound Pikmin and revoke its bridge authority before any native
// creature-list mutation that a later release could re-observe. Grounded path
// (no damage/knockback): used by teardown, owner_lost and scene_exit.
void detach(Piki* piki)
{
    if (!current(piki)) return;
    auto it = bindings.find(piki);
    Binding b = it->second;
    bindings.erase(it);
    // Only remove the exact mouth link we authored; a replacement mouth selected
    // by another owner/callback stays untouched.
    if (piki->isStickToMouth() && piki->getStickObject() == b.owner && piki->getStickPart() == b.mouth)
        piki->endStickMouth();
}

void collectOwned(Creature* owner, std::vector<Piki*>& out)
{
    for (const auto& entry : bindings)
        if (entry.second.owner == owner) out.push_back(entry.first);
}
} // namespace

bool pc_p2_sarai_piki_capture(Piki* piki, Creature* owner, CollPart* mouth,
                              std::uint64_t ownerToken, unsigned slot)
{
    if (!piki || !owner || !mouth || !ownerToken || slot >= p2sarai::kMouthSlots
        || current(piki)
        || !mouth->isBouncySphereType()
        || !piki->isAlive() || piki->isStickTo() || piki->isStickToMouth()) {
        return false;
    }
    piki->startStickMouth(owner, mouth);
    if (!piki->isStickToMouth() || piki->getStickObject() != owner || piki->getStickPart() != mouth) {
        if (piki->isStickToMouth() && piki->getStickObject() == owner && piki->getStickPart() == mouth)
            piki->endStickMouth();
        return false;
    }
    bindings[piki] = {piki, ownerToken, owner, mouth, slot};
    return true;
}

bool pc_p2_sarai_piki_bound(const Piki* piki) { return current(piki); }
bool pc_p2_sarai_piki_owned_by(const Piki* piki, Creature* owner)
{
    return current(piki) && bindings[const_cast<Piki*>(piki)].owner == owner;
}
int pc_p2_sarai_piki_slot(const Piki* piki)
{
    if (!current(piki)) return p2sarai::kNoSlot;
    return int(bindings[const_cast<Piki*>(piki)].slot);
}
bool pc_p2_sarai_piki_release(Piki* piki)
{
    if (!current(piki)) return false;
    detach(piki);
    return true;
}
unsigned pc_p2_sarai_carried_count(Creature* owner)
{
    unsigned count = 0;
    for (const auto& entry : bindings)
        if (entry.second.owner == owner) ++count;
    return count;
}

// Source fallMeckGround(): InteractFallMeck(damage) then a downward
// setVelocity(-fallMeckSpeed) for every mouth-stuck creature. The P1 engine has
// no InteractFallMeck; InteractFlick detaches the mouth link (actCommon) and
// applies the flick/damage receiver (actPiki), then the source downward
// velocity is applied.
unsigned pc_p2_sarai_drop_owned(Creature* owner, float damage, float downSpeed)
{
    if (!owner) return 0;
    const float dmg = p2sarai::fallMeckDamage(damage);
    const float down = p2sarai::fallMeckReleaseVelocity(downSpeed);
    std::vector<Piki*> owned;
    collectOwned(owner, owned);
    unsigned released = 0;
    for (Piki* piki : owned) {
        if (!current(piki) || bindings[piki].owner != owner) continue;
        if (!piki->isAlive()) { detach(piki); continue; }
        piki->stimulate(InteractFlick(owner, p2sarai::kFlickKnockback, dmg, FLICK_BACKWARDS_ANGLE));
        bindings.erase(piki); // exactly-once, revoked before any re-entry
        piki->mVelocity.set(0.0f, 0.0f, 0.0f);
        piki->mVelocity.y = down;
        ++released;
    }
    return released;
}

// Source flickStickTarget(): InteractFlick(knockback 10, damage 0) for every
// mouth-stuck creature; harmless detach + knockback (escape receiver).
unsigned pc_p2_sarai_flick_owned(Creature* owner)
{
    if (!owner) return 0;
    std::vector<Piki*> owned;
    collectOwned(owner, owned);
    unsigned detached = 0;
    for (Piki* piki : owned) {
        if (!current(piki) || bindings[piki].owner != owner) continue;
        if (!piki->isAlive()) { detach(piki); continue; }
        piki->stimulate(InteractFlick(owner, p2sarai::kFlickKnockback, p2sarai::kFlickDamage, FLICK_BACKWARDS_ANGLE));
        bindings.erase(piki);
        ++detached;
    }
    return detached;
}

void pc_p2_sarai_owner_lost(std::uint64_t ownerToken)
{
    if (!ownerToken) return;
    std::vector<Piki*> affected;
    for (const auto& entry : bindings)
        if (entry.second.ownerToken == ownerToken) affected.push_back(entry.first);
    for (Piki* piki : affected) detach(piki);
}
void pc_p2_sarai_scene_exit()
{
    std::vector<Piki*> all;
    for (const auto& entry : bindings) all.push_back(entry.first);
    for (Piki* piki : all) detach(piki);
}
void pc_p2_sarai_forget() { bindings.clear(); }
