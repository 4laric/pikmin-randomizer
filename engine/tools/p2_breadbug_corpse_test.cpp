// Engine-free test of the #972 Breadbug presentation policy.
#include "pc_p2_breadbug_corpse.h"
#include "pc_p2_breadbug_fsm.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
namespace bb = p2breadbugfsm;
int main() {
    using namespace p2breadbugcorpse;
    assert(clampFrame(-3.f, 39) == 0.f);
    assert(clampFrame(std::numeric_limits<float>::quiet_NaN(), 39) == 0.f);
    assert(clampFrame(1e9f, 39) == 38.f);
    assert(clampFrame(12.5f, 39) == 12.5f);
    assert(clampFrame(5.f, 1) == 0.f);
    // The carried-corpse clock loops the type5 key range (10..29) and never leaves the clip.
    bb::Clip carry;
    carry.name = "type5"; carry.frames = 39; carry.staged = true;
    carry.events = {{10, bb::KeyLoopStart}, {29, bb::KeyLoopEnd}};
    bb::Animator a;
    a.start(&carry, bb::AnimCarry);
    a.setFrame(kHoldFrame);
    assert(std::fabs(a.frame() - 10.f) < 1e-4f);
    float lo = 1e9f, hi = -1e9f;
    for (int i = 0; i < 2000; ++i) {
        a.animate(1.f / 60.f);
        lo = std::fmin(lo, a.frame()); hi = std::fmax(hi, a.frame());
    }
    assert(lo >= 10.f - 1e-3f && hi < 31.f);
    assert(hi > 25.f);  // it really plays the loop, not a frozen pose
    std::puts("p2_breadbug_corpse_test ok");
    return 0;
}
