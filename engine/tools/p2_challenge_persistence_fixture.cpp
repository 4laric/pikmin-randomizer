// Challenge persistence guarded fixture (#713, consumer-repair for #561).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp by scripts/build_p2_challenge_persistence.py; no shared
// build files are touched. It drives the owned anchors/score/markers module
// (pc_port/pc_p2_challenge_persistence.{h,cpp}) through one full probe-order
// stage session for ch_MAT_route_rover (the #561 consumer stage, ui 27) and
// emits the exact 7 probe markers plus PASS. No engine world is booted and no
// save tree is written: this proves the module + marker contract, not
// gameplay. The engine call-site follow-on is specified in
// docs/PIKMIN2_CHALLENGE_PERSISTENCE_HOOKUP.md (blocked on #710 + #186).
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
#include "pc_p2_challenge_persistence.h"
// The module TU is not a CMake target (no shared build edits allowed), so it
// is compiled as part of this replacement-main TU. pc_p2_challenge_persistence
// has no other object in the link, so this single inclusion is the one and
// only definition site.
#include "../pc_port/pc_p2_challenge_persistence.cpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

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
            std::printf("FAIL CHALLENGE_PERSISTENCE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CHALLENGE_PERSISTENCE_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_CHALLENGE_PERSISTENCE %s\n", reason);
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
            // Engine-independent; the exit code is the assertion.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_CHALLENGE_PERSISTENCE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    // Any other argv (e.g. --experimental-pikmin2-room from shared runners) is
    // accepted and ignored: this data-module fixture boots no engine world.
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Challenge persistence fixture", 960, 540)) return 3;
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
        std::printf("P2_CHALLENGE_PERSISTENCE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    using namespace p2challengepersist;
    // Fail-closed refusal paths first: unknown/empty stage keys must refuse
    // with no markers and no state change.
    {
        StageAnchors probe;
        std::memset(&probe, 0, sizeof(probe));
        if (selectStage("ch_NOPE_missing", &probe)) fail("unknown-stage-accepted");
        if (selectStage("", &probe)) fail("empty-stage-accepted");
        if (selectStage(nullptr, &probe)) fail("null-stage-accepted");
        if (selectStage("ch_MAT_route_rover", nullptr)) fail("null-out-accepted");
        if (compute_score(-1, 120.5, 15) != -1) fail("negative-score-accepted");
    }
    // Full probe-order session for the #561 consumer stage.
    StageAnchors anchors;
    if (!selectStage("ch_MAT_route_rover", &anchors)) fail("route-rover-select");
    if (anchors.uiIndex != 27 || anchors.floors != 1) fail("route-rover-pins");
    if (std::strcmp(anchors.saveKey, "p2_challenge_save_ch_MAT_route_rover") != 0) fail("save-key");
    if (std::strcmp(anchors.loadKey, "p2_challenge_load_ch_MAT_route_rover") != 0) fail("load-key");
    if (std::strcmp(anchors.clearKey, "p2_challenge_clear_ch_MAT_route_rover") != 0) fail("clear-key");
    if (std::strcmp(anchors.highKey, "p2_challenge_highscore_ch_MAT_route_rover") != 0) fail("high-key");
    if (std::strcmp(anchors.unlockKey, "p2_challenge_unlock_ch_MAT_route_rover") != 0) fail("unlock-key");
    // Probe order: save, load, clear, highscore, unlock, receipt, reentry.
    if (!recordSave(&anchors)) fail("save-record");
    if (!recordLoad(&anchors)) fail("load-record");
    if (!recordClear(&anchors)) fail("clear-record");
    // Deterministic result-screen sample: 42 pokos, 120.5 s left, 15 population.
    if (!recordHighscore(&anchors, 42, 120.5, 15)) fail("highscore-record");
    if (anchors.highscore != 690) fail("highscore-value");
    if (!recordUnlock(&anchors)) fail("unlock-record");
    if (!recordReceipt(&anchors, 1)) fail("receipt-record");
    if (!recordReceipt(&anchors, 1)) fail("receipt-dedup-record");
    if (!recordReentry(&anchors)) fail("reentry-record");
    if (!anchors.saveSeen || !anchors.loadSeen || !anchors.cleared || !anchors.unlocked ||
        !anchors.reentered) fail("anchor-state");
    if (anchors.receiptCount != 1 || anchors.dedupHits != 1 || anchors.lastReceiptId != 1) {
        fail("receipt-state");
    }
    std::printf("P2_CHALLENGE_PERSISTENCE_RESOLVED stage=ch_MAT_route_rover ui_index=27 markers=7\n");
    std::fflush(stdout);
    std::puts("PASS P2_CHALLENGE_PERSISTENCE_RUN markers=7");
    std::fflush(stdout);
    return 0;
}
