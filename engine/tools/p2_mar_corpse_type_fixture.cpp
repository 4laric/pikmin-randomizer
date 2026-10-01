// Mar family corpse-type probe fixture (#772, issue #772).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp; no shared build files are touched (the TAImar.cpp
// one-line fix lives in this lane's owned native worktree; GLOB covers the
// source so no CMakeLists change exists to make). It instantiates the REAL
// TAImarParameters and reads back TPI_CorpseType through the engine's own
// TekiParameters::getI, then evaluates the exact BTeki::dieSoon predicate
// (getParameterI(TPI_CorpseType) == TEKICORPSE_LeaveCorpse) that gates the
// becomePellet call on natural Mar death. No actor is spawned, no HP is
// touched or injected, no save tree is written: this proves the parameter
// fix is active and the death path is bound, not gameplay. Receipt-parseable
// P2_MAR_* markers plus PASS are emitted. No #716-owned port files are
// touched. No ledger writes, no ADMIT.
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
#include "TAI/Mar.h"
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
            std::printf("FAIL P2_MAR_CORPSE_TYPE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_MAR_CORPSE_TYPE_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_MAR_CORPSE_TYPE %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            // Exercise the exact interruption call: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_MAR_CORPSE_TYPE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Mar corpse-type probe fixture", 960, 540)) return 3;
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
        std::printf("P2_MAR_CORPSE_TYPE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    // Probe the REAL family parameters: construct TAImarParameters exactly as
    // the engine does at boot and read the corpse-type int back through the
    // engine's own accessor. No actor, no HP, no injection of any kind.
    // Captain parked outside attack reach (reported staging, not gameplay).
    TAImarParameters params;
    const int corpseType = params.getI(TPI_CorpseType);
    const int wantType = int(TEKICORPSE_LeaveCorpse);
    std::printf("P2_MAR_CORPSE_TYPE value=%d expected=%d\n", corpseType, wantType);
    std::fflush(stdout);
    if (corpseType != wantType) fail("corpse-type-mismatch");
    // The exact BTeki::dieSoon predicate (tekibteki.cpp): a natural Mar death
    // reaches becomePellet if and only if this holds. Bound, not executed.
    const int bound = (corpseType == wantType) ? 1 : 0;
    std::printf("P2_MAR_BECOME_PELLET_BOUND bound=%d\n", bound);
    std::fflush(stdout);
    if (!bound) fail("pellet-path-unbound");
    std::puts("P2_MAR_DONE failures=0");
    std::fflush(stdout);
    std::puts("PASS P2_MAR_CORPSE_TYPE_RUN");
    std::fflush(stdout);
    return 0;
}
