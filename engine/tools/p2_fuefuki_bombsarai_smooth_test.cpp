// Engine-free checks for pc_p2_fb_smooth.h and the pose-bank pieces the
// Antenna Beetle / Dirigibug smoothing relies on (#972).
#include "pc_p2_fb_smooth.h"

#include <cmath>
#include <cstdio>
#include <vector>

static int failures = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); ++failures; } } while (0)

static bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }

int main() {
    using namespace p2fbsmooth;
    // bankDuration: full span kept, dropped tail shortened, dropped head untouched.
    CHECK(bankDuration({0, 5, 9, 104}, 105) == 105);
    CHECK(bankDuration({0, 5, 9, 99}, 105) == 100);
    CHECK(bankDuration({3, 5, 9, 104}, 105) == 105);
    CHECK(bankDuration({}, 40) == 40);
    // carryLoopFrame: loops 10..29 at 30 frames per second.
    CHECK(near(carryLoopFrame(0.0f, 10, 29), 10.0f));
    CHECK(near(carryLoopFrame(1.0f / 30.0f, 10, 29), 11.0f));
    CHECK(near(carryLoopFrame(19.0f / 30.0f, 10, 29), 10.0f));  // wraps at LOOP_END
    for (int i = 0; i < 400; ++i) {
        const float f = carryLoopFrame(float(i) * 0.0173f, 10, 29);
        CHECK(f >= 10.0f && f < 29.0f);
    }
    CHECK(near(carryLoopFrame(-1.0f, 10, 29), 10.0f));
    CHECK(near(carryLoopFrame(NAN, 10, 29), 10.0f));
    CHECK(near(carryLoopFrame(1.0f, 10, 10), 10.0f));
    // bombLoopFrame: 4 render frames per source frame, wraps at the clip length.
    CHECK(near(bombLoopFrame(0, 8), 0.0f));
    CHECK(near(bombLoopFrame(6, 8), 1.5f));
    CHECK(near(bombLoopFrame(32, 8), 0.0f));
    CHECK(near(bombLoopFrame(5, 0), 0.0f));
    // fadeStep.
    CHECK(near(fadeStep(0.016f), 0.016f));
    CHECK(fadeStep(-1.0f) == 0.0f);
    CHECK(fadeStep(2.0f) == 0.0f);
    CHECK(fadeStep(NAN) == 0.0f);
    if (failures) { std::printf("p2_fuefuki_bombsarai_smooth_test: %d failures\n", failures); return 1; }
    std::printf("p2_fuefuki_bombsarai_smooth_test: ok\n");
    return 0;
}
