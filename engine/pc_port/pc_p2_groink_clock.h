#pragma once

#include <cmath>

// Bounded source-clock adapter for the isolated Groink policy. It samples no
// wall clock: the owning integration supplies elapsed seconds and runs its
// source update exactly once for every returned tick. Explicit fire events are
// deliberately outside this helper, so the owner can retain a pending event
// until one of those source ticks consumes it.
class P2GroinkSourceClock {
public:
    static constexpr double kSourceDelta = 1.0 / 30.0;
    static constexpr int kMaximumTicks = 4;

    void reset() { mDebt = 0.0; }

    // Fraction (0..1) of the next source tick already accumulated. Presentation
    // only: lets a 30 Hz source clip be drawn at the real frame rate.
    float fraction() const { return static_cast<float>(mDebt / kSourceDelta); }

    // Inactive, invalid, negative, and long-gap input discard all debt. A
    // long gap cannot turn into a later burst. Normal accumulation preserves
    // only the fractional remainder after a source tick.
    int step(double elapsedSeconds, bool active)
    {
        if (!active || !std::isfinite(elapsedSeconds) || elapsedSeconds < 0.0
            || elapsedSeconds >= 0.25) {
            reset();
            return 0;
        }

        mDebt += elapsedSeconds;
        if (!std::isfinite(mDebt)) {
            reset();
            return 0;
        }
        const int ticks = static_cast<int>(mDebt / kSourceDelta);
        if (ticks > kMaximumTicks) {
            reset();
            return kMaximumTicks;
        }
        mDebt -= static_cast<double>(ticks) * kSourceDelta;
        return ticks;
    }

private:
    double mDebt = 0.0;
};
