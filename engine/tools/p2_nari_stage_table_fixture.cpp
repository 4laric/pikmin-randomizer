// Pinned NARI stage-table boot fixture with argv stage select (#769).
//
// Resolves the pinned 02tile (ui 4) and 03toy (ui 5) rows by ui_index
// (default runs both; argv[1] selects one), prints the boot pops (02tile 50,
// 03toy 100) and ticks each resolved row with the #632 captain guard.
// Markers use the P2_NARI_STAGE_ prefix. The module TU rides along via
// include so no CMake target edit is needed (serialized #186 follow-on).
// Fail-closed: unknown ui exits 2, guard trip exits 86, --no-guard refuses.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "../pc_port/pc_p2_challenge_nari_stages.h"
#include "../pc_port/pc_p2_challenge_nari_stages.cpp"

// Captain-safety guard (#632), vendored verbatim semantics from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
// Observation-only; CAPTAIN_DOWN exits 86 (BLOCKED).
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(stdout);
    std::_Exit(86);
}

static int runOne(int ui) {
    int index = p2challenge::nari::selectNariByUiIndex(ui);
    if (index < 0) {
        std::printf("P2_NARI_STAGE_ERROR missing_stage ui=%d\n", ui);
        std::fflush(nullptr);
        return 2;
    }
    const p2challenge::nari::NariStageRow& entry =
        p2challenge::nari::kNariStages[index];
    std::printf("P2_NARI_STAGE_RESOLVED cave=%s ui_index=%d floors=%d\n",
                entry.caveId, entry.uiIndex, entry.floorCount);
    std::fflush(nullptr);
    const int pops = p2challenge::nari::bootPopTotal(entry);
    std::printf("P2_NARI_STAGE_BOOT_POP cave=%s pops=%d\n", entry.caveId, pops);
    std::fflush(nullptr);
    for (int tickNo = 0; tickNo < 3; ++tickNo) {
        p2_fixture_require_captain(false, false, 100.0f, tickNo);
        std::printf("P2_NARI_STAGE_TICK cave=%s tick=%d\n", entry.caveId, tickNo);
        std::fflush(nullptr);
    }
    return 0;
}

static int selfTest() {
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.5f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {false, true, 100.0f, true},
        {true, false, 100.0f, true},
    };
    for (size_t r = 0; r < sizeof(rows) / sizeof(rows[0]); ++r) {
        if (p2_fixture_captain_down(rows[r].orima, rows[r].dead, rows[r].hp) != rows[r].expectDown) {
            std::printf("FAIL P2_NARI_STAGE_GUARD_SELFTEST row=%d\n", int(r));
            std::fflush(nullptr);
            return 1;
        }
    }
    if (p2challenge::nari::selectNariByUiIndex(999) >= 0) {
        std::printf("FAIL P2_NARI_STAGE_GUARD_SELFTEST unknown-accepted\n");
        std::fflush(nullptr);
        return 1;
    }
    std::printf("P2_NARI_STAGE_GUARD_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(nullptr);
    return 0;
}

int main(int argc, char** argv) {
    bool guard = true;
    int stages[2] = {4, 5};
    int count = 2;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--no-guard")) {
            guard = false;
        } else if (!std::strcmp(argv[i], "--self-test")) {
            return selfTest();
        } else if (!std::strcmp(argv[i], "--negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_NARI_STAGE negative test did not trip\n");
            std::fflush(nullptr);
            return 1;
        } else {
            stages[0] = std::atoi(argv[i]);
            count = 1;
        }
    }
    if (!guard) {
        std::printf("P2_NARI_STAGE_REFUSED reason=unguarded-run\n");
        std::fflush(nullptr);
        return 2;
    }
    for (int i = 0; i < count; ++i) {
        int code = runOne(stages[i]);
        if (code) return code;
    }
    std::printf("P2_NARI_STAGE_TABLE_DONE stages=%d\n", count);
    std::fflush(nullptr);
    return 0;
}
