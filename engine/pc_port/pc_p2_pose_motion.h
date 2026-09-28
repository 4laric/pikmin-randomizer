#pragma once
// Central P2 pose-playback tunables and helpers (#895).
//
// Engine-free so tools/p2_pose_motion_test.cpp can include it directly. Every
// P2 draw path that plays a baked pose bank (batch2, batch3 and the dedicated
// family modules) takes its fidelity knobs from here, so one place documents
// and overrides them:
//
//   PIKMIN_P2_INTERPOLATION=0     nearest baked pose, no vertex lerp (A/B)
//   PIKMIN_P2_CROSSFADE_MS=<ms>   clip-change crossfade length (default 150,
//                                 0 disables; clamped to 0..1000)
//   PIKMIN_P2_MOVE_ENTER=<v>      horizontal speed^2 that enters the move clip
//                                 (default 1.5)
//   PIKMIN_P2_MOVE_LEAVE=<v>      speed^2 that falls back to wait (default 0.5)
//   PIKMIN_P2_CLIP_DWELL_MS=<ms>  minimum move/wait dwell (default 250)
//   PIKMIN_P2_FALLBACK_SHAPES=<n> full pose Shapes kept per clip for the
//                                 non-vector fallback (default 4, 1..64)
//
// Gameplay timing stays on the authoritative P1 clock: these helpers only pick
// what is drawn. See docs/PIKMIN2_POSE_FIDELITY.md.
#include "pc_p2_pose_blend.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <vector>

namespace p2motion {

struct Tunables {
    bool lerp = true;               // vertex lerp between bracketing poses
    float crossfadeSeconds = 0.15f; // clip-change crossfade
    float moveEnter = 1.5f;         // speed^2 (x/z) entering the move clip
    float moveLeave = 0.5f;         // speed^2 (x/z) leaving the move clip
    float minDwellSeconds = 0.25f;  // move/wait minimum dwell
    int fallbackShapes = 4;         // Shapes per clip when vectors are unusable
};

inline float envNumber(const char* name, float fallback, float lo, float hi) {
    const char* raw = std::getenv(name);
    if (!raw || !*raw) return fallback;
    char* end = nullptr;
    const double value = std::strtod(raw, &end);
    if (end == raw || !std::isfinite(value)) return fallback;
    return float(std::max(double(lo), std::min(double(hi), value)));
}

inline Tunables loadTunables() {
    Tunables t;
    const char* lerp = std::getenv("PIKMIN_P2_INTERPOLATION");
    t.lerp = !(lerp && lerp[0] == '0');
    t.crossfadeSeconds = envNumber("PIKMIN_P2_CROSSFADE_MS", 150.f, 0.f, 1000.f) / 1000.f;
    t.moveEnter = envNumber("PIKMIN_P2_MOVE_ENTER", 1.5f, 0.f, 1.0e6f);
    t.moveLeave = envNumber("PIKMIN_P2_MOVE_LEAVE", 0.5f, 0.f, 1.0e6f);
    if (t.moveLeave > t.moveEnter) t.moveLeave = t.moveEnter;
    t.minDwellSeconds = envNumber("PIKMIN_P2_CLIP_DWELL_MS", 250.f, 0.f, 5000.f) / 1000.f;
    t.fallbackShapes = int(envNumber("PIKMIN_P2_FALLBACK_SHAPES", 4.f, 1.f, 64.f));
    return t;
}

// Read once per process; tests use loadTunables()/Tunables directly.
inline const Tunables& tunables() {
    static const Tunables t = loadTunables();
    return t;
}

// Nearest pose for a uniform phase in [0,1] (rounds, never truncates).
inline std::size_t nearestIndex(float phase, std::size_t count) {
    if (count <= 1) return 0;
    if (!std::isfinite(phase)) phase = 0.f;
    phase = std::max(0.f, std::min(1.f, phase));
    const std::size_t index = std::size_t(phase * float(count - 1) + 0.5f);
    return std::min(index, count - 1);
}

// Move/wait selection with hysteresis and a minimum dwell, advanced from the
// simulation update (seconds), read at draw time.
class MoveGate {
    bool moving_ = false;
    float dwell_ = 1.0e9f;
public:
    bool moving() const { return moving_; }
    void reset() { moving_ = false; dwell_ = 1.0e9f; }
    // Returns true when the state flipped.
    bool update(float speed2, float seconds, const Tunables& t) {
        if (!std::isfinite(seconds) || seconds < 0.f) seconds = 0.f;
        if (!std::isfinite(speed2) || speed2 < 0.f) speed2 = 0.f;
        dwell_ = std::min(1.0e9f, dwell_ + seconds);
        if (dwell_ < t.minDwellSeconds) return false;
        const bool next = moving_ ? speed2 >= t.moveLeave : speed2 > t.moveEnter;
        if (next == moving_) return false;
        moving_ = next;
        dwell_ = 0.f;
        return true;
    }
};

// Clip-change crossfade over captured displayed geometry. advance() belongs
// to the simulation update; mix() to rendering. An interrupted fade restarts
// from whatever was last displayed, so there is never a pop.
class Fade {
    p2pose::Pose from_;
    float elapsed_ = 0.f, duration_ = 0.f;
    bool active_ = false;
public:
    void reset() { active_ = false; elapsed_ = duration_ = 0.f; }
    bool active() const { return active_; }
    bool begin(const p2pose::Pose& displayed, float seconds) {
        if (!(seconds > 0.f) || !std::isfinite(seconds) || displayed.positions.empty()
                || displayed.normals.empty()) {
            reset();
            return false;
        }
        from_ = displayed;
        elapsed_ = 0.f;
        duration_ = seconds;
        active_ = true;
        return true;
    }
    void advance(float seconds) {
        if (!active_ || !std::isfinite(seconds) || seconds < 0.f) return;
        elapsed_ = std::min(duration_, elapsed_ + seconds);
    }
    // Linear progress 0..1 (1 when idle).
    float progress() const { return active_ && duration_ > 0.f ? std::min(1.f, elapsed_ / duration_) : 1.f; }
    // Smoothstep-eased weight of the new clip.
    float weight() const { const float p = progress(); return p * p * (3.f - 2.f * p); }
    // out = from -> target at weight(). Finishes the fade once complete.
    bool mix(const p2pose::Pose& target, p2pose::Pose& out) {
        if (!active_) return false;
        const float w = weight();
        if (w >= 1.f) { active_ = false; return false; }
        if (from_.positions.size() != target.positions.size()
                || from_.normals.size() != target.normals.size()) {
            reset();
            return false;
        }
        out.positions.resize(target.positions.size());
        out.normals.resize(target.normals.size());
        if (!p2pose::blendInto(from_, target, w, out)) { reset(); return false; }
        return true;
    }
};

// Pose indices kept as full Shapes (evenly spread, first and last included).
inline std::vector<std::size_t> shapeSlots(std::size_t count, std::size_t maxShapes) {
    std::vector<std::size_t> out;
    if (!count) return out;
    if (maxShapes < 1) maxShapes = 1;
    if (count <= maxShapes) {
        for (std::size_t i = 0; i < count; ++i) out.push_back(i);
        return out;
    }
    if (maxShapes == 1) return {0};
    for (std::size_t i = 0; i < maxShapes; ++i) {
        const std::size_t slot = std::size_t(std::floor(double(i) * double(count - 1) / double(maxShapes - 1) + 0.5));
        if (out.empty() || slot != out.back()) out.push_back(slot);
    }
    return out;
}

inline bool isSlot(const std::vector<std::size_t>& slots, std::size_t index) {
    return std::binary_search(slots.begin(), slots.end(), index);
}

inline std::size_t nearestSlot(const std::vector<std::size_t>& slots, std::size_t index) {
    if (slots.empty()) return 0;
    std::size_t best = slots.front();
    for (std::size_t slot : slots) {
        const std::size_t d = slot > index ? slot - index : index - slot;
        const std::size_t b = best > index ? best - index : index - best;
        if (d < b) best = slot;
    }
    return best;
}

// Resident bytes of one decoded pose (positions + normals).
inline std::size_t poseBytes(const p2pose::Pose& pose) {
    return (pose.positions.size() + pose.normals.size()) * sizeof(p2pose::Vec);
}

// Resolve the bracketing interval for a source frame. With lerp off the
// interval collapses onto the nearer pose.
inline bool interval(const std::vector<int>& frames, float sourceFrame, bool lerp, p2pose::Interval& out) {
    if (!p2pose::bracket(frames, sourceFrame, out)) return false;
    if (!lerp && out.left != out.right) {
        const std::size_t pick = out.weight < 0.5f ? out.left : out.right;
        out = {pick, pick, 0.f};
    }
    return true;
}

}  // namespace p2motion
