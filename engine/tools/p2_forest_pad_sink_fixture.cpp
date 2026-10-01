// Forest controller PAD sink guarded fixture (lane forest-controller-pad-sink-native, #794).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp (response-file rewrite; no shared build files touched).
// Proves ControllerMgr::keyDown observes scripted presses injected through the
// test-only ControllerMgr::testSinkPadButtons sink, and reads false without
// injection. Headless by design: keyDown reads static PAD state, so no window,
// engine boot, or game world is needed; no blanket invincibility exists here.
//
// Captain safety (#632): the canonical guard is vendored verbatim and proven
// by the self-test and negative-test modes below. There is no Navi to observe
// per tick in this headless probe; no gameplay is claimed.
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
#include "Controller.h"
#include "Dolphin/pad.h"
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
            std::printf("FAIL FOREST_PAD_SINK selftest row=%d\n", int(i));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_FOREST_PAD_SINK_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_FOREST_PAD_SINK %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL FOREST_PAD_SINK negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    ControllerMgr pad;
    // Baseline: no injection must read false (proves the sink, not stale state).
    ControllerMgr::testSinkPadButtons(0);
    if (pad.keyDown(PAD_BUTTON_A) || pad.keyDown(PAD_BUTTON_START)) fail("baseline-not-clear");
    std::printf("P2_FOREST_PAD_SINK_BASELINE_CLEAR\n");
    std::fflush(stdout);
    // Inject A: keyDown(A) true, keyDown(START) still false (no bleed).
    ControllerMgr::testSinkPadButtons(PAD_BUTTON_A);
    if (!pad.keyDown(PAD_BUTTON_A)) fail("injected-A-unobserved");
    if (pad.keyDown(PAD_BUTTON_START)) fail("injected-A-bleed");
    std::printf("P2_FOREST_PAD_SINK_OBSERVED button=A\n");
    std::fflush(stdout);
    // Inject START: keyDown(START) true, keyDown(A) still false.
    ControllerMgr::testSinkPadButtons(PAD_BUTTON_START);
    if (!pad.keyDown(PAD_BUTTON_START)) fail("injected-START-unobserved");
    if (pad.keyDown(PAD_BUTTON_A)) fail("injected-START-bleed");
    std::printf("P2_FOREST_PAD_SINK_OBSERVED button=START\n");
    std::fflush(stdout);
    // Clear again: both false (proves the sink writes, not latches).
    ControllerMgr::testSinkPadButtons(0);
    if (pad.keyDown(PAD_BUTTON_A) || pad.keyDown(PAD_BUTTON_START)) fail("clear-not-observed");
    std::printf("P2_FOREST_PAD_SINK_GATES all=UNTESTED content_wired=0\n");
    std::fflush(stdout);
    std::puts("PASS P2_FOREST_PAD_SINK_RUN markers=3");
    std::fflush(stdout);
    return 0;
}
