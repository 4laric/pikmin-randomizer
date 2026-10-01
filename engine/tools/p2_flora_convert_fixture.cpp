// Native M1/M2 flora conversion + scenery guarded fixture (#697).
//
// Game-linked observation fixture: runs the conversion (M1) and scenery
// registration (M2) suites from pc_p2_flora_convert.cpp and emits observed
// P2_FLORA_CONVERT_* / P2_FLORA_SCENERY_* markers. Captain safety #632 is
// mandatory: the guard runs before any observation and exits 86 (BLOCKED)
// on captain-down, so a dead captain can never be recorded as a conversion.
//
// Modes: `live` (default) runs both suites; `negcap` forces captain-down to
// prove the negative path.
//
// 960x540 centred startup is inherited from the production room entrypoint;
// this fixture does not re-implement window setup. Arrival/receiver wiring
// and visual binding are #186-reviewed engine seams and stay unobserved
// (UNTESTED); no shared files are touched.
//
// NOTE: registering this fixture in CMake/CTest touches shared build files
// and therefore requires #186 review (see the lane packet). It is built
// privately via the replacement-main builder instead.
#include <cstdio>
#include <cstring>

#include "p2_fixture_captain_guard.h"
#include "pc_p2_flora_convert.h"
#include "pc_p2_flora_convert.cpp"

int p2_flora_convert_suite();
int p2_flora_scenery_suite();

int main(int argc, char** argv)
{
    const bool negative = argc > 1 && std::strcmp(argv[1], "negcap") == 0;
    // Guard BEFORE any observation: orimaDead/NaviDead/HP<=1 -> exit 86.
    p2_fixture_require_captain(negative, false, negative ? 0.0f : 100.0f, 0);
    std::printf("P2_FLORA_BOOT mode=%s\n", negative ? "negcap" : "live");
    std::fflush(stdout);
    int failures = 0;
    failures += p2_flora_convert_suite();
    failures += p2_flora_scenery_suite();
    if (failures) {
        std::printf("P2_FLORA_ERROR failures=%d\n", failures);
        return 2;
    }
    std::printf("P2_FLORA_DONE convert=pass scenery=pass\n");
    std::fflush(stdout);
    return 0;
}
