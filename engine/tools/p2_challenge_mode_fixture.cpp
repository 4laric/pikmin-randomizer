// P2 Challenge host-state UNIT TEST (#651) - NOT a game-linked boot fixture.
//
// Classification (per #651/#186 review, pinned challenge-host-review.md sha256
// fc3901ad...): this target links only the host-state module plus a standalone
// main. It does NOT link game startup, cannot prove real captain health,
// window adoption, engine stage selection or engine boot, and must never be
// described as a "game-linked guarded boot fixture".
//
// What it DOES verify, deterministically and engine-free:
//   * stage selection by the contract's ui_index over a labelled SAMPLE table;
//   * squad/spray application from the entry's contract fields;
//   * mTimeLimit countdown and per-floor timer extension on descend;
//   * ordinary vs deathless result and the retry/reset boundary;
//   * the #632 captain guard's negative path (exit 86 / BLOCKED).
//
// Captain inputs here are SIMULATED command-line values, not engine state.
// Real runtime checks require actual engine state and a negative captain-down
// observation; see docs/PIKMIN2_CHALLENGE_MODE.md (engine boot-hook patch and
// required ownership are specified there).
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include "pc_p2_challenge_mode.h"
#include "p2_fixture_captain_guard.h"

namespace {

// Labelled SAMPLE table: two decoded-contract-shaped entries used only to
// exercise selection and timing logic. Not retail evidence.
const p2challenge::StageEntry kSampleStages[] = {
    {"ch_MUKI_metal", 1, 2, {130.0f, 100.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 50}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}}, 1, 1},
    {"ch_NARI_01kusachi", 3, 1, {180.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 50}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}}, 1, 2},
};

} // namespace

int main(int argc, char** argv)
{
    int uiIndex = 1;
    float captainHp = 100.0f;
    bool orimaDead = false, naviDead = false, simulateCaptainDown = false;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--ui-index") && i + 1 < argc) uiIndex = std::atoi(argv[++i]);
        else if (!std::strcmp(argv[i], "--captain-hp") && i + 1 < argc) captainHp = float(std::atof(argv[++i]));
        else if (!std::strcmp(argv[i], "--orima-dead")) orimaDead = true;
        else if (!std::strcmp(argv[i], "--navi-dead")) naviDead = true;
        else if (!std::strcmp(argv[i], "--captain-down")) simulateCaptainDown = true;
    }

    const int stageCount = int(sizeof(kSampleStages) / sizeof(kSampleStages[0]));
    const int index = p2challenge::selectByUiIndex(kSampleStages, stageCount, uiIndex);
    if (index < 0) {
        std::printf("P2_CHALLENGE_HOSTSTATE_ERROR missing_stage ui_index=%d\n", uiIndex);
        return 2;
    }

    p2challenge::HostState state = p2challenge::start(kSampleStages[index]);
    p2challenge::applySquadAndSprays(state, kSampleStages[index].bitterSprays, kSampleStages[index].spicySprays);
    std::printf("P2_CHALLENGE_HOSTSTATE_KIND unit_test guard_inputs=SIMULATED\n");
    p2challenge::emit("BOOT", state);

    const float effectiveHp = simulateCaptainDown ? 0.5f : captainHp;
    const bool effectiveDead = simulateCaptainDown || orimaDead || naviDead;
    for (int tickNo = 0; tickNo < 3; ++tickNo) {
        // #632 guard BEFORE observing the tick. Simulated inputs are labelled.
        p2_fixture_require_captain(effectiveDead, false, effectiveHp, tickNo);
        p2challenge::tick(state, 10.0f);
        p2challenge::emit("TICK", state);
    }

    if (p2challenge::descend(state)) p2challenge::emit("FLOOR_ADVANCE", state);
    p2challenge::HostState again = p2challenge::retry(state);
    p2challenge::emit("RETRY_STATE", again);
    std::printf("P2_CHALLENGE_HOSTSTATE_DONE end=%s score=%d\n",
                state.endState ? state.endState : "none", p2challenge::score(state));
    return 0;
}