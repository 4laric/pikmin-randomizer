#include "pc_p2_elecbug_fx.h"
#include "pc_p2_attack_fx.h"
#include <cassert>
#include <cstdio>
using namespace p2elecbugfx;
int main() {
    // Effects live exactly over the charge/discharge states; every other state fades them.
    for (int s = 0; s <= 9; ++s) assert(effectsLive(s) == (s == 4 || s == 5 || s == 6 || s == 7));
    // The arc is the generator only, from frame 8, and only while linked.
    assert(!arcLive(Discharge, true, 0.0f));
    assert(arcLive(Discharge, true, 8.0f / 30.0f));
    assert(!arcLive(Discharge, false, 1.0f));      // link lost -> arc gone
    assert(!arcLive(ChildDischarge, true, 1.0f));  // the child never draws thunder
    assert(!arcLive(9, true, 1.0f));               // return/recover: gone
    // Long links stay bounded; short ones still get one piece.
    assert(arcPieces(10.0f) == 1 && arcPieces(300.0f) == kMaxPieces && arcPieces(1000.0f) == kMaxPieces);
    assert(arcPieces(300.0f) * p2attackfx::MAX_ARC_POINTS * 2 <= 100);
    // Session lifecycle: begin on link, end on fade, nothing outstanding.
    p2attackfx::Session ses;
    assert(ses.begin(p2attackfx::Element::Elec));
    assert(ses.outstanding() == 1);
    assert(ses.end() && ses.outstanding() == 0);
    std::puts("p2_elecbug_fx_test PASS");
    return 0;
}
