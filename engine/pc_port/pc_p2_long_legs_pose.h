#pragma once
// Engine-free presentation policy for the Raging Long Legs (BigFoot, 69)
// sampled pose bank (animation smoothing pass, #972).
//
// BigFoot ships four real J3D clips on the disc (wait, landing, flick, dead).
// The extractor bakes 24 single-joint poses per clip; p2posefamily lerps and
// crossfades between them. This header holds only the parts that need no
// engine: the P2_LONG_LEGS_ANIMATION_1 config parser and the choice of clip
// and source frame from the (unchanged) source FSM state. It never feeds back
// into behaviour: the FSM, timings, collision and feet are untouched.
#include "pc_p2_long_legs_fsm.h"

#include <algorithm>
#include <cmath>
#include <istream>
#include <string>
#include <vector>

namespace p2longlegspose {

constexpr float kSourceFps = 30.0f;

struct ClipConfig {
    std::string name;
    int count = 0;
    int duration = 0;
    std::vector<int> frames;
};

// Format (written by experimental/pikmin2_long_legs_bank.py):
//   P2_LONG_LEGS_ANIMATION_1
//   BigFoot
//   <clip> <count> <duration> <frame>...   (wait, landing, flick, dead in order)
// Frames strictly rise from 0 to duration-1. Any deviation rejects the file.
inline bool parse(std::istream& in, std::vector<ClipConfig>& out) {
    static const char* const names[] = {"wait", "landing", "flick", "dead"};
    std::string word;
    if (!(in >> word) || word != "P2_LONG_LEGS_ANIMATION_1") return false;
    if (!(in >> word) || word != "BigFoot") return false;
    std::vector<ClipConfig> parsed;
    for (const char* name : names) {
        ClipConfig clip;
        if (!(in >> clip.name >> clip.count >> clip.duration) || clip.name != name || clip.count < 2 ||
            clip.count > 64 || clip.duration < 2 || clip.duration > 10000)
            return false;
        for (int i = 0; i < clip.count; ++i) {
            int frame = 0;
            if (!(in >> frame) || frame < 0 || frame >= clip.duration || (i && frame <= clip.frames.back()))
                return false;
            clip.frames.push_back(frame);
        }
        if (clip.frames.front() != 0 || clip.frames.back() != clip.duration - 1) return false;
        parsed.push_back(clip);
    }
    if (in >> word) return false;
    out = std::move(parsed);
    return true;
}

// Index of the pose whose source frame is nearest `frame` (the nearest-pose
// fallback when interpolation is off or a private Shape cannot be built).
inline int nearestPose(const std::vector<int>& frames, float frame) {
    int best = 0;
    for (size_t i = 1; i < frames.size(); ++i)
        if (std::fabs(float(frames[i]) - frame) < std::fabs(float(frames[size_t(best)]) - frame)) best = int(i);
    return best;
}

struct Choice {
    const char* clip = "wait";
    float frame = 0.0f;  // source frame within the clip, 0..duration-1
};

// Looping clip position: J3D repeat playback steps from duration-1 back to 0.
inline float loopFrame(float seconds, int duration) {
    if (!(seconds >= 0.0f) || duration < 2) return 0.0f;
    const float frame = std::fmod(seconds * kSourceFps, float(duration));
    return std::min(frame, float(duration - 1));
}

inline float holdFrame(float seconds, int duration) {
    if (!(seconds >= 0.0f) || duration < 2) return 0.0f;
    return std::min(seconds * kSourceFps, float(duration - 1));
}

// Map the (unchanged) FSM state onto a clip. BigFoot has no walk clip (the
// source walks with IK only), so Walk, Wait and dormant Stay all show the
// looping `wait` clip. `stateSeconds` is time in the current Land/Flick state,
// `deadSeconds` time since Dead began, `clockSeconds` a monotonically running
// actor clock for loops. A corpse holds the dead clip's last visible pose.
inline Choice choose(P2LongLegsState state, float stateSeconds, float deadSeconds, float clockSeconds, bool corpse,
                     int waitDuration, int landingDuration, int flickDuration, int deadDuration) {
    Choice c;
    if (corpse) {
        c.clip = "dead";
        c.frame = float(std::max(deadDuration, 1) - 1);
        return c;
    }
    switch (state) {
    case P2LongLegsState::Dead:
        c.clip = "dead";
        c.frame = holdFrame(deadSeconds, deadDuration);
        break;
    case P2LongLegsState::Land:
        c.clip = "landing";
        c.frame = holdFrame(stateSeconds, landingDuration);
        break;
    case P2LongLegsState::Flick:
        c.clip = "flick";
        c.frame = holdFrame(stateSeconds, flickDuration);
        break;
    default:
        c.clip = "wait";
        c.frame = loopFrame(clockSeconds, waitDuration);
        break;
    }
    return c;
}

}  // namespace p2longlegspose
