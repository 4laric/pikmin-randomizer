#pragma once
#include "Interactions.h"
// Receiver spy, not an implementation of the engine's damage state machine.
struct Navi {
    bool alive = true;
    bool accepts = true;
    float mHealth = 100.0f;
    int calls = 0;
    Creature* owner = nullptr;
    float damage = 0.0f;
    bool isAlive() const { return alive; }
    bool stimulate(const InteractAttack& hit) {
        ++calls; owner = hit.mOwner; damage = hit.mDamage;
        return accepts;
    }
};
