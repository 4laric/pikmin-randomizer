// tutorial1 wrapper -c defect-fix probe fixture (#686).
//
// Proves the fixed wrapper compile path: this TU must be compiled from
// native/tools/ (never pc_port/), which it verifies at runtime via __FILE__.
// Engine-independent, stdlib-only (+ vendored guard); it is never added to a
// game target: the lane builds it directly through the fixed wrapper path
// with the same MinGW toolchain used for the private engine build.
//
// Modes:
//   --guard-self-test     run the guard truth table, print
//                         P2_TUTORIAL1_DEFECTFIX_SELFTEST_PASS, exit 0.
//   --guard-negative-test force captain-down: P2_FIXTURE_CAPTAIN_DOWN, exit
//                         86 (BLOCKED), no PASS.
//   (default run)         verify the -c directory proof, then print
//                         "PASS TUTORIAL1_DEFECTFIX" and exit 0.
// Anything else is FAIL (1), BLOCKED (86), or timeout (2).
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474);
// observation-only, equivalent tested guard. The canonical header is consumed
// read-only; this vendored copy exists because a replacement-main TU cannot
// include a Python-tree script header at native build time.
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    // std::isfinite avoided on purpose: keep this TU dependency-free.
    return orimaDead || deadState || !(hp == hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}

namespace {
bool ends_with_tools_fixture(const char* path) {
    const char* want = "tools/p2_tutorial1_defect_fix_fixture.cpp";
    std::string normalized(path);
    for (size_t i = 0; i < normalized.size(); ++i)
        if (normalized[i] == '\\') normalized[i] = '/';
    if (normalized.size() < std::strlen(want)) return false;
    return normalized.compare(normalized.size() - std::strlen(want),
                              std::string::npos, want) == 0;
}

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
            std::printf("FAIL TUTORIAL1_DEFECTFIX selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_TUTORIAL1_DEFECTFIX_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}
} // namespace

int main(int argc, char** argv) {
    bool selfTest = false, negativeTest = false;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") selfTest = true;
        if (std::string(argv[i]) == "--guard-negative-test") {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL TUTORIAL1_DEFECTFIX negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    if (selfTest) return guardSelfTest();
    if (!ends_with_tools_fixture(__FILE__)) {
        // The #674 defect compiled the fixture basename under pc_port/; a
        // fixed wrapper path always ends in tools/<this TU>.
        std::printf("FAIL TUTORIAL1_DEFECTFIX compiled_from=%s\n", __FILE__);
        std::fflush(stdout);
        return 1;
    }
    p2_fixture_require_captain(false, false, 100.0f, 0);
    std::printf("PASS TUTORIAL1_DEFECTFIX compiled_from=tools\n");
    std::fflush(stdout);
    return 0;
}
