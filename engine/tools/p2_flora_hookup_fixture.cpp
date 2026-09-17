// Flora hookup guarded fixture (#723, issue #723).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp by scripts/build_p2_flora_hookup.py; no shared build
// files are touched. It proves the engine hookup bridge fires: the ported
// #697 converter plus the new pc_p2_flora_hookup bridge link into the engine
// graph, run the conversion/scenery suites plus a fixed live-facts bridge
// session, and emit the hook markers plus PASS. No engine world is booted and
// no save tree is written: this proves module + bridge linkage and firing,
// not gameplay. The shared-engine per-tick call (pc_bbft.cpp) and CMake
// membership are a serialized follow-on owned by #722; specified, not edited.
//
// Captain safety (#632): the canonical guard runs in the engine-independent
// self-test and negative-test modes below. This fixture boots no game world,
// so there is no Navi to observe per tick; the guard is vendored verbatim,
// proven by those two modes, and its hashes are recorded. No blanket
// invincibility exists anywhere here.
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Inline tested equivalent of scripts/p2_fixture_captain_guard.h (recorded
// hash alongside the lane); never changes captain health or game state. A
// replacement-main TU cannot include a Python-tree script header at native
// build time, so the exact guard body is vendored here.
#include <cmath>
#include <cstdio>
#include <cstdlib>
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}
#endif
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_flora_hookup.h"
// Neither the converter nor the bridge has a CMake target (no shared build
// edits allowed), so both TUs are compiled as part of this replacement-main
// TU. They have no other object in the link, so this single inclusion is the
// one and only definition site for each.
#include "../pc_port/pc_p2_flora_convert.cpp"
#include "../pc_port/pc_p2_flora_hookup.cpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

int guardSelfTest() {
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.5f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {false, true, 100.0f, true},
        {true, false, 100.0f, true},
        {true, true, 0.0f, true},
    };
    for (size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        const bool down = p2_fixture_captain_down(rows[i].orima, rows[i].dead, rows[i].hp);
        if (down != rows[i].expectDown) {
            std::printf("FAIL FLORA_HOOKUP selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_FLORA_HOOKUP_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_FLORA_HOOKUP %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

} // namespace

// Declared by the ported converter TU; linked here through the inclusion.
int p2_flora_convert_suite();
int p2_flora_scenery_suite();

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            // Exercise the exact interruption call: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_FLORA_HOOKUP negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Flora hookup fixture", 960, 540)) return 3;
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0};
        SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_FLORA_HOOKUP_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    int failures = 0;
    failures += p2_flora_convert_suite();
    failures += p2_flora_scenery_suite();
    failures += p2florahookup::p2_flora_hookup_suite();
    if (failures != 0) fail("suite-failures");
    std::puts("PASS P2_FLORA_HOOKUP_RUN suites=3");
    std::fflush(stdout);
    return 0;
}
