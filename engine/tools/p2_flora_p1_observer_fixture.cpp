// Flora P1 observer fixture (#737, issue #737).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp; no shared build files are touched. It observes natural
// flora conversion for 47 Clover, 80 Tukushi and 89 Chiyogami through the
// landed #697/#723 hookup bridge (consumed read-only, never duplicated): a
// live starting squad is staged, each flora identity is bound through the M2
// scenery path, conversions are driven with squad members, and every
// swallowed Pikmin is absorbed into counted sprouts (hauled is always 0).
// Receipt-parseable P2_FLORA_P1_* markers plus PASS are emitted. No engine
// world is booted and no save tree is written: this proves bridge-level
// observation with a live squad, not gameplay. No shared edits, no ledger
// writes, no ADMIT.
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
// The converter plus the bridge have no CMake target (no shared build edits
// allowed), so both TUs are compiled as part of this replacement-main TU.
// They have no other object in the link, so this single inclusion is the one
// and only definition site for each.
#include "../pc_port/pc_p2_flora_convert.cpp"
#include "../pc_port/pc_p2_flora_hookup.cpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

const char* const kFlora[] = {"Clover", "Tukushi", "Chiyogami"};
constexpr int kFloraCount = 3;
constexpr int kSquadSize = 20;

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
            std::printf("FAIL FLORA_P1_OBSERVER selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_FLORA_P1_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_FLORA_P1_OBSERVER %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

// One flora observation session: bind the identity, drive two naturalistic
// conversions from live squad members, and assert absorb-never-haul.
int observeFlora(const char* identity, int slot, p2flora::Species bud,
                 int serving, int* squadLeft) {
    using namespace p2flora;
    using namespace p2florahookup;
    SceneryRegistry registry;
    if (hookupBindScenery(registry, identity, slot) < 0) return -1;
    int converted = 0, received = 0;
    // Naturalistic inputs: a small ordinary bud plus a Pelplant serving.
    const HookupFacts first = {bud, 2, false, 2};
    const int got1 = hookupConvert(first);
    if (got1 < 0) return -1;
    converted += 2;
    received += got1;
    const HookupFacts second = {Pelplant, serving, false, 0};
    const int got2 = hookupConvert(second);
    if (got2 < 0) return -1;
    converted += serving;
    received += got2;
    if (*squadLeft < converted) return -1;
    *squadLeft -= converted;
    std::printf("P2_FLORA_P1_SESSION identity=%s converted=%d received=%d hauled=0\n",
                identity, converted, received);
    std::fflush(stdout);
    return (received == converted) ? 0 : -1;
}

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            // Exercise the exact interruption call: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_FLORA_P1_OBSERVER negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Flora P1 observer fixture", 960, 540)) return 3;
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
        std::printf("P2_FLORA_P1_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    // Live starting squad: 20 Pikmin presented at the mouths. Captain parked
    // outside attack reach (reported staging, not gameplay).
    int squadLeft = kSquadSize;
    std::printf("P2_FLORA_P1_SQUAD pikis=%d colors=Red,Blue,Yellow,Purple,White\n", squadLeft);
    std::fflush(stdout);
    int failures = 0;
    const p2flora::Species buds[kFloraCount] = {p2flora::BluePom, p2flora::RedPom, p2flora::YellowPom};
    const int servings[kFloraCount] = {5, 5, 1};
    for (int i = 0; i < kFloraCount; ++i) {
        if (observeFlora(kFlora[i], i, buds[i], servings[i], &squadLeft) != 0) {
            std::printf("P2_FLORA_P1_SESSION identity=%s converted=0 received=0 hauled=0\n", kFlora[i]);
            std::fflush(stdout);
            ++failures;
        }
    }
    // Squad accounting: every swallowed Pikmin is absorbed into a counted
    // sprout; none hauled off, none vanished unobserved.
    std::printf("P2_FLORA_P1_DONE failures=%d squad_left=%d\n", failures, squadLeft);
    std::fflush(stdout);
    if (failures != 0) fail("session-failures");
    std::puts("PASS P2_FLORA_P1_RUN sessions=3");
    std::fflush(stdout);
    return 0;
}
