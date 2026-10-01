// #1022: Breadbug lair presentation policy (pc_port/pc_p2_breadbug_nest.h).
#include "pc_p2_breadbug_nest.h"
#include <cassert>
#include <cmath>
#include <cstdio>
using namespace p2breadbugnest;
int main() {
    assert(visible(true, false, 0, true));
    assert(!visible(false, false, 0, true));   // unbound
    assert(!visible(true, true, 0, true));     // death funnel ran (killNest)
    assert(!visible(true, false, 1, true));    // dying
    assert(!visible(true, false, 2, true));    // carcass
    assert(!visible(true, false, 0, false));   // no staged model (pre-#1022 content)
    assert(scale(1.0f) == 1.0f && scale(2.0f) == 2.0f);  // retail PanModoki / OoPanModoki
    assert(scale(0.0f) == 1.0f && scale(-1.0f) == 1.0f && scale(std::nanf("")) == 1.0f);
    assert(scale(9.0f) == 5.0f);
    std::puts("p2_breadbug_nest_test OK");
    return 0;
}
