// Engine-free contract for pc_p2_tamago_policy.h (Mitite group/scare policy).
#include "pc_p2_tamago_policy.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>

int main()
{
    using namespace p2tamagopolicy;
    // One placement is a leader plus nine fellows.
    assert(GroupCount == 10 && fellowCount(GroupCount) == 9);
    assert(EggGroupCount == 10 && BigFootGroupCount == 30);
    assert(fellowCount(1) == 0 && fellowCount(0) == 0);
    // Pool guard mirrors Mgr::createGroup's getFreeNum() < count refusal.
    assert(poolHoldsGroup(10, 10) && !poolHoldsGroup(9, 10));
    // Found only inside the retail 120 appearance radius.
    assert(withinAppearRange(119.0f) && !withinAppearRange(121.0f));
    assert(isFound(true, false) && isFound(false, true) && !isFound(false, false));
    // Survival window 144..180 ticks = 4.8..6.0 s of walking.
    assert(std::fabs(activeMaxTicks(0.0f) - 144.0f) < 1e-3f);
    assert(std::fabs(activeMaxTicks(1.0f) - 180.0f) < 1e-3f);
    assert(!shouldHide(143.0f, activeMaxTicks(0.0f)) && shouldHide(145.0f, activeMaxTicks(0.0f)));
    // Random windows: walk 25..80 ticks, appear delay 20..90 ticks, at 30 ticks/s.
    assert(std::fabs(walkSeconds(0.0f) - 25.0f / 30.0f) < 1e-4f);
    assert(std::fabs(walkSeconds(1.0f) - 80.0f / 30.0f) < 1e-4f);
    assert(std::fabs(appearDelaySeconds(0.0f) - 20.0f / 30.0f) < 1e-4f);
    assert(std::fabs(appearDelaySeconds(1.0f) - 90.0f / 30.0f) < 1e-4f);
    // Fellow ring: radius 0.2..1.0 of 45 units; every second fellow faces flipped.
    for (int i = 0; i < 9; ++i) {
        for (float r : {0.0f, 0.5f, 1.0f}) {
            const Offset o = fellowOffset(i, GroupCount, r);
            const float d = std::sqrt(o.x * o.x + o.z * o.z);
            assert(d >= 0.2f * GroundSpread - 1e-3f && d <= GroundSpread + 1e-3f);
        }
    }
    assert(fellowOffset(1, GroupCount, 0.5f).faceDir < 0.0f);
    assert(fellowOffset(2, GroupCount, 0.5f).faceDir > 0.0f);
    // Astonish scares the receivable, skips Purple and the untransittable states.
    assert(astonishAccepts(true, false, 0));   // normal
    assert(astonishAccepts(true, false, 22));  // flicked
    assert(!astonishAccepts(true, true, 0));   // purple
    assert(!astonishAccepts(false, false, 0)); // dead body
    assert(!astonishAccepts(true, false, StPanic));
    assert(!astonishAccepts(true, false, StFlying));
    assert(!astonishAccepts(true, false, StDying));
    assert(!astonishAccepts(true, false, StSwallowed));
    assert(!astonishAccepts(true, false, StNukareWait)); // sprout
    // The scare is short (Pikmin panic time), not the 30 s constructor argument.
    assert(PikminPanicSeconds > 0.0f && PikminPanicSeconds < 10.0f);
    // Panic burst radius and the harm rule.
    assert(PanicRadius == 150.0f);
    const PikminEffect e = pikminEffect();
    assert(!e.damages && e.scares);
    std::puts("p2_tamago_policy_test ok");
    return 0;
}
