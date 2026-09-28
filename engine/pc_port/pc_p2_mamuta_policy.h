#pragma once
// Mamuta source pose-bank policy, engine-free (#221).
//
// Values checked against PaniAnimator.h TekiMotion (Dead 0 .. Type5 14) and the
// installed P2 Miulin clip bank. pc_p2_mamuta.cpp owns the .mod loading and the
// live draw; this header owns the decisions a standalone test can exercise:
//
//   * anchor() maps the exact P1 Miurin motion to its Miulin clip.
//   * kMaxPoses is the raised bank cap (dense import samples 8-10 poses per
//     clip: even frames plus every event frame), asserted here so the loader,
//     the manifest validator and the test share one number.
//   * selectSample() places the sampled pose on the source animation frame
//     timeline, so a strike lands on its true event frame instead of a uniform
//     pose index. Time comes from the animator's source frames, never a
//     wall-clock counter.
namespace p2mamuta {

// Dense time-sampled import banks (even source frames + every event frame).
constexpr int kMaxPoses = 16;
static_assert(kMaxPoses >= 8, "dense sampled Mamuta banks need at least 8 poses");
static_assert(kMaxPoses <= 64, "Mamuta bank cap must stay bounded");

// Clip indices match the installed bank order.
enum Clip {
    Wait = 0,
    WaitAct = 1,
    Move = 2,
    Attack0 = 3,
    Attack1 = 4,
    Attack4 = 5,
    Flick = 6,
    Dead = 7,
    Type5 = 8,
};
constexpr int kClips = 9;

inline int anchor(int type, int motion, bool corpse) {
    if (type != 24) return -1;
    if (corpse || motion == 0) return Dead;          // Dead
    switch (motion) {
    case 2: case 3: return Wait;                     // Wait1/Wait2
    case 4: case 5: return WaitAct;                  // WaitAct1/WaitAct2
    case 6: case 7: return Move;                     // Move1/Move2
    case 8: return Attack1;                          // Attack posture/attack
    case 9: return Flick;                            // Flick (ground shake)
    case 10: case 11: case 12: return Attack1;       // Type1/Type2/Type3 bury strike
    case 13: return Attack4;                         // Type4 recovery
    case 14: return Type5;                           // Type5 pellet tremble
    default: return -1;
    }
}

// Nearest sampled pose to `srcFrame` on the clip's source-frame timeline.
// `sampleFrames` holds `poseCount` strictly ascending source frames. Returns -1
// for an unusable bank so the caller can refuse the draw. Ties keep the earlier
// (lower) sample.
inline int selectSample(float srcFrame, const int* sampleFrames, int poseCount) {
    if (!sampleFrames || poseCount < 1 || poseCount > kMaxPoses) return -1;
    if (!(srcFrame >= 0.0f)) srcFrame = 0.0f;
    int best = 0;
    float bestDistance = float(sampleFrames[0]) - srcFrame;
    if (bestDistance < 0.0f) bestDistance = -bestDistance;
    for (int i = 1; i < poseCount; ++i) {
        float distance = float(sampleFrames[i]) - srcFrame;
        if (distance < 0.0f) distance = -distance;
        if (distance < bestDistance) { bestDistance = distance; best = i; }
    }
    return best;
}

} // namespace p2mamuta
