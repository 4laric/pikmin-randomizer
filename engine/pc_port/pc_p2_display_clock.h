#pragma once
#include "pc_p2_source_clock.h"

namespace p2display {
enum class Advance { Ok, RecoveredGap, Invalid };
// Noninteractive displays only: owns no gameplay events. Preserve SDL wall time.
class Clock {
public:
    bool start(int duration, std::uint32_t tick) {
        if (!clock_.start(p2source::Clip{double(duration), true, 0, double(duration), {}})) return false;
        duration_ = duration; previous_ = tick; ready_ = true; return true;
    }
    void reset() { clock_.cancel(); ready_ = false; }
    Advance update(std::uint32_t tick) {
        if (!ready_) return Advance::Invalid;
        const double frames = double(std::uint32_t(tick - previous_)) * 0.03;
        const auto result = clock_.advance(frames);
        if (result) { previous_ = tick; return Advance::Ok; }
        if (result.error != p2source::Error::Budget) return Advance::Invalid;
        // This adapter never accepts event metadata, so a visual seek loses no events.
        if (!clock_.seek(std::fmod(clock_.frame() + frames, duration()))) return Advance::Invalid;
        previous_ = tick; return Advance::RecoveredGap;
    }
    double frame() const { return clock_.frame(); }
private:
    double duration() const { return duration_; }
    p2source::Clock clock_;
    std::uint32_t previous_ = 0;
    double duration_ = 0;
    bool ready_ = false;
};
} // namespace p2display
