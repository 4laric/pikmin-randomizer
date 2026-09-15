#include "pc_p2_projectile_engine_receiver.h"

#include "Creature.h"
#include "Interactions.h"
#include "teki.h"

P2ProjectileEngineHit p2_projectile_apply_engine_strike(Creature* target, Creature* source,
                                                        bool attack, bool targetIsTeki,
                                                        float damage)
{
    P2ProjectileEngineHit hit;
    if (!target) {
        return hit;
    }
    hit.attempted = true;
    hit.healthBefore = target->mHealth;
    if (targetIsTeki) {
        hit.storedDamageBefore = static_cast<Teki*>(target)->mStoredDamage;
    }

    bool applied = false;
    if (attack) {
        // Source Rock.cpp:222 `InteractAttack attack(this, 250.0f, collObj)`.
        // The P1 Interaction signature is (owner, collPart, damage, p4); the host
        // has no collision part for the Stone, so collPart is nullptr and p4=false.
        InteractAttack interaction(source, nullptr, damage, false);
        applied = target->stimulate(interaction);
    } else {
        // Source Rock.cpp:218 `InteractPress press(source-or-self, attackDamage, nullptr)`.
        InteractPress interaction(source, damage);
        applied = target->stimulate(interaction);
    }

    hit.applied = applied;
    hit.healthAfter = target->mHealth;
    if (targetIsTeki) {
        hit.storedDamageAfter = static_cast<Teki*>(target)->mStoredDamage;
    }
    if (!applied && target->isAlive()) {
        hit.rejected = true;
    }
    return hit;
}
