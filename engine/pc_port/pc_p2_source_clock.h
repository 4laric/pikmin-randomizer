#pragma once
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

// Source time is independent of pose-bank density. No native callbacks here.
namespace p2source {
struct Event { double frame; std::uint32_t id; };
struct Clip {
    double duration = 0; // Source interval [0, duration); last pose is duration-1.
    bool looping = false;
    double loopBegin = 0, loopEnd = 0; // Intro followed by [loopBegin, loopEnd).
    std::vector<Event> events; // Stable source order; equal-frame events allowed.
};
struct Occurrence { std::uint32_t id; double frame; std::uint64_t cycle; };
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
    static bool valid(const Clip& c) {
        if (!std::isfinite(c.duration) || c.duration < 1 || c.duration > 1000000 ||
            c.events.size() > MaxEvents) return false;
        if (c.looping && (!std::isfinite(c.loopBegin) || !std::isfinite(c.loopEnd) ||
            c.loopBegin < 0 || c.loopBegin >= c.loopEnd || c.loopEnd > c.duration)) return false;
        double previous = -1;
        for (const auto& e : c.events) {
            if (!std::isfinite(e.frame) || e.frame < 0 || e.frame >= c.duration ||
                (c.looping && e.frame >= c.loopEnd) || e.frame < previous) return false;
            previous = e.frame;
        }
        return true;
    }
    bool start(const Clip& clip) {
        if (!valid(clip) || generation_ == std::numeric_limits<std::uint64_t>::max()) return false;
        clip_ = clip; ++generation_; frame_ = 0; cycle_ = 0;
        active_ = true; entry_ = true; paused_ = false;
        return true;
    }
    bool restart() { return active_ && start(clip_); }
    // Seek discards crossed events and invalidates already returned batches.
    bool seek(double frame) {
        if (!active_ || !std::isfinite(frame) || frame < 0 ||
            (clip_.looping ? frame >= clip_.loopEnd : frame > clip_.duration) ||
            generation_ == std::numeric_limits<std::uint64_t>::max()) return false;
        ++generation_; frame_ = frame; cycle_ = 0; entry_ = false;
        return true;
    }
    void cancel() { active_ = false; entry_ = false; }
    void pause(bool paused) { paused_ = paused; }
    bool current(const Batch& b) const { return active_ && bool(b) && b.generation == generation_; }
    double frame() const { return frame_; }
    double poseFrame() const { return !active_ ? 0 : (frame_ < clip_.duration - 1 ? frame_ : clip_.duration - 1); }
    std::uint64_t cycle() const { return cycle_; }
    std::uint64_t generation() const { return generation_; }
    bool finished() const { return active_ && !clip_.looping && frame_ == clip_.duration; }

    Batch advanceSeconds(double seconds, double sourceFps) {
        if (!std::isfinite(seconds) || seconds < 0 || !std::isfinite(sourceFps) || sourceFps <= 0)
            return failure(Error::InvalidAdvance);
        return advance(seconds * sourceFps);
    }
    Batch advance(double delta) {
        if (!active_) return failure(Error::Inactive);
        if (!std::isfinite(delta) || delta < 0) return failure(Error::InvalidAdvance);
        Batch out; out.generation = generation_;
        if (paused_ || delta == 0) return out;
        // Stage all state and output: a budget rejection consumes nothing.
        double pos = frame_, remaining = delta;
        std::uint64_t cycle = cycle_;
        std::size_t wraps = 0;
        auto emit = [&](double from, double to, bool includeFrom) {
            for (const auto& e : clip_.events) {
                if ((e.frame > from || (includeFrom && e.frame == from)) && e.frame <= to) {
                    if (out.events.size() == MaxEvents) return false;
                    out.events.push_back({e.id, e.frame, cycle});
                }
            }
            return true;
        };
        if (entry_ && !emit(pos, pos, true)) return failure(Error::Budget);
        while (remaining > 0) {
            const double end = clip_.looping ? clip_.loopEnd : clip_.duration;
            const double distance = end - pos;
            if (remaining < distance) {
                if (!emit(pos, pos + remaining, false)) return failure(Error::Budget);
                pos += remaining; remaining = 0;
            } else {
                if (!emit(pos, end, false)) return failure(Error::Budget);
                remaining -= distance;
                if (!clip_.looping) { pos = end; break; }
                if (++wraps > MaxWraps || cycle == std::numeric_limits<std::uint64_t>::max())
                    return failure(Error::Budget);
                ++cycle; pos = clip_.loopBegin;
                if (!emit(pos, pos, true)) return failure(Error::Budget);
            }
        }
        frame_ = pos; cycle_ = cycle; entry_ = false;
        return out;
    }
private:
    Batch failure(Error error) const { Batch b; b.error = error; b.generation = generation_; return b; }
    Clip clip_;
    double frame_ = 0;
    std::uint64_t generation_ = 0, cycle_ = 0;
    bool active_ = false, entry_ = false, paused_ = false;
};
} // namespace p2source
