// Damagumo bind-mod guarded fixture (#727, issue #727).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp by scripts/build_p2_damagumo_bind_mod.py; no shared
// build files are touched. It loads the produced
// `longlegs_Damagumo_bind_00.mod` (staged into the run
// assets/dataDir/courses/pikmin2room/) through the family bind path checks:
// size budget plus the real `p2animation::resources()` container parse that
// `loadBind()` enforces before `gameflow.loadShape`. Draw-path execution with
// a live Damagumo actor stays #173 arena scope and is explicitly not claimed
// here; this fixture proves the artifact the bind consumes is present and
// valid, with no abort and no captain-down.
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
#include <vector>
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
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include "pc_p2_animation.h"

namespace {

const char* const kModPath = "assets/dataDir/courses/pikmin2room/longlegs_Damagumo_bind_00.mod";
constexpr size_t kMeshBytes = 4 * 1024 * 1024; // mirrors loadBind budget
constexpr size_t kTotalBytes = 16 * 1024 * 1024;

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
            std::printf("FAIL DAMAGUMO_BIND_MOD selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_DAMAGUMO_BIND_MOD_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL P2_DAMAGUMO_BIND_MOD %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

} // namespace

int main(int argc, char** argv) {
    const char* modPath = kModPath;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            // Exercise the exact interruption call: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_DAMAGUMO_BIND_MOD negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
        if (!std::strncmp(argv[i], "--mod=", 6)) modPath = argv[i] + 6;
    }
    std::ifstream file(modPath, std::ios::binary | std::ios::ate);
    if (!file) fail("missing-bind-mod");
    const auto size = file.tellg();
    if (size <= 0 || size_t(size) > kMeshBytes) fail("bind-mod-budget");
    if (size_t(size) > kTotalBytes) fail("bind-mod-total-budget");
    file.seekg(0);
    std::vector<unsigned char> data(size_t(size), 0);
    if (!file.read(reinterpret_cast<char*>(data.data()), size)) fail("unreadable-bind-mod");
    std::vector<unsigned char> resources;
    if (!p2animation::resources(data, resources)) fail("invalid-bind-resources");
    std::printf("P2_DAMAGUMO_BIND_LOADED bytes=%lld resources=%zu\n",
                (long long)data.size(), resources.size());
    std::fflush(stdout);
    std::puts("PASS P2_DAMAGUMO_BIND_MOD_LOADED");
    std::fflush(stdout);
    return 0;
}
