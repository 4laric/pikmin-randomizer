// #972: corpse origin sanity (pc_port/pc_corpse_origin.h).
#include "pc_corpse_origin.h"
#include <cassert>
#include <cmath>
#include <cstdio>
using namespace pc_corpse_origin;
int main() {
    // Breadbug case: 'carc' never written (0,0,0) while the body stands at (-329,-37,2000).
    assert(!carcassUsable(0, 0, 0, -329.3f, -37.7f, 2000.2f, 20.0f));
    // A written centre inside the body is kept (vanilla placement unchanged).
    assert(carcassUsable(-325.0f, -20.0f, 2004.0f, -329.3f, -37.7f, 2000.2f, 20.0f));
    // Stale centre from a previous life of a pooled teki, far away.
    assert(!carcassUsable(500.0f, 0.0f, -800.0f, -329.3f, -37.7f, 2000.2f, 20.0f));
    // Big bodies get a proportionally larger allowance (Giant Breadbug scale).
    assert(limit(20.0f) == kMinSlack);
    assert(limit(100.0f) == 400.0f);
    assert(carcassUsable(300.0f, 0, 0, 0, 0, 0, 100.0f));
    assert(!carcassUsable(300.0f, 0, 0, 0, 0, 0, 20.0f));
    // Near the world origin a zero centre is simply the right place.
    assert(carcassUsable(0, 0, 0, 10.0f, 5.0f, -10.0f, 20.0f));
    // NaN never used.
    assert(!carcassUsable(std::nanf(""), 0, 0, 0, 0, 0, 20.0f));
    assert(carcassUsable(0, 0, 0, 0, 0, 0, std::nanf("")));  // NaN size -> min slack
    std::puts("pc_corpse_origin_test OK");
    return 0;
}
