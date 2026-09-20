#pragma once
// Creature stand-in for the Sarai capture bridge translation unit. The bridge
// only uses the owner pointer for identity comparisons and passes it back into
// Piki stick calls; no Creature method is invoked here.
#include "types.h"
#include "Vector.h"

class CollPart;

class Creature {
public:
    Creature() = default;
    virtual ~Creature() = default;
};
