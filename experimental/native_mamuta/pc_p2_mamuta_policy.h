#pragma once
// Static source anchors, not time-sampled animation. Values checked against PaniAnimator.h.
namespace p2mamuta {
inline int anchor(int type, int motion, bool corpse) {
    if (type != 24) return -1;
    if (corpse || motion == 0) return 1;
    if (motion == 2) return 0;
    if (motion == 10 || motion == 11 || motion == 12) return 2;
    return -1;
}
}
