#pragma once
// Interaction stand-ins for the Sarai capture bridge translation unit. Only the
// InteractFlick constructor and the backwards-angle sentinel are consumed by the
// bridge; the doubles record what was delivered so the test can assert the
// exactly-once release shape.
#include "types.h"
#include "Vector.h"

#define FLICK_BACKWARDS_ANGLE (-1000.0f)

class Creature;

class Interaction {
public:
    explicit Interaction(Creature* owner) : mOwner(owner) {}
    virtual ~Interaction() = default;
    Creature* mOwner = nullptr;
};

class InteractFlick : public Interaction {
public:
    inline InteractFlick(Creature* owner, f32 knockback, f32 damage, f32 angle)
        : Interaction(owner)
    {
        mIntensity = knockback;
        mDamage = damage;
        mAngle = angle;
    }
    f32 mIntensity = 0.0f;
    f32 mDamage = 0.0f;
    f32 mAngle = 0.0f;
};
