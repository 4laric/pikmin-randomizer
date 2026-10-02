#pragma once
#include "teki.h"

// Explicit stub: verifies whether the real receiver calls its legacy TAI edge.
struct TaiStrategy {
    int transitions = 0;
    bool allow = true;
    bool transit(Teki& actor, int state) {
        ++transitions;
        if (allow) actor.mStateID = state;
        return allow;
    }
};
