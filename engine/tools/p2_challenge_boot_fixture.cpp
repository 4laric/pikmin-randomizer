// P2 challenge-stage boot fixture with argv stage select (#672).
//
// Boots a pinned stage entry by ui_index (default 7 = ch_MUKI_bigfoot), applies
// squad/sprays, ticks with the #632 captain guard before every observed tick,
// then exercises descend + retry. Markers use the P2_CHALLENGE_BOOT_ prefix.
// The module TU rides along via include; registered in CMakeLists.txt as the
// p2_challenge_boot_fixture executable + ctest test (#674).


#include <cstdio>
#include <cstdlib>


#include "../pc_port/pc_p2_challenge_mode.h"
#include "../pc_port/pc_p2_challenge_mode.cpp"
#include "p2_fixture_captain_guard.h"


static const p2challenge::StageEntry kStages[] = {
    {"ch_MUKI_bigfoot", 7, 1, {200.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {25, 0, 0}, {0, 0, 0}, {0, 0, 0}, {25, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 0, 2},
    {"ch_MUKI_metal", 1, 2, {130.0f, 100.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 50}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 1, 1},
    // Lane p2-challenge-ch-mat-crawler-p1 (#562) private-worktree addition:
    // ch_MAT_crawler entry decoded live from the retail stage table
    // (ui 29, 2 floors 170/120 s, roster [[0,0,30],[0,0,30],...], bitter 3,
    // spicy 4). Population sums to 60. Private to this lane's native worktree;
    // not a shared edit.
    {"ch_MAT_crawler", 29, 2, {170.0f, 120.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 30}, {0, 0, 30}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 3, 4},
};


int main(int argc, char** argv) {
    int ui = 7;
    if (argc > 1) ui = std::atoi(argv[1]);
    int index = p2challenge::selectByUiIndex(kStages, 3, ui);
    if (index < 0) {
        std::printf("P2_CHALLENGE_BOOT_ERROR missing_stage ui=%d\n", ui);
        return 2;
    }
    p2challenge::HostState state = p2challenge::start(kStages[index]);
    p2challenge::applySquadAndSprays(state, kStages[index].bitterSprays,
                                   kStages[index].spicySprays);
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
    std::printf("P2_CHALLENGE_BOOT_DONE end=%s score=%d\n",
                state.endState ? state.endState : "none",
                p2challenge::score(state));
}
