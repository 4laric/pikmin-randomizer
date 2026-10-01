// tutorial1 wrapper-selection probe fixture (#680, prerequisite for #674/#114).
//
// Purpose: prove the #674 `--fixture` selection path of the shared wrapper
// (scripts/build_p2_cave_guarded_boot_fixture.py) end to end with COMPILED
// evidence, independently of the consumer-owned tutorial1 fixture. This TU is
// a minimal replacement-main: the wrapper compiles it with the reference
// tools/ compile command, then links it in place of pc_main.cpp against the
// private pikmin_pc graph. It deliberately stays engine-independent so the
// produced executable can be run (and its markers checked) without a GL boot,
// rundir or assets; the consumer fixture owns the guarded engine boot.
//
// Captain guard (#632): the canonical scripts/p2_fixture_captain_guard.h
// (sha256 d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474)
// is vendored verbatim below, as the consumer fixture does, so the probe's
// guard behavior is byte-comparable and hash-pinned. It never changes state.
//
// Markers: P2_TUTORIAL1_WRAPPER_PROBE_READY then PASS TUTORIAL1_WRAPPER_PROBE
// on exit 0. --guard-self-test is engine-independent and prints
// P2_TUTORIAL1_WRAPPER_PROBE_SELFTEST_PASS. --guard-negative-test must print
// P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <string>

namespace {
// --- vendored #632 guard (scripts/p2_fixture_captain_guard.h) ---------------
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
// ---------------------------------------------------------------------------

int guardSelfTest() {
    struct Row { bool orima; bool dead; float hp; bool down; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {true, false, 100.0f, true},
        {false, true, 100.0f, true},
        {false, false, std::nanf(""), true},
    };
    int failures = 0;
    for (const Row& row : rows) {
        const bool down = p2_fixture_captain_down(row.orima, row.dead, row.hp);
        if (down != row.down) {
            std::printf("P2_TUTORIAL1_WRAPPER_PROBE_SELFTEST_FAIL orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(row.orima), int(row.dead), row.hp, int(down), int(row.down));
            ++failures;
        }
    }
    if (failures) {
        std::fflush(stdout);
        return 1;
    }
    std::printf("P2_TUTORIAL1_WRAPPER_PROBE_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        if (arg == "--guard-self-test") return guardSelfTest();
        if (arg == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL TUTORIAL1_WRAPPER_PROBE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    // Selection-path proof: a real, runnable replacement-main produced by the
    // wrapper --fixture path. No engine boot is attempted or claimed here.
    std::printf("P2_TUTORIAL1_WRAPPER_PROBE_READY argv0=%s\n", argc > 0 ? argv[0] : "?");
    std::printf("PASS TUTORIAL1_WRAPPER_PROBE\n");
    std::fflush(stdout);
    return 0;
}
