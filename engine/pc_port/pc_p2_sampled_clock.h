#pragma once
// Bounded sampled-animation clock/event contract (root #128, issue #431).
//
// Source time is independent of pose-bank density. A family advances this clock
// in source frames and reads:
//
//   * poseIndex() - a pure projection of the current source frame onto the
//     nearest baked pose via the existing p2animation::Clip selector, independent
//     of how many events have been dispatched; and
//   * Batch::events - the authored (frame,key) events crossed by that advance,
//     in stable source order, exactly once per crossing.
//
// Event delivery follows the shared source-clock policy (#247): the first
// positive, unpaused advance includes frame-0 events; regular advances emit
// (old, new]; a looping clip plays its intro once and repeats
// [loopBegin, loopEnd); a one-shot finishes at duration with poseFrame() clamped
// to duration-1. This is a sampled-bank contract, not a skeletal runtime and not
// a second wall clock. It does not call actors or execute damage/capture/drops.
#include "pc_p2_animation.h"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <istream>
#include <limits>
#include <string>
#include <vector>

namespace p2sampled {

struct Event {
    int frame = 0;
    std::string key;
};

struct Clip {
    p2animation::Clip poses;  // name/count/duration/frames; frames may be empty
    std::vector<Event> events;
    double loopBegin = 0.0;
    double loopEnd = -1.0;  // negative => one-shot

    bool looping() const { return loopEnd >= 0.0; }

    bool valid() const {
        if (poses.name.empty() || poses.name.size() > 68 || poses.count < 1
            || poses.count > 64 || poses.duration < 1 || poses.duration > 10000
            || events.size() > 4096) {
            return false;
        }
        if (!poses.frames.empty()) {
            if (int(poses.frames.size()) != poses.count) return false;
            long long previous = -1;
            for (int frame : poses.frames) {
                if (frame < 0 || frame >= poses.duration || frame <= previous) return false;
                previous = frame;
            }
        }
        long long previous = -1;
        for (const Event& event : events) {
            if (event.key.empty() || event.frame < 0 || event.frame >= poses.duration
                || event.frame < previous) {
                return false;
            }
            for (char ch : event.key) {
                if (ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r') return false;
            }
            previous = event.frame;
        }
        if (!looping()) {
            if (loopBegin != 0.0) return false;
        } else {
            if (!(loopBegin >= 0.0) || !(loopBegin < loopEnd) || !(loopEnd <= poses.duration)) {
                return false;
            }
            for (const Event& event : events) {
                if (double(event.frame) >= loopEnd) return false;
            }
        }
        return true;
    }

    // Nearest sampled pose to `frame`; ties keep the lower index. Reuses the
    // existing p2animation::Clip selection so adoption is selection-preserving.
    std::size_t poseIndex(double frame) const {
        if (poses.duration <= 1 || poses.count <= 1) return 0;
        double source = frame;
        if (!std::isfinite(source)) source = 0.0;
        if (source < 0.0) source = 0.0;
        if (source > double(poses.duration - 1)) source = double(poses.duration - 1);
        return poses.index(float(source / double(poses.duration - 1)));
    }
};

struct Occurrence {
    int frame = 0;
    std::string key;
    std::uint64_t cycle = 0;
};

enum class Error { None, Inactive, InvalidAdvance, Budget };

struct Batch {
    Error error = Error::None;
    std::uint64_t generation = 0;
    std::vector<Occurrence> events;
    explicit operator bool() const { return error == Error::None; }
};

class Clock {
public:
    static constexpr std::size_t MaxEvents = 4096, MaxWraps = 256;

    bool start(const Clip& clip) {
        if (!clip.valid() || generation_ == std::numeric_limits<std::uint64_t>::max()) return false;
        clip_ = clip;
        ++generation_;
        frame_ = 0.0;
        cycle_ = 0;
        active_ = true;
        entry_ = true;
        paused_ = false;
        return true;
    }

    bool restart() { return active_ && start(clip_); }

    bool seek(double frame) {
        if (!active_ || !std::isfinite(frame) || frame < 0.0
            || generation_ == std::numeric_limits<std::uint64_t>::max()) {
            return false;
        }
        if (clip_.looping() ? frame >= clip_.loopEnd : frame > double(clip_.poses.duration)) {
            return false;
        }
        ++generation_;
        frame_ = frame;
        cycle_ = 0;
        entry_ = false;
        return true;
    }

    void cancel() { active_ = false; entry_ = false; }
    void pause(bool paused) { paused_ = paused; }
    bool current(const Batch& batch) const {
        return active_ && bool(batch) && batch.generation == generation_;
    }

    double frame() const { return frame_; }
    double poseFrame() const {
        if (!active_) return 0.0;
        const double last = double(clip_.poses.duration - 1);
        return frame_ < last ? frame_ : last;
    }
    std::size_t poseIndex() const { return active_ ? clip_.poseIndex(poseFrame()) : 0; }
    std::uint64_t cycle() const { return cycle_; }
    std::uint64_t generation() const { return generation_; }
    bool finished() const {
        return active_ && !clip_.looping() && frame_ == double(clip_.poses.duration);
    }

    Batch advance(double delta) {
        if (!active_) return failure(Error::Inactive);
        if (!std::isfinite(delta) || delta < 0.0) return failure(Error::InvalidAdvance);
        Batch out;
        out.generation = generation_;
        if (paused_ || delta == 0.0) return out;

        double pos = frame_, remaining = delta;
        std::uint64_t cycle = cycle_;
        std::size_t wraps = 0;
        std::vector<Occurrence> staged;

        auto emit = [&](double from, double to, bool includeFrom) {
            for (const Event& event : clip_.events) {
                const double ef = double(event.frame);
                if ((ef > from || (includeFrom && ef == from)) && ef <= to) {
                    if (staged.size() == MaxEvents) return false;
                    staged.push_back(Occurrence{event.frame, event.key, cycle});
                }
            }
            return true;
        };

        if (entry_ && !emit(pos, pos, true)) return failure(Error::Budget);
        while (remaining > 0.0) {
            const double end = clip_.looping() ? clip_.loopEnd : double(clip_.poses.duration);
            const double distance = end - pos;
            if (remaining < distance) {
                if (!emit(pos, pos + remaining, false)) return failure(Error::Budget);
                pos += remaining;
                remaining = 0.0;
            } else {
                if (!emit(pos, end, false)) return failure(Error::Budget);
                remaining -= distance;
                if (!clip_.looping()) {
                    pos = end;
                    break;
                }
                if (++wraps > MaxWraps || cycle == std::numeric_limits<std::uint64_t>::max()) {
                    return failure(Error::Budget);
                }
                ++cycle;
                pos = clip_.loopBegin;
                if (!emit(pos, pos, true)) return failure(Error::Budget);
            }
        }
        frame_ = pos;
        cycle_ = cycle;
        entry_ = false;
        out.events = std::move(staged);
        return out;
    }

private:
    Batch failure(Error error) const {
        Batch batch;
        batch.error = error;
        batch.generation = generation_;
        return batch;
    }

    Clip clip_;
    double frame_ = 0.0;
    std::uint64_t generation_ = 0, cycle_ = 0;
    bool active_ = false, entry_ = false, paused_ = false;
};

// Canonical P2_ANIM_CLOCK_1 text parser. Trailing data is refused.
inline bool parse(std::istream& in, std::vector<Clip>& out) {
    std::string magic;
    int count = 0;
    if (!(in >> magic >> count) || magic != "P2_ANIM_CLOCK_1" || count < 0 || count > 4096) {
        return false;
    }
    std::vector<Clip> parsed;
    for (int i = 0; i < count; ++i) {
        Clip clip;
        std::string token;
        int poseCount = 0, eventCount = 0;
        if (!(in >> token) || token != "clip" || !(in >> clip.poses.name >> clip.poses.duration
            >> clip.loopBegin >> clip.loopEnd >> poseCount >> eventCount)
            || poseCount < 1 || poseCount > 64 || eventCount < 0 || eventCount > 4096) {
            return false;
        }
        clip.poses.count = poseCount;
        if (!(in >> token) || token != "poses") return false;
        for (int p = 0; p < poseCount; ++p) {
            int frame = 0;
            if (!(in >> frame)) return false;
            clip.poses.frames.push_back(frame);
        }
        for (int e = 0; e < eventCount; ++e) {
            Event event;
            if (!(in >> token) || token != "event" || !(in >> event.frame >> event.key)) return false;
            clip.events.push_back(event);
        }
        if (!clip.valid()) return false;
        parsed.push_back(clip);
    }
    if (in >> magic) return false;
    out = parsed;
    return true;
}

}  // namespace p2sampled
