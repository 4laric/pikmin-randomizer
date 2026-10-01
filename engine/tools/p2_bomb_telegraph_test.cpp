// Unit test for the Volatile Dweevil carried-bomb telegraph policy.
#include "pc_p2_bomb_telegraph.h"
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); std::exit(1); } } while (0)

using namespace p2bombtelegraph;

int main() {
    // Source constants.
    CHECK(kBombLife == 4.5f);
    CHECK(std::fabs(kTotalSeconds - 4.8333333f) < 1e-4f);
    CHECK(gaugeRatio(4.5f) == 1.0f);
    CHECK(gaugeRatio(2.25f) == 0.5f);
    CHECK(gaugeRatio(-1.0f) == 0.0f);
    CHECK(gaugeRatio(9.0f) == 1.0f);

    // Period speeds up monotonically as the gauge empties.
    CHECK(flashPeriod(1.0f) == kFlashSlowPeriod);
    CHECK(std::fabs(flashPeriod(0.0f) - kFlashFastPeriod) < 1e-6f);
    float prev = 10.0f;
    for (int i = 0; i <= 20; ++i) {
        const float p = flashPeriod(1.0f - i / 20.0f);
        CHECK(p <= prev + 1e-6f);
        prev = p;
    }

    // Not burning: nothing happens.
    Burn idle;
    Step none = idle.step(0.033f);
    CHECK(!none.pulse && !none.detonate && !none.lightOn);

    // Full burn at 30 fps: gauge drains, pulses accelerate, blast is last and
    // happens exactly once at 4.5 s + 10 frames.
    Burn burn;
    burn.ignite();
    CHECK(burn.burning && burn.ratio() == 1.0f);
    const float dt = 1.0f / 30.0f;
    float t = 0.0f, lastRatio = 1.0f;
    std::vector<float> pulseTimes;
    int detonations = 0, lights = 0;
    float detonateAt = -1.0f, lightAt = -1.0f;
    for (int i = 0; i < 400 && detonations == 0; ++i) {
        Step s = burn.step(dt);
        t += dt;
        CHECK(burn.ratio() <= lastRatio + 1e-6f);
        lastRatio = burn.ratio();
        if (s.pulse) pulseTimes.push_back(t);
        if (s.lightOn) { ++lights; lightAt = t; }
        if (s.detonate) { ++detonations; detonateAt = t; }
    }
    CHECK(detonations == 1);
    CHECK(lights == 1);
    CHECK(std::fabs(lightAt - 0.5f) < 0.05f);           // health < 4.0 after 0.5 s
    CHECK(std::fabs(detonateAt - kTotalSeconds) < 0.06f); // 4.5 s + 10 frames
    CHECK(burn.ratio() == 0.0f);
    CHECK(burn.detonated && !burn.burning);
    // No second blast and no more pulses after detonation.
    Step after = burn.step(dt);
    CHECK(!after.detonate && !after.pulse);
    burn.ignite();
    CHECK(!burn.burning); // cannot re-ignite a spent bomb

    // Pulse gaps shrink: the last gap is much shorter than the first.
    CHECK(pulseTimes.size() >= 12);
    const float firstGap = pulseTimes[1] - pulseTimes[0];
    const float lastGap = pulseTimes.back() - pulseTimes[pulseTimes.size() - 2];
    CHECK(firstGap > 0.35f);
    CHECK(lastGap < firstGap * 0.35f);
    CHECK(lastGap < 0.16f);

    // Frame-rate independent: 60 fps blasts at the same time within a frame.
    Burn b60;
    b60.ignite();
    float t60 = 0.0f, at60 = -1.0f;
    for (int i = 0; i < 1000 && at60 < 0.0f; ++i) {
        Step s = b60.step(1.0f / 60.0f);
        t60 += 1.0f / 60.0f;
        if (s.detonate) at60 = t60;
    }
    CHECK(std::fabs(at60 - detonateAt) < 0.06f);

    // Flash is lit half of each phase and only while burning.
    Burn f;
    CHECK(!f.flashOn());
    f.ignite();
    f.phase = 0.25f; CHECK(f.flashOn());
    f.phase = 0.75f; CHECK(!f.flashOn());

    // Tint: dim when off, bright when on, redder as the gauge empties.
    Tint off = flashTint(false, 1.0f);
    Tint on1 = flashTint(true, 1.0f);
    Tint on0 = flashTint(true, 0.0f);
    CHECK(off.r < on1.r && off.g < on1.g);
    CHECK(on0.g < on1.g && on0.b < on1.b);

    std::printf("p2_bomb_telegraph_test ok pulses=%zu first_gap=%.3f last_gap=%.3f blast=%.3f\n", pulseTimes.size(),
                firstGap, lastGap, detonateAt);
    return 0;
}
