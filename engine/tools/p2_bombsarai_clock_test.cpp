#include "../pc_port/pc_p2_bombsarai_clock.h"

#include <cmath>
#include <cstdio>
#include <limits>

namespace {
bool check(bool value, const char* label)
{
    if (value) return true;
    std::fprintf(stderr, "FAIL %s\n", label);
    return false;
}

bool rate(double frameSeconds, int frames, const char* label)
{
    P2BombSaraiSourceClock clock;
    int ticks = 0;
    for (int frame = 0; frame < frames; ++frame) ticks += clock.step(frameSeconds, true);
    return check(ticks == 30, label);
}
}

int main()
{
    bool ok = true;
    ok &= rate(1.0 / 60.0, 60, "60 Hz produces 30 source ticks");
    ok &= rate(1.0 / 120.0, 120, "120 Hz produces 30 source ticks");
    ok &= rate(1.0 / 30.0, 30, "30 Hz produces 30 source ticks");

    P2BombSaraiSourceClock clock;
    ok &= check(clock.step(0.20, true) == P2BombSaraiSourceClock::kMaximumTicks,
                "sub-gap stall caps ticks");
    ok &= check(clock.step(0.0, true) == 0, "capped stall debt discarded");
    ok &= check(clock.step(1.0 / 30.0, true) == 1, "no later capped burst");
    ok &= check(clock.step(0.25, true) == 0, "large gap drops debt");
    ok &= check(clock.step(1.0 / 30.0, true) == 1, "large gap leaves no debt");

    clock.step(1.0 / 60.0, true);
    ok &= check(clock.step(1.0 / 60.0, false) == 0, "pause resets debt");
    ok &= check(clock.step(1.0 / 60.0, true) == 0, "resume has no paused debt");
    ok &= check(clock.step(-0.01, true) == 0, "negative elapsed resets debt");
    ok &= check(clock.step(std::numeric_limits<double>::infinity(), true) == 0,
                "infinite elapsed resets debt");
    ok &= check(clock.step(std::numeric_limits<double>::quiet_NaN(), true) == 0,
                "NaN elapsed resets debt");
    clock.step(1.0 / 60.0, true);
    clock.reset();
    ok &= check(clock.step(0.0, true) == 0, "explicit reset leaves no debt");

    if (ok) std::puts("p2_bombsarai_clock_test PASS");
    return ok ? 0 : 1;
}
