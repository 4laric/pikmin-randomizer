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
//                                 (default 1.0, the legacy `speed2 > 1` test)
//   PIKMIN_P2_MOVE_LEAVE=<v>      speed^2 below which a moving actor falls back
//                                 to wait (default 0.5; the 0.5..1.0 band is the
//                                 hysteresis: a slow actor already moving keeps
//                                 its move clip instead of flickering)
//   PIKMIN_P2_CLIP_DWELL_MS=<ms>  minimum move/wait dwell (default 250)
//   PIKMIN_P2_FALLBACK_SHAPES=<n> full pose Shapes kept per clip whose vectors
//                                 decode (default 4, 1..64). A clip whose
//                                 vectors do not decode loads every pose as a
//                                 Shape instead (loud P2_POSE_LOADER_FALLBACK).
//
// Gameplay timing stays on the authoritative P1 clock: these helpers only pick
// what is drawn. See docs/PIKMIN2_POSE_FIDELITY.md.
#include "pc_p2_pose_blend.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <string>
#include <vector>

namespace p2motion {

struct Tunables {
    bool lerp = true;               // vertex lerp between bracketing poses
    float crossfadeSeconds = 0.15f; // clip-change crossfade
    float moveEnter = 1.0f;         // speed^2 (x/z) entering the move clip (legacy threshold)
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
    t.moveEnter = envNumber("PIKMIN_P2_MOVE_ENTER", 1.0f, 0.f, 1.0e6f);
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


// Largest per-vertex position distance between two poses (0 on mismatch).
inline float maxDistance(const p2pose::Pose& a, const p2pose::Pose& b) {
    if (a.positions.size() != b.positions.size()) return 0.f;
    double best = 0.0;
    for (std::size_t i = 0; i < a.positions.size(); ++i) {
        const double dx = double(a.positions[i].x) - b.positions[i].x;
        const double dy = double(a.positions[i].y) - b.positions[i].y;
        const double dz = double(a.positions[i].z) - b.positions[i].z;
        best = std::max(best, dx * dx + dy * dy + dz * dz);
    }
    return float(std::sqrt(best));
}

// Loop seam of a baked clip (#895). J3D repeat playback steps from source
// frame duration-1 straight back to frame 0, so the seam spans one source
// frame. The retail audit (scripts/p2_loop_seam_audit.py) shows most P2 loops
// are authored that way: frame duration-1 is NOT a copy of frame 0, it is one
// ordinary step before it, so a P1 wrap that shows pose last -> pose 0 is
// continuous. Clips whose seam jumps (one-shot acts such as Chappy waitact2,
// root-motion flights) are not; a P1 wrap of those gets a short blend instead
// of a pop.
//
// Continuous: the seam distance is at most `factor` times the clip's largest
// per-source-frame step between adjacent baked poses, with a small absolute
// floor so a still clip is never flagged.
template <class PoseAt>
inline bool seamContinuous(std::size_t count, PoseAt poseAt, const std::vector<int>& frames,
                           float factor = 3.f, float floor = 0.05f) {
    if (count < 2 || frames.size() != count) return true;
    float step = 0.f;
    for (std::size_t i = 0; i + 1 < count; ++i) {
        const int span = frames[i + 1] - frames[i];
        if (span <= 0) return true;
        step = std::max(step, maxDistance(poseAt(i), poseAt(i + 1)) / float(span));
    }
    const float seam = maxDistance(poseAt(count - 1), poseAt(0));
    return seam <= std::max(floor, factor * step);
}

// Death clips (#895). Several retail P2 death animations end with the whole
// body scaled to zero (Sokkuri dead1/pdead1, UmiMushi dead1, SnakeCrow and
// SnakeWhole dead): P2 then hands the carcass to a separate pellet. The P1
// port keeps the actor's own body as the corpse, so a death clip plays only
// up to its last visible pose and the corpse holds that pose (the previous
// sparse bake could not convert the collapsed frames at all, which kept the
// corpse visible by accident).
inline bool isDeathClip(const std::string& name) {
    return name.rfind("dead", 0) == 0 || name.rfind("pdead", 0) == 0 || name == "kagebozu_dead";
}

// Bounding-box diagonal of a pose's positions.
inline float extent(const p2pose::Pose& pose) {
    if (pose.positions.empty()) return 0.f;
    p2pose::Vec lo = pose.positions.front(), hi = lo;
    for (const auto& v : pose.positions) {
        lo = {std::min(lo.x, v.x), std::min(lo.y, v.y), std::min(lo.z, v.z)};
        hi = {std::max(hi.x, v.x), std::max(hi.y, v.y), std::max(hi.z, v.z)};
    }
    const double dx = double(hi.x) - lo.x, dy = double(hi.y) - lo.y, dz = double(hi.z) - lo.z;
    return float(std::sqrt(dx * dx + dy * dy + dz * dz));
}

// Last pose whose extent is at least `fraction` of the clip's largest (the
// last visible pose; count-1 when nothing collapses).
template <class PoseAt>
inline std::size_t visibleEnd(std::size_t count, PoseAt poseAt, float fraction = 0.2f) {
    if (!count) return 0;
    float biggest = 0.f;
    for (std::size_t i = 0; i < count; ++i) biggest = std::max(biggest, extent(poseAt(i)));
    for (std::size_t i = count; i-- > 0;)
        if (extent(poseAt(i)) >= fraction * biggest) return i;
    return count - 1;
}

// A P1 loop wrap: the same clip's source frame jumped back by more than half
// the clip. Forward motion and small jitters are not wraps.
inline bool isWrap(float lastFrame, float sourceFrame, int lastBakedFrame) {
    if (!(lastFrame >= 0.f) || !std::isfinite(sourceFrame) || lastBakedFrame < 2) return false;
    return lastFrame - sourceFrame > 0.5f * float(lastBakedFrame);
}

// What one draw should show (engine-free; p2pose::present writes it into the
// actor's private Shape).
struct Shown {
    const p2pose::Pose* pose = nullptr;
    bool crossfadeStarted = false;  // a clip change began a fade
    bool wrapBlend = false;         // a discontinuous loop seam began a fade
    p2pose::Interval span;
};

// Per-actor presentation state: bracket/lerp at a source frame, and crossfade
// from the last displayed geometry on a clip change or across a
// discontinuous loop seam. advance() runs from the simulation update even
// while the actor is not drawn; a display older than staleSeconds (the actor
// was off-screen) is never faded from, so a later clip change or wrap
// switches directly instead of blending from an out-of-date pose.
class Presenter {
public:
    static constexpr float staleSeconds = 0.25f;
    p2pose::Pose scratch, mixed, display;
    Fade fade;
    std::string clip;
    float lastFrame = -1.f;
    float idle = 1.0e9f;  // seconds since the last committed draw
    bool shown = false;

    void reset() {
        fade.reset();
        clip.clear();
        lastFrame = -1.f;
        idle = 1.0e9f;
        shown = false;
    }
    void advance(float seconds) {
        if (!std::isfinite(seconds) || seconds < 0.f) return;
        fade.advance(seconds);
        idle = std::min(1.0e9f, idle + seconds);
    }
    bool fresh() const { return shown && idle <= staleSeconds; }

    template <class PoseAt>
    Shown select(const std::string& name, std::size_t count, PoseAt poseAt, const std::vector<int>& frames,
                 float sourceFrame, bool seamOk, const Tunables& tune) {
        Shown out;
        if (!count || frames.size() != count || !interval(frames, sourceFrame, tune.lerp, out.span)
                || out.span.left >= count || out.span.right >= count)
            return out;
        const p2pose::Pose& a = poseAt(out.span.left);
        const p2pose::Pose& b = poseAt(out.span.right);
        if (scratch.positions.size() != a.positions.size() || scratch.normals.size() != a.normals.size()) {
            scratch.positions.resize(a.positions.size());
            scratch.normals.resize(a.normals.size());
        }
        if (!p2pose::blendInto(a, b, out.span.weight, scratch)) return out;
        if (clip != name) {
            if (fresh() && !clip.empty()) out.crossfadeStarted = fade.begin(display, tune.crossfadeSeconds);
            else fade.reset();
            clip = name;
        } else if (!seamOk && isWrap(lastFrame, sourceFrame, frames.back())) {
            if (fresh()) out.wrapBlend = fade.begin(display, tune.crossfadeSeconds);
            else fade.reset();
        } else if (!fresh()) {
            fade.reset();  // never finish a fade from a stale display
        }
        lastFrame = sourceFrame;
        out.pose = &scratch;
        if (fade.active()) {
            if (mixed.positions.size() != scratch.positions.size() || mixed.normals.size() != scratch.normals.size()) {
                mixed.positions.resize(scratch.positions.size());
                mixed.normals.resize(scratch.normals.size());
            }
            if (fade.mix(scratch, mixed)) out.pose = &mixed;
        }
        return out;
    }
    // Record what was actually drawn.
    void commit(const p2pose::Pose& drawn) {
        display.positions.assign(drawn.positions.begin(), drawn.positions.end());
        display.normals.assign(drawn.normals.begin(), drawn.normals.end());
        shown = true;
        idle = 0.f;
    }
};

}  // namespace p2motion
