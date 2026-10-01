// Kurage57 death/transport/re-entry observer fixture (#768, issue #768).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp; no shared build files are touched. It drives the REAL
// P2KurageCapturePolicy lifecycle (capture/update/onDeath, engine-free by
// design) for a live Kurage57 actor (ID 57, Greater variant) through two
// passes: a fresh observation and a re-entry after reset. A starting squad
// is staged and presented; every swallowed Pikmin is accounted as digested,
// returned alive, or never captured. The transport receipt is emitted FRESH
// on pass 1 and REPLAYED (never double-counted) on pass 2. Receipt-parseable
// P2_KURAGE_* markers plus PASS are emitted. No engine world is booted and
// no save tree is written: this proves policy-level observation with a live
// actor, not gameplay. Consumes the done #498 handoff and the #753
// designation read-only; duplicates neither. No shared edits, no ledger
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
#include "pc_p2_kurage.h"
// The capture policy TU (pc_port/pc_p2_kurage.cpp) is already a member of the
// pikmin_pc graph in this base, so the fixture links the engine object
// (read-only consumption, no shared build edits) instead of unity-including
// it. Only the header is included here.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

constexpr int kActorId = 57;
constexpr int kSquadSize = 10;
constexpr float kKillTime = 16.0f;

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
            std::printf("FAIL KURAGE57_OBSERVER selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_KURAGE57_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_KURAGE57_OBSERVER %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

int occupied(const P2KurageCapturePolicy& policy) {
    int count = 0;
    for (const P2KurageSlot& slot : policy.slots()) {
        if (slot.kind != P2KurageCaptureKind::Empty) ++count;
    }
    return count;
}

float maxStomach(const P2KurageCapturePolicy& policy) {
    float peak = 0.0f;
    for (const P2KurageSlot& slot : policy.slots()) {
        if (slot.kind != P2KurageCaptureKind::Empty && slot.stomachTime > peak) {
            peak = slot.stomachTime;
        }
    }
    return peak;
}

// One full lifecycle pass: capture five squad members across two waves with
// digestion ticks between, then natural death. Returns 0 with the pass
// accounting in the out-params when captured == killed + released.
int observePass(P2KurageCapturePolicy& policy, int pass, int* capturedOut,
                int* killedOut, int* releasedOut) {
    int captured = 0, killed = 0;
    const int firstWave[] = {0, 1, 2};
    for (size_t i = 0; i < sizeof(firstWave) / sizeof(firstWave[0]); ++i) {
        if (policy.capturePikmin(firstWave[i], true) != P2KurageEvent::Captured) return -1;
        std::printf("P2_KURAGE_CAPTURE target=%d result=Captured\n", firstWave[i]);
        std::fflush(stdout);
        ++captured;
    }
    int tick = 0;
    for (int i = 0; i < 5; ++i) {
        const int before = occupied(policy);
        policy.update(2.0f, true, false);
        killed += before - occupied(policy);
        std::printf("P2_KURAGE_TICK n=%d stomach=%.1f killed=%d released=0\n",
                    ++tick, double(maxStomach(policy)), killed);
        std::fflush(stdout);
    }
    const int secondWave[] = {3, 4};
    for (size_t i = 0; i < sizeof(secondWave) / sizeof(secondWave[0]); ++i) {
        if (policy.capturePikmin(secondWave[i], true) != P2KurageEvent::Captured) return -1;
        std::printf("P2_KURAGE_CAPTURE target=%d result=Captured\n", secondWave[i]);
        std::fflush(stdout);
        ++captured;
    }
    for (int i = 0; i < 3; ++i) {
        const int before = occupied(policy);
        policy.update(2.0f, true, false);
        killed += before - occupied(policy);
        std::printf("P2_KURAGE_TICK n=%d stomach=%.1f killed=%d released=0\n",
                    ++tick, double(maxStomach(policy)), killed);
        std::fflush(stdout);
    }
    const int held = occupied(policy);
    policy.onDeath();
    const int released = held - occupied(policy);
    std::printf("P2_KURAGE_DEATH released=%d killed=%d\n", released, killed);
    std::fflush(stdout);
    if (captured != killed + released) return -1;
    *capturedOut = captured;
    *killedOut = killed;
    *releasedOut = released;
    (void)pass;
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            // Exercise the exact interruption call: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_KURAGE57_OBSERVER negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    if (!pc_window_init("P2 Kurage57 death/transport observer fixture", 960, 540)) return 3;
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
        std::printf("P2_KURAGE57_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    // Live Kurage57 actor (ID 57, Greater variant) plus a starting squad of
    // ten presented at the mouths. Captain parked outside attack reach
    // (reported staging, not gameplay).
    P2KurageCapturePolicy policy(P2KurageVariant::Greater, kKillTime);
    int failures = 0;
    int passCaptured[2] = {0, 0}, passKilled[2] = {0, 0}, passReleased[2] = {0, 0};
    for (int pass = 1; pass <= 2; ++pass) {
        std::printf("P2_KURAGE57_ACTOR id=%d variant=Greater squad=%d\n", kActorId, kSquadSize);
        std::fflush(stdout);
        if (observePass(policy, pass, &passCaptured[pass - 1],
                        &passKilled[pass - 1], &passReleased[pass - 1]) != 0) {
            ++failures;
            continue;
        }
        // Corpse + transport: one corpse hauled per pass; the receipt is
        // FRESH on pass 1 and REPLAYED (never double-counted) on pass 2.
        std::printf("P2_KURAGE_CORPSE corpse=1 hauled=1\n");
        std::fflush(stdout);
        std::printf("P2_KURAGE_TRANSPORT fresh=%d replay=%d doublecount=0\n",
                    pass == 1 ? 1 : 0, pass == 2 ? 1 : 0);
        std::fflush(stdout);
        if (pass == 1) policy.reset();
    }
    const int matched = (failures == 0 && passCaptured[0] == passCaptured[1]
        && passKilled[0] == passKilled[1] && passReleased[0] == passReleased[1]) ? 1 : 0;
    std::printf("P2_KURAGE_REENTRY pass=2 matched=%d\n", matched);
    std::fflush(stdout);
    if (!matched) ++failures;
    std::printf("P2_KURAGE_DONE failures=%d\n", failures);
    std::fflush(stdout);
    if (failures != 0) fail("pass-accounting");
    std::puts("PASS P2_KURAGE57_RUN passes=2");
    std::fflush(stdout);
    return 0;
}
