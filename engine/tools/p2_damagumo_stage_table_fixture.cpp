// Damagumo stage-table resolution fixture (#742).
//
// Standalone translation unit: proves the pinned ch_MUKI_damagumo row
// resolves by exact cave id (and nothing else does), emits
// receipt-parseable markers, and exercises the #632 captain-guard
// negative path. Links only the row TU plus a C++ runtime: no engine
// objects, no game boot, no gameplay. All six gates stay UNTESTED.
//
// Captain inputs here are SIMULATED command-line values, labelled as such;
// real runtime checks require engine state (see the serialized integration
// follow-on). Guard vendored verbatim from scripts/p2_fixture_captain_guard.h
// (sha256 d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
// Usage:
//   p2_damagumo_stage_table_fixture --cave-id ch_MUKI_damagumo [--expect-resolved 1]
//   p2_damagumo_stage_table_fixture --cave-id ch_NARI_01kusachi --expect-resolved 0
//   p2_damagumo_stage_table_fixture --cave-id ch_MUKI_damagumo --captain-down [--expect-resolved 1]
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>

#include "pc_p2_challenge_damagumo_stage.h"

// Vendored verbatim from scripts/p2_fixture_captain_guard.h (sha256 above).
// Observation-only; the canonical header is consumed read-only at review.
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

namespace {

int rosterTotal(const P2DamagumoStageRow& row) {
    int total = 0;
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h) total += row.roster[c][h];
    return total;
}

} // namespace

int main(int argc, char** argv)
{
    const char* caveId = nullptr;
    int expectResolved = -1;
    bool captainDown = false;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--cave-id") && i + 1 < argc) caveId = argv[++i];
        else if (!std::strcmp(argv[i], "--expect-resolved") && i + 1 < argc) expectResolved = std::atoi(argv[++i]);
        else if (!std::strcmp(argv[i], "--captain-down")) captainDown = true;
        else {
            std::printf("P2_DAMAGUMO_STAGE_USAGE unknown_arg=%s\n", argv[i]);
            return 2;
        }
    }
    if (!caveId) {
        std::puts("P2_DAMAGUMO_STAGE_USAGE missing_cave_id");
        return 2;
    }
    // #632 guard BEFORE any observation. Simulated inputs, labelled.
    std::printf("P2_DAMAGUMO_STAGE_GUARD guard_inputs=SIMULATED\n");
    p2_fixture_require_captain(captainDown, false, captainDown ? 0.5f : 100.0f, 0);
    const P2DamagumoStageRow* row = p2_damagumo_stage_lookup(caveId);
    const int resolved = row ? 1 : 0;
    if (expectResolved >= 0 && resolved != expectResolved) {
        std::printf("P2_DAMAGUMO_STAGE_MISMATCH cave=%s resolved=%d expected=%d\n",
                    caveId, resolved, expectResolved);
        return 1;
    }
    if (!row) {
        std::printf("P2_DAMAGUMO_STAGE_REFUSED cave=%s\n", caveId);
        return expectResolved == 0 ? 0 : 1;
    }
    std::printf("P2_DAMAGUMO_STAGE_RESOLVED cave=%s ui_index=%d floors=%d roster_total=%d "
                "bitter=%d spicy=%d legacy=%.1f treasure=%d source=%.8s\n",
                row->caveId, row->uiIndex, row->floors, rosterTotal(*row),
                row->bitterSprays, row->spicySprays, (double)row->legacyTime,
                row->treasureCountField, row->sourceSha256);
    std::printf("P2_DAMAGUMO_STAGE_GATES all=UNTESTED content_wired=0\n");
    return 0;
}
