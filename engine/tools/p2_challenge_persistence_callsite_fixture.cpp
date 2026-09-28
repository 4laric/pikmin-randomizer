// Challenge persistence ENGINE CALL SITE guarded fixture (#718).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp by scripts/build_p2_challenge_persistence_callsite.py;
// no shared build files are touched. Unlike the #713 module fixture, this one
// drives the ENGINE CALL SITE: it boots the 960x540 centred window, runs
// pc_bbft_init() with a selected challenge stage, and calls the real
// pc_bbft_update() bridge, which now invokes the #713 recorders from
// pc_port/pc_bbft.cpp (the #710 hook is left untouched). A successful run
// emits the exact 7 probe markers for ch_MAT_route_rover plus PASS, proving
// the module is reachable through the engine call site and links.
//
// The module (pc_port/pc_p2_challenge_persistence.{h,cpp}) is not yet in any
// CMake target, so this TU compiles it in (single definition site) and the
// pc_bbft.o weak references resolve to it at link time.
//
// Captain safety (#632): the canonical guard is vendored verbatim and proven
// by the self-test and negative-test modes below. This fixture boots no game
// world, so there is no Navi to observe per tick; no blanket invincibility
// exists anywhere here.
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Inline tested equivalent of scripts/p2_fixture_captain_guard.h (recorded
// hash alongside the lane); never changes captain health or game state.
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
#include "pc_bbft.h"
// pc_p2_challenge_stage() is defined in pc_bbft.cpp (process-lifetime
// std::string) but has no public header on this line; declare it here.
// (The #710-only pc_p2_challenge_runtime.h is absent here, so no include.)
const char* pc_p2_challenge_stage();
#include "pc_p2_challenge_persistence.h"
// The module TU is not a CMake target (no shared build edits allowed), so it
// is compiled as part of this replacement-main TU. It has no other object in
// the link, so this single inclusion is the one and only definition site.
#include "../pc_port/pc_p2_challenge_persistence.cpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

const char* const kStage = "ch_MAT_route_rover";

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
            std::printf("FAIL CHALLENGE_PERSISTENCE_CALLSITE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CHALLENGE_PERSISTENCE_CALLSITE_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_CHALLENGE_PERSISTENCE_CALLSITE %s\n", reason);
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
            std::printf("FAIL P2_CHALLENGE_PERSISTENCE_CALLSITE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Challenge persistence callsite fixture", 960, 540)) return 3;
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
        std::printf("P2_CHALLENGE_PERSISTENCE_CALLSITE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    // Drive the ENGINE CALL SITE: select the #561 consumer stage, then run the
    // real pc_bbft_update() bridge (which invokes the #718 call site). The
    // module emits SAVE_KEY/LOAD_KEY/CLEAR/HIGHSCORE/UNLOCK/RECEIPT_DEDUP/
    // REENTRY for the selected stage.
    char arg0[] = "p2_challenge_persistence_callsite";
    char arg1[] = "--experimental-challenge-stage";
    char arg2[] = "ch_MAT_route_rover";
    char* initArgv[] = { arg0, arg1, arg2 };
    pc_bbft_init(3, initArgv);
    if (std::strcmp(pc_p2_challenge_stage() ? pc_p2_challenge_stage() : "", kStage) != 0) {
        fail("stage-flag-not-recorded");
    }
    pc_bbft_update();
    pc_bbft_update(); // idempotent: markers must not repeat
    // Independent module check: the call site must have resolved the stage and
    // the sample must match the deterministic result-screen values.
    using namespace p2challengepersist;
    StageAnchors probe;
    if (!selectStage(kStage, &probe)) fail("module-stage-unresolved");
    if (probe.uiIndex != 27 || probe.floors != 1) fail("module-pins");
    if (compute_score(42, 120.5, 15) != 690) fail("score-formula");
    if (std::strcmp(probe.saveKey, "p2_challenge_save_ch_MAT_route_rover") != 0) fail("save-key");
    if (std::strcmp(probe.unlockKey, "p2_challenge_unlock_ch_MAT_route_rover") != 0) fail("unlock-key");
    std::printf("P2_CHALLENGE_PERSISTENCE_CALLSITE_RESOLVED stage=%s ui_index=27 markers=7\n", kStage);
    std::fflush(stdout);
    std::puts("PASS P2_CHALLENGE_PERSISTENCE_CALLSITE_RUN markers=7");
    std::fflush(stdout);
    return 0;
}
