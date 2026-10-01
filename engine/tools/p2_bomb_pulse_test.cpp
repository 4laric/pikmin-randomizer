// Engine-free checks for p2bombtelegraph::Pulse (#1066, Dirigibug lit bomb).
#include "pc_p2_bomb_telegraph.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); std::exit(1); } } while (0)

using namespace p2bombtelegraph;

// Pulses in `seconds` at a fixed ratio, stepped at 60 Hz.
static int pulsesOver(float seconds, float ratio) {
    Pulse p;
    for (int i = 0; i < int(seconds * 60.0f + 0.5f); ++i) p.step(1.0f / 60.0f, ratio);
    return p.pulses;
}

int main() {
    Pulse p;
    CHECK(!p.on() && p.pulses == 0);
    CHECK(p.step(1.0f / 60.0f, 1.0f));  // first step starts a flash
    CHECK(p.on());
    CHECK(!p.step(0.0f, 1.0f) && !p.step(-1.0f, 1.0f) && p.pulses == 1);
    // Lit for the first half of each period, dark for the second.
    Pulse h;
    h.step(0.01f, 1.0f);
    for (int i = 0; i < 20; ++i) h.step(0.01f, 1.0f);  // 0.21 s of a 0.5 s period
    CHECK(h.on());
    for (int i = 0; i < 10; ++i) h.step(0.01f, 1.0f);  // 0.31 s
    CHECK(!h.on());
    // Faster near the blast: an empty gauge pulses several times as often as a full one.
    const int slow = pulsesOver(1.0f, 1.0f), fast = pulsesOver(1.0f, 0.0f);
    CHECK(slow >= 2 && slow <= 3);
    CHECK(fast >= 13 && fast <= 16);
    // Same ramp as Burn: the period at a ratio is flashPeriod(ratio).
    Pulse q;
    q.step(0.0001f, 0.5f);
    const float period = flashPeriod(0.5f);
    int n = 0;
    float t = 0.0f;
    while (n < 2 && t < 5.0f) { t += 0.001f; if (q.step(0.001f, 0.5f)) ++n; }
    CHECK(std::fabs(t - 2.0f * period) < 0.01f);
    // reset
    q.reset();
    CHECK(q.pulses == 0 && !q.on());
    std::printf("p2_bomb_pulse_test: ok\n");
    return 0;
}
