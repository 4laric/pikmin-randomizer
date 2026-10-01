#pragma once
// #972 presentation policy for the Breadbug family (engine-free).
// The carried carcass holds the type5 loop-start pose in the nearest-pose draw
// (startCarcassMotion); the smoothed draw instead plays the type5 loop so the
// body is not frozen. Only the drawn source frame changes; gameplay never
// reads it.
namespace p2breadbugcorpse {
constexpr float kHoldFrame = 10.0f;  // type5 key 0 (loop start)
// A source frame usable by the pose bank: finite and inside [0, duration-1].
inline float clampFrame(float frame, int duration) {
    const float last = duration > 1 ? float(duration - 1) : 0.0f;
    if (!(frame > 0.0f)) return 0.0f;  // also NaN
    return frame < last ? frame : last;
}
}
