#include "pc_p2_bombsarai_hover.h"

// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <limits>

namespace {
constexpr float kDelta = P2BombSaraiHover::kSourceDelta;

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

struct Map {
    float groundY = 0.0f;
    bool fail = false;
};
float getMinY(void* opaque, float, float)
{
    Map& map = *static_cast<Map*>(opaque);
    return map.fail ? std::numeric_limits<float>::quiet_NaN() : map.groundY;
}
}

int main()
{
    const P2BombSaraiHoverParms parms; // fp01 90, fp10 2.5, fp11 20, fp21 1.5, fp22 1.0

    // Rise toward minY + 90 from below: positive velocity proportional to
    // the gap, no pitch oscillation below the oscillation band.
    {
        Map map;
        P2BombSaraiHover hover;
        hover.reset(parms);
        float vy = 0.0f, height = 0.0f;
        assert(hover.update(false, 0, { 0, 40, 0 }, kDelta, getMinY, &map, vy, height));
        assert(near(height, 40.0f));
        assert(near(vy, 1.5f * (90.0f - 40.0f))); // free rise factor 1.5
        assert(near(hover.pitchRatio(), 0.0f));   // below 90-20: no pitch yet
    }

    // Convergence: velocity sign flips above the target band, so repeated
    // updates settle near minY + flightHeight modulo the pitch oscillation.
    {
        Map map;
        P2BombSaraiHover hover;
        hover.reset(parms);
        float y = 10.0f;
        for (int i = 0; i < 600; ++i) {
            float vy = 0.0f, height = 0.0f;
            assert(hover.update(false, 0, { 0, y, 0 }, kDelta, getMinY, &map, vy, height));
            y += vy * kDelta;
        }
        assert(near(y, 90.0f, 25.0f)); // within one pitch amplitude of fp01
        assert(y > 60.0f);
    }

    // Weight degradation: 5 stuck Pikmin select the laden rise factor 1.0;
    // the blend is linear over the clamped count (BombSarai.cpp:205-212).
    {
        Map map;
        P2BombSaraiHover hover;
        hover.reset(parms);
        float vyFree = 0.0f, vyLaden = 0.0f, vyHalf = 0.0f, height = 0.0f;
        assert(hover.update(false, 0, { 0, 40, 0 }, kDelta, getMinY, &map, vyFree, height));
        assert(hover.update(false, 5, { 0, 40, 0 }, kDelta, getMinY, &map, vyLaden, height));
        assert(near(vyLaden, 1.0f * (90.0f - 40.0f)));
        assert(vyLaden < vyFree);
        hover.reset(parms);
        // 2 stuck: (5-2)/5*1.5 + 2/5*1.0 = 1.3
        assert(hover.update(false, 2, { 0, 40, 0 }, kDelta, getMinY, &map, vyHalf, height));
        assert(near(vyHalf, 1.3f * (90.0f - 40.0f)));
        // Clamping: negative counts act as 0, above-5 as 5.
        float vyClampLow = 0.0f, vyClampHigh = 0.0f;
        hover.reset(parms);
        assert(hover.update(false, -3, { 0, 40, 0 }, kDelta, getMinY, &map, vyClampLow, height));
        assert(near(vyClampLow, vyFree));
        hover.reset(parms);
        assert(hover.update(false, 99, { 0, 40, 0 }, kDelta, getMinY, &map, vyClampHigh, height));
        assert(near(vyClampHigh, vyLaden));
    }

    // Fast takeoff forces rise factor 6.0 regardless of stuck Pikmin
    // (TakeOff2 path, BombSarai.cpp:205).
    {
        Map map;
        P2BombSaraiHover hover;
        hover.reset(parms);
        float vy = 0.0f, height = 0.0f;
        assert(hover.update(true, 5, { 0, 40, 0 }, kDelta, getMinY, &map, vy, height));
        assert(near(vy, 6.0f * (90.0f - 40.0f)));
    }

    // Pitch oscillation engages only inside the band and wraps at TAU
    // (addPitchRatio, BombSarai.cpp:251-257).
    {
        Map map;
        P2BombSaraiHover hover;
        hover.reset(parms);
        float vy = 0.0f, height = 0.0f;
        // At height 80 (> 90-20): pitch advances by 2.5 * 1/30 per tick.
        assert(hover.update(false, 0, { 0, 80, 0 }, kDelta, getMinY, &map, vy, height));
        assert(near(hover.pitchRatio(), 2.5f * kDelta));
        // newHeight = 90 + 20*sin(ratio) -> vy = 1.5 * (90 + 20*sin(r) - 80)
        assert(near(vy, 1.5f * (90.0f + 20.0f * std::sin(2.5f * kDelta) - 80.0f)));
        // Run past TAU (2.5/s needs ~2.52 s = 76 ticks) and confirm wrapping.
        for (int i = 0; i < 200; ++i) {
            assert(hover.update(false, 0, { 0, 80, 0 }, kDelta, getMinY, &map, vy, height));
        }
        assert(hover.pitchRatio() >= 0.0f && hover.pitchRatio() <= 6.28319f);
    }

    // Validation: failed terrain sample, wrong delta, non-finite position.
    {
        Map map;
        P2BombSaraiHover hover;
        hover.reset(parms);
        float vy = 0.0f, height = 0.0f;
        map.fail = true;
        assert(!hover.update(false, 0, { 0, 40, 0 }, kDelta, getMinY, &map, vy, height));
        map.fail = false;
        assert(!hover.update(false, 0, { 0, 40, 0 }, 1.0f / 60.0f, getMinY, &map, vy, height));
        assert(!hover.update(false, 0, { 0, std::numeric_limits<float>::quiet_NaN(), 0 },
                             kDelta, getMinY, &map, vy, height));
        assert(!hover.update(false, 0, { 0, 40, 0 }, kDelta, nullptr, nullptr, vy, height));
    }

    return 0;
}
