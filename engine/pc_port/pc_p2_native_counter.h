#pragma once
#include "pc_p2_source_clock.h"

namespace p2source {
// Observe simulation-owned counters. Callers supply actual motion/loop identity.
class NativeCounter {
public:
    bool bind(const Clip& clip, double nativeLastFrame, std::uint64_t motionSerial) {
        if (!motionSerial || motionSerial <= serial_ || !std::isfinite(nativeLastFrame) ||
            nativeLastFrame <= 0 || clip.duration < 2 || !Clock::valid(clip)) return false;
        if (!clock_.start(clip)) return false;
        clip_ = clip; span_ = nativeLastFrame; serial_ = motionSerial;
        ordinal_ = 0; position_ = 0; active_ = true; return true;
    }
    Batch observe(std::uint64_t motionSerial, double nativeCounter, std::uint64_t loopOrdinal=0) {
        if (!active_) return error(Error::Inactive);
        if (motionSerial != serial_ || !std::isfinite(nativeCounter) || nativeCounter < 0 ||
            nativeCounter > span_ || loopOrdinal < ordinal_ || (!clip_.looping && loopOrdinal))
            return error(Error::InvalidAdvance);
        const double next = (nativeCounter / span_) * (clip_.duration - 1);
        if (clip_.looping && (next >= clip_.loopEnd || (loopOrdinal && next < clip_.loopBegin)))
            return error(Error::InvalidAdvance);
        if (clock_.finished())
            return nativeCounter == span_ ? clock_.advance(0) : error(Error::InvalidAdvance);
        const auto wraps = loopOrdinal - ordinal_;
        // Refuse before converting large ordinals to floating point.
        if (wraps > Clock::MaxWraps) return error(Error::Budget);
        const double delta = (clip_.looping ? double(wraps) * (clip_.loopEnd - clip_.loopBegin) : 0) + next - position_;
        if (delta < 0) return error(Error::InvalidAdvance); // Never guess restart vs loop.
        auto batch = clock_.advance(delta);
        if (batch) { position_ = next; ordinal_ = loopOrdinal; }
        return batch;
    }
    // Invoke only on authoritative nonloop END, never on interruption/seek.
    Batch finish(std::uint64_t motionSerial) {
        if (!active_) return error(Error::Inactive);
        if (motionSerial != serial_ || clip_.looping) return error(Error::InvalidAdvance);
        return clock_.advance(clip_.duration - clock_.frame());
    }
    // Explicit seek discards events and invalidates previous batches.
    bool seek(std::uint64_t motionSerial, double nativeCounter) {
        if (!active_ || motionSerial <= serial_ || !std::isfinite(nativeCounter) ||
            nativeCounter < 0 || nativeCounter > span_) return false;
        const double next = (nativeCounter / span_) * (clip_.duration - 1);
        if (!clock_.seek(next)) return false;
        serial_ = motionSerial; position_ = next; ordinal_ = 0; return true;
    }
    void cancel() { active_ = false; clock_.cancel(); }
    bool current(const Batch& batch) const { return active_ && clock_.current(batch); }
    double frame() const { return clock_.frame(); }
    double poseFrame() const { return clock_.poseFrame(); }
    bool finished() const { return clock_.finished(); }
private:
    Batch error(Error value) const { Batch b; b.error=value; b.generation=clock_.generation(); return b; }
    Clock clock_;
    Clip clip_;
    double span_=0, position_=0;
    std::uint64_t serial_=0, ordinal_=0;
    bool active_=false;
};
} // namespace p2source
