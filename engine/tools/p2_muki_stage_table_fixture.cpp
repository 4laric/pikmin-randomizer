// Pinned MUKI stage-table boot fixture with argv stage select (#748).
//
// Resolves the pinned houdai (ui 8) and redblue (ui 18) rows by ui_index
// (default runs both; argv[1] selects one), applies squad/sprays, ticks with
// the #632 captain guard before every observed tick, then exercises descend +
// retry. Markers use the P2_MUKI_STAGE_ prefix plus the module P2_CHALLENGE_MODE_*
// emits. The module TU rides along via include so no CMake target edit is
// needed (serialized #186 follow-on). No engine linkage; host-state only.

#include <cstdio>
#include <cstdlib>

#include "../pc_port/pc_p2_challenge_muki_stages.h"
#include "../pc_port/pc_p2_challenge_muki_stages.cpp"
// NOTE: pc_p2_challenge_mode.cpp is NOT included here because it is
// compiled into pikmin_pc on this native line; the fixture links those
// engine objects via the maintained builder. Including it would cause
// multiple-definition link errors.
#include "p2_fixture_captain_guard.h"

static int runOne(int ui) {
    int index = p2challenge::muki::selectMukiByUiIndex(ui);
    if (index < 0) {
        std::printf("P2_MUKI_STAGE_ERROR missing_stage ui=%d\n", ui);
        return 2;
    }
    const p2challenge::StageEntry& entry =
        p2challenge::muki::kMukiStages[index];
    std::printf("P2_MUKI_STAGE_RESOLVED cave=%s ui_index=%d floors=%d\n",
                entry.caveId, entry.uiIndex, entry.floorCount);
    std::fflush(nullptr);
    p2challenge::HostState state = p2challenge::start(entry);
    p2challenge::applySquadAndSprays(state, entry.bitterSprays,
                                     entry.spicySprays);
    p2challenge::emit("BOOT", state);
    for (int tickNo = 0; tickNo < 3; ++tickNo) {
        p2_fixture_require_captain(false, false, 100.0f, tickNo);
        p2challenge::tick(state, 10.0f);
        p2challenge::emit("TICK", state);
    }
    if (p2challenge::descend(state))
        p2challenge::emit("FLOOR_ADVANCE", state);
    else
        p2challenge::emit("SINGLE_FLOOR", state);
    p2challenge::HostState again = p2challenge::retry(state);
    p2challenge::emit("RETRY_STATE", again);
    return 0;
}

int main(int argc, char** argv) {
    int stages[2] = {8, 18};
    int count = 2;
    if (argc > 1) {
        stages[0] = std::atoi(argv[1]);
        count = 1;
    }
    for (int i = 0; i < count; ++i) {
        int code = runOne(stages[i]);
        if (code) return code;
    }
    std::printf("P2_MUKI_STAGE_TABLE_DONE stages=%d\n", count);
    std::fflush(nullptr);
    return 0;
}