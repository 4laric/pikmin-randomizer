#pragma once
// Engine-free presentation helpers for the interpolated Antenna Beetle (41) and
// Careening Dirigibug (58) draws (#972). Presentation only: none of this feeds
// the source FSM or any gameplay clock.
#include <cmath>
#include <vector>

namespace p2fbsmooth {

// Span handed to the pose bank for a clip whose converter skipped its last
// source frames (Bank::validFrames wants 0 first and duration-1 last): a
// dropped tail shortens the span to the last kept pose instead of falling back
// to uniform frames, which would shift every pose.
inline int bankDuration(const std::vector<int>& frames, int duration) {
    if (!frames.empty() && frames.front() == 0 && frames.back() < duration - 1) return frames.back() + 1;
    return duration;
}

// startCarcassMotion plays a carried corpse's carry/type5 clip between its
// LOOP_START and LOOP_END markers. `seconds` is the corpse's own clock
// (30 source frames per second); the result stays in [start, end).
inline float carryLoopFrame(float seconds, int loopStart, int loopEnd) {
    const float span = float(loopEnd - loopStart);
    if (!(span > 0.0f) || !std::isfinite(seconds) || seconds < 0.0f) return float(loopStart);
    return float(loopStart) + std::fmod(seconds * 30.0f, span);
}

// Armed Dirigibug bomb hit_loop: one pose per 4 render frames as before, but a
// continuous source frame (so the private Shape lerps between poses).
inline float bombLoopFrame(int pulse, int frames) {
    if (frames < 1 || pulse < 0) return 0.0f;
    return std::fmod(float(pulse) / 4.0f, float(frames));
}

// Fade-clock step: only plausible frame times advance it.
inline float fadeStep(float dt) { return dt > 0.0f && dt < 0.5f && std::isfinite(dt) ? dt : 0.0f; }

}  // namespace p2fbsmooth
