#include "pc_p2_bigtreasure_receiver.h"

#include <cmath>

const char* p2_bigtreasure_receiver_stimulus_name(P2BigTreasureReceiverStimulus stimulus)
{
    switch (stimulus) {
    case P2BigTreasureReceiverStimulus::Fire: return "fire";
    case P2BigTreasureReceiverStimulus::Gas: return "gas";
    case P2BigTreasureReceiverStimulus::Water: return "water";
    case P2BigTreasureReceiverStimulus::Elec: return "elec";
    case P2BigTreasureReceiverStimulus::None: return "none";
    }
    return "?";
}

P2BigTreasureReceiverHit p2_bigtreasure_receiver_resolve(int weapon,
                                                         const P2BigTreasureVec3& origin,
                                                         float attackDamage,
                                                         const P2BigTreasureVec3& target)
{
    P2BigTreasureReceiverHit hit;
    switch (weapon) {
    case P2BTWEAPON_Fire:
        hit.stimulus = P2BigTreasureReceiverStimulus::Fire;
        hit.damage = attackDamage;
        break;
    case P2BTWEAPON_Gas:
        hit.stimulus = P2BigTreasureReceiverStimulus::Gas;
        hit.damage = attackDamage;
        break;
    case P2BTWEAPON_Water:
        // Source InteractBubble(mOwner, 0.0f): the bubble state replaces damage.
        hit.stimulus = P2BigTreasureReceiverStimulus::Water;
        hit.damage = 0.0f;
        break;
    case P2BTWEAPON_Elec: {
        // Source zapDir (BigTreasureAttack.cpp:466-471): horizontal-to-target,
        // normalised, scaled to 150, raised to y = 150.
        hit.stimulus = P2BigTreasureReceiverStimulus::Elec;
        hit.damage = attackDamage;
        const float dx = target.x - origin.x;
        const float dz = target.z - origin.z;
        const float len = std::sqrt(dx * dx + dz * dz);
        const float kZap = 150.0f;
        if (len > 1e-6f) {
            hit.direction.x = dx / len * kZap;
            hit.direction.z = dz / len * kZap;
        } else {
            hit.direction.z = kZap;
        }
        hit.direction.y = kZap;
        break;
    }
    default:
        break;
    }
    return hit;
}
