#pragma once
// Consumer adoption of the bounded sampled-animation clock (#431) for the
// batch-2 pose-bank draw path. See docs/PIKMIN2_SAMPLED_CLOCK_EVENTS.md.
//
// The batch-2 draw path selects whichever clip the P1 animator is playing and
// then projects the P1 counter onto the sampled bank. This header replaces the
// per-draw phase expression with an explicit source-frame clock that keeps pose
// selection and event delivery independent, reusing the legacy nearest-pose
// selector so adoption is selection-preserving.
#include "pc_p2_sampled_clock.h"

#include <cmath>
#include <cstddef>
#include <string>
#include <utility>
#include <vector>

namespace p2batch2clock {

// One P2_*_BANK_1 clip row: authored source length, uniform pose count and the
// authored "frame:key,..." events. The bank only records a pose count, so the
// converted clock clip keeps uniform sampling (empty pose frames) and
// Clock::poseIndex() reproduces the legacy Clip::index(phase) selection.
// P2_BANK_FRAMES_1 extension: an optional `frames f0,f1,...` trailer carries
// explicit per-pose source frames. With a valid trailer the clip uses true
// bracketing; without it synthesis stays uniform (empty frames) with
// uniform-bracketing degradation when interpolation is on. A malformed trailer
// disables interpolation for that clip (nearest-pose fallback), never fail().
struct Row {
    std::string name;
    int sourceFrames = 0;
    int poseCount = 0;
    std::vector<p2sampled::Event> events;
    std::vector<int> poseFrames;
    bool framesMalformed = false;
};

// Parse one `f0,f1,...` trailer token (no spaces). Returns false on any
// non-numeric/empty/oversized input; range/endpoint ordering is validated by
// the caller against the clip duration.
inline bool parseFramesList(const std::string& token, std::vector<int>& out) {
    out.clear();
    if (token.empty() || token.size() > 512) return false;
    size_t at = 0;
    while (true) {
        const size_t comma = token.find(',', at);
        const std::string part =
            comma == std::string::npos ? token.substr(at) : token.substr(at, comma - at);
        if (part.empty() || part.size() > 6) return false;
        for (char c : part) {
            if (c < '0' || c > '9') return false;
        }
        long value = 0;
        try {
            value = std::stol(part);
        } catch (...) {
            return false;
        }
        if (value < 0 || value > 10000) return false;
        out.push_back(int(value));
        if (out.size() > 64) return false;
        if (comma == std::string::npos) break;
        at = comma + 1;
    }
    if (out.empty()) return false;
    return true;
}

// Uniform synthesis matching experimental/pikmin2_animation.py sample_frames:
// round(i*(duration-1)/(count-1)), clamped to [0, duration-1].
inline std::vector<int> uniformFrames(int count, int duration) {
    std::vector<int> out;
    if (count <= 0 || duration <= 0) return out;
    if (count == 1) {
        out.push_back(0);
        return out;
    }
    for (int i = 0; i < count; ++i) {
        const double v = double(i) * double(duration - 1) / double(count - 1);
        int frame = int(std::floor(v + 0.5));
        if (frame < 0) frame = 0;
        if (frame >= duration) frame = duration - 1;
        out.push_back(frame);
    }
    return out;
}

// Frames to bracket for one clip: explicit when present, else uniform.
inline std::vector<int> bracketFramesFor(const p2sampled::Clip& clip) {
    if (!clip.poses.frames.empty()) return clip.poses.frames;
    return uniformFrames(clip.poses.count, clip.poses.duration);
}

// The bank's uniform sampling is encoded as a full-duration loop. A clip with a
// missing/one-frame source length falls back to its pose count so selection
// stays a strict function of the sampled phase.
inline p2sampled::Clip makeClip(const Row& row) {
    p2sampled::Clip clip;
    clip.poses.name = row.name;
    clip.poses.count = row.poseCount > 0 ? row.poseCount : 1;
    int duration = row.sourceFrames;
    if (duration < 2) {
        duration = row.poseCount >= 2 ? row.poseCount : 2;
    }
    clip.poses.duration = duration;
    if (!row.framesMalformed && !row.poseFrames.empty()
            && int(row.poseFrames.size()) == clip.poses.count) {
        bool ok = true;
        for (size_t i = 0; i < row.poseFrames.size(); ++i) {
            const int frame = row.poseFrames[i];
            if (frame < 0 || frame >= duration) {
                ok = false;
                break;
            }
            if (i == 0 && frame != 0) {
                ok = false;
                break;
            }
            if (i > 0 && frame <= row.poseFrames[i - 1]) {
                ok = false;
                break;
            }
        }
        if (ok && row.poseFrames.back() != duration - 1) ok = false;
        if (ok) clip.poses.frames = row.poseFrames;
    }
    clip.events = row.events;
    clip.loopBegin = 0.0;
    clip.loopEnd = double(duration);
    return clip;
}

struct Step {
    bool ok = false;
    std::size_t pose = 0;
    std::vector<p2sampled::Occurrence> events;
};

// Advances one actor's clock in source frames derived from the authoritative P1
// animator counter. Within a cycle the clock only moves forward; a clip change
// or a non-forward target (P1 loop wrap) restarts the cycle, so authored events
// fire exactly once per forward crossing.
class Cursor {
public:
    bool start(const p2sampled::Clip& clip) {
        clip_ = clip;
        active_ = clock_.start(clip_);
        last_ = -1.0;
        return active_;
    }

    bool active() const { return active_; }

    Step stepTo(double sourceFrame) {
        Step out;
        if (!active_) {
            return out;
        }
        if (!(sourceFrame >= 0.0)) {
            sourceFrame = 0.0;
        }
        if (last_ < 0.0 || sourceFrame < last_) {
            if (!clock_.restart()) {
                active_ = false;
                return out;
            }
            last_ = 0.0;
        }
        p2sampled::Batch batch = clock_.advance(sourceFrame - last_);
        if (!batch) {
            return out;
        }
        out.ok = true;
        out.pose = clock_.poseIndex();
        out.events = std::move(batch.events);
        last_ = sourceFrame;
        return out;
    }

private:
    p2sampled::Clip clip_;
    p2sampled::Clock clock_;
    double last_ = -1.0;
    bool active_ = false;
};

// Parse the bank's authored event token ("-" for none, else "frame:key,...").
inline bool parseEvents(const std::string& token, std::vector<p2sampled::Event>& out) {
    if (token == "-") {
        return true;
    }
    size_t at = 0;
    while (at <= token.size()) {
        const size_t comma = token.find(',', at);
        const size_t end = comma == std::string::npos ? token.size() : comma;
        const std::string item = token.substr(at, end - at);
        const size_t colon = item.find(':');
        if (colon == std::string::npos || colon == 0 || colon + 1 >= item.size()) {
            return false;
        }
        int frame = 0;
        for (size_t i = 0; i < colon; ++i) {
            if (item[i] < '0' || item[i] > '9') {
                return false;
            }
            frame = frame * 10 + (item[i] - '0');
            if (frame > 100000) {
                return false;
            }
        }
        p2sampled::Event event;
        event.frame = frame;
        event.key = item.substr(colon + 1);
        out.push_back(std::move(event));
        if (comma == std::string::npos) {
            break;
        }
        at = comma + 1;
    }
    return true;
}

}  // namespace p2batch2clock
