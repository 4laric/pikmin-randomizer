#pragma once
// Engine-free double for the Sarai lifecycle test: creature skeleton. Only
// what the real pc_p2_sarai_host.h class declaration needs (base with the
// transform, complete collision-part and matrix types) is provided; all host
// behavior methods are defined in the test TU itself.
#include "Vector.h"

struct Matrix4f {
    float mMtx[4][4];
};

struct CollPart {
};

class Graphics;

struct SRT;


class Creature {
public:
    SRT mSRT;
    virtual ~Creature() = default;
    virtual void update() {}
    virtual void refresh(Graphics&) {}
    virtual void doKill() {}
};
