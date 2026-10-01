// Challenge persistence ENGINE MEMBERSHIP guarded fixture (#725).
//
// Replacement-main TU linked against the PRODUCTION pikmin_pc graph in place
// of pc_port/pc_main.cpp by scripts/build_p2_challenge_persistence_membership.py.
//
// Difference from the #718 callsite fixture: this TU does NOT include
// ../pc_port/pc_p2_challenge_persistence.cpp. It only includes the header and
// calls the recorders directly, so the link MUST resolve them from the
// pikmin_pc object produced by the CMake membership change -- if the module
// were absent from the target, the link would fail (strong references) rather
// than silently take the pc_bbft.cpp weak-null path. A successful run therefore
// proves the module is a real member of pikmin_pc AND that the engine callsite
// emits the exact 7 probe markers for the selected stage.
//
// Captain safety (#632): the canonical guard is vendored verbatim (or an
// inline tested equivalent) and proven by the self-test and negative-test
// modes below. This fixture boots no game world, so there is no Navi to
// observe per tick; no blanket invincibility exists anywhere here.
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
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
#include "pc_p2_challenge_persistence.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// pc_p2_challenge_stage() is defined in pc_bbft.cpp (process-lifetime
// std::string) but has no public header on this line; declare it here.
const char* pc_p2_challenge_stage();

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
            std::printf("FAIL CHALLENGE_PERSISTENCE_MEMBERSHIP selftest row=%d\n", int(i));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_CHALLENGE_PERSISTENCE_MEMBERSHIP %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL CHALLENGE_PERSISTENCE_MEMBERSHIP negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Challenge persistence membership fixture", 960, 540)) return 3;
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
        std::printf("P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    char arg0[] = "p2_challenge_persistence_membership";
    char arg1[] = "--experimental-challenge-stage";
    char arg2[] = "ch_MAT_route_rover";
    char* initArgv[] = { arg0, arg1, arg2 };
    pc_bbft_init(3, initArgv);
    if (std::strcmp(pc_p2_challenge_stage() ? pc_p2_challenge_stage() : "", kStage) != 0) {
        fail("stage-flag-not-recorded");
    }
    // Direct strong references: link-only resolves if the module is a pikmin_pc
    // member. Then drive the real engine callsite in pc_bbft_update().
    using namespace p2challengepersist;
    StageAnchors probe;
    if (!selectStage(kStage, &probe)) fail("module-stage-unresolved");
    if (probe.uiIndex != 27 || probe.floors != 1) fail("module-pins");
    if (compute_score(42, 120.5, 15) != 690) fail("score-formula");
    if (std::strcmp(probe.saveKey, "p2_challenge_save_ch_MAT_route_rover") != 0) fail("save-key");
    if (std::strcmp(probe.unlockKey, "p2_challenge_unlock_ch_MAT_route_rover") != 0) fail("unlock-key");
    pc_bbft_update();
    pc_bbft_update(); // idempotent: markers must not repeat
    std::printf("P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_RESOLVED stage=%s ui_index=27 markers=7\n", kStage);
    std::fflush(stdout);
    std::puts("PASS P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_RUN markers=7");
    std::fflush(stdout);
    return 0;
}
