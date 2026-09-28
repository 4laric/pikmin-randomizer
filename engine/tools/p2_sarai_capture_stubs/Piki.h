#pragma once
// Piki stand-in for the Sarai capture bridge translation unit. Implements the
// exact mouth-stick surface the shipped bridge relies on, so capture admission,
// exactly-once detach and the FallMeck/Flick release can be observed directly.
#include "Creature.h"
#include "Collision.h"
#include "Interactions.h"
#include "types.h"
#include "Vector.h"

class Piki : public Creature {
public:
    bool isAlive() const { return alive; }
    bool isStickTo() const { return stickTarget != nullptr; }
    bool isStickToMouth() const { return stickMouth; }
    Creature* getStickObject() const { return stickTarget; }
    CollPart* getStickPart() const { return stickPart; }

    void startStickMouth(Creature* owner, CollPart* part)
    {
        stickTarget = owner;
        stickPart = part;
        stickMouth = true;
        ++startStickCalls;
    }
    void endStickMouth()
    {
        stickTarget = nullptr;
        stickPart = nullptr;
        stickMouth = false;
        ++endStickCalls;
    }

    // The bridge delivers exactly one InteractFlick (drop or escape). In the
    // engine, Interaction::actCommon detaches the mouth link and actPiki applies
    // the flick receiver; mirror that so the released body is observably off the
    // mouth (matching the bridge's exactly-once erase that follows).
    bool stimulate(immut Interaction& interaction)
    {
        ++stimulateCalls;
        const InteractFlick* flick = dynamic_cast<const InteractFlick*>(&interaction);
        if (flick) {
            lastKnockback = flick->mIntensity;
            lastDamage = flick->mDamage;
            lastAngle = flick->mAngle;
            if (isStickToMouth()) endStickMouth();
        }
        return true;
    }

    bool alive = true;
    Vector3f mVelocity;

    // Observable stick/release bookkeeping (test-only).
    Creature* stickTarget = nullptr;
    CollPart* stickPart = nullptr;
    bool stickMouth = false;
    int startStickCalls = 0;
    int endStickCalls = 0;
    int stimulateCalls = 0;
    f32 lastKnockback = 0.0f;
    f32 lastDamage = 0.0f;
    f32 lastAngle = 0.0f;
};
