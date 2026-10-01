#include "pc_p2_captive_navi_policy.h"
#include <cassert>
#include <cstdio>

int main()
{
    using namespace p2captivenavi;
    // A released (captain-less) Pikmin asked to rejoin a party goes free.
    assert(modeFor(kFormationMode, false) == kFreeMode);
    // With a captain nothing changes, for every mode.
    for (int mode = 0; mode < 16; ++mode) assert(modeFor(mode, true) == mode);
    // Other modes are never rewritten, captain or not.
    for (int mode = 0; mode < 16; ++mode)
        if (mode != kFormationMode) assert(modeFor(mode, false) == mode);
    assert(!keepThrowPick(false) && keepThrowPick(true));
    assert(!mayHang(false) && mayHang(true));
    std::puts("p2_captive_navi_policy_test ok");
    return 0;
}
