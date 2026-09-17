// Challenge 03toy stage-table guarded fixture (lane toy-stage-table-row-native, #752).
//
// Standalone TU: compiles pc_port/pc_p2_challenge_toy_stage.cpp in as its
// single definition site (the row is NOT a member of any CMake target; the
// pc_bbft.cpp/CMakeLists integration is a specified follow-on blocked on the
// #710/#736 line and is NOT implemented here). No shared build files touched.
//
// Proves the pinned ch_NARI_03toy row resolves with exact pins and emits its
// markers, and that unknown keys are refused fail-closed. Boots the 960x540
// centred window like the other guarded fixtures. All six gameplay gates stay
// UNTESTED; content wiring is the downstream #746 consumer's job. No PASS is
// emitted without observed evidence.
//
// Captain safety (#632): the canonical guard is vendored verbatim and proven
// by the self-test and negative-test modes below. This fixture boots no game
// world, so there is no Navi to observe per tick; no blanket invincibility
// exists anywhere here.
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
#include "pc_p2_challenge_toy_stage.h"
// The row TU is not a CMake target (serialized integration), so it is
// compiled as part of this TU. It has no other object in any link, so this
// single inclusion is the one and only definition site.
#include "../pc_port/pc_p2_challenge_toy_stage.cpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

const char* const kStage = "ch_NARI_03toy";
const char* const kSha = "d74b49ac3d9a2388288b9cb868dd8717ff893fd522453b309740519be841f03c";

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
            std::printf("FAIL TOY_STAGE_TABLE selftest row=%d\n", int(i));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_TOY_STAGE_TABLE_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_TOY_STAGE_TABLE %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL TOY_STAGE_TABLE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
        if (!std::strcmp(argv[i], "--unknown-test")) {
            // Fail-closed proof: an unknown stage key must be refused with no marker.
            const p2toystage::ToyStageRow* row = nullptr;
            if (p2toystage::lookupStage("ch_NARI_99bogus", &row)) {
                fail("unknown-accepted");
            }
            std::printf("P2_TOY_STAGE_UNKNOWN_REFUSED key=ch_NARI_99bogus\n");
            std::fflush(stdout);
            return 0;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Challenge 03toy stage table fixture", 960, 540)) return 3;
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
        std::printf("P2_TOY_STAGE_TABLE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    // Resolve the pinned row and verify every pin before emitting markers.
    const p2toystage::ToyStageRow* row = nullptr;
    if (!p2toystage::lookupStage(kStage, &row)) fail("stage-unresolved");
    if (row->uiIndex != 5 || row->tableOrder != 2 || row->floors != 2) fail("row-pins");
    if (row->floorSeconds[0] != 100.0f || row->floorSeconds[1] != 150.0f) fail("row-timers");
    if (row->roster[2][2] != 100) fail("row-roster");
    if (row->bitterSprays != 2 || row->spicySprays != 2) fail("row-sprays");
    if (std::strcmp(row->cavePath, "user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt") != 0) fail("row-path");
    if (std::strcmp(row->sourceSha256, kSha) != 0) fail("row-sha");
    if (p2toystage::rowCount() != 1) fail("row-count");
    p2toystage::emitResolved(row);
    std::printf("P2_TOY_STAGE_TABLE_GATES all=UNTESTED content_wired=0\n");
    std::fflush(stdout);
    std::puts("PASS P2_TOY_STAGE_TABLE_RUN markers=3");
    std::fflush(stdout);
    return 0;
}
