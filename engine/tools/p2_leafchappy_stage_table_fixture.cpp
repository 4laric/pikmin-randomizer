// Guarded standalone fixture for the pinned leafchappy stage row (#774).
//
// Compiles with -Ipc_port ONLY (no engine headers: the engine-free policy
// boundary is enforced by the build itself):
//
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port
//       tools/p2_leafchappy_stage_table_fixture.cpp
//       pc_port/pc_p2_challenge_leafchappy_stage.cpp
//       -o p2_leafchappy_stage_table_fixture
//
// Proves the leafchappy row resolves by cave_id, the pinned fields match
// exactly, and unknown/malformed keys refuse fail-closed. Emits
// P2_LEAFCHAPPY_STAGE_* marker lines on stdout plus a checks summary; exit
// 0 only when every check passes. A printed row alone cannot pass: every
// claim below executes the provider lookup and asserts the outcome.
//
// Captain safety (#632): this fixture boots no game world, so there is no
// Navi to observe (same construction as the accepted #734 rover fixture).
// The vendored guard below is verbatim from
// scripts/p2_fixture_captain_guard.h (sha256 recorded in the handoff doc);
// --guard-self-test proves its 7-row truth table and --guard-negative-test
// proves the CAPTAIN_DOWN + BLOCKED(86) interruption with no PASS. The
// canonical header is adopted by reference for any future game-world run
// of this harness; no blanket invincibility exists anywhere here.
//
// Consumer contract: the p2-challenge-ch-abem-leafchappy-p1 lane (#550)
// runs this fixture expecting exactly one
// "P2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_ABEM_LeafChappy ui=17 floors=2"
// line (ui-17 resolution) plus unknown-key refusals.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "pc_p2_challenge_leafchappy_stage.h"

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474);
// observation-only, equivalent tested guard.
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

int failures = 0;
int checks = 0;

void check(bool condition, const char* name)
{
    ++checks;
    if (!condition) {
        ++failures;
        std::printf("FAIL %s\n", name);
    }
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
            std::printf("FAIL LEAFCHAPPY selftest row=%d orima=%d dead=%d hp=%.3f\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp);
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_LEAFCHAPPY_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void emitResolved(const p2leafchappystage::LeafchappyStageRow* row)
{
    std::printf("P2_LEAFCHAPPY_STAGE_RESOLVED cave=%s ui=%d floors=%d\n",
                row->caveId, row->uiIndex, row->floors);
    std::fflush(stdout);
}

void emitRefused(const char* reason)
{
    std::printf("P2_LEAFCHAPPY_STAGE_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
}

} // namespace

int main(int argc, char** argv)
{
    using namespace p2leafchappystage;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL LEAFCHAPPY negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }

    // 1. Row count contract: exactly one pinned row, never a table.
    check(leafchappyRowCount() == 1, "row-count-is-one");

    // 2. Pinned row fields match the lane-plan source contract exactly.
    {
        const LeafchappyStageRow* row = leafchappyRow();
        check(row != nullptr, "row-present");
        check(leafchappyRowMatches(row), "row-matches-pinned");
        check(std::strcmp(row->caveId, "ch_ABEM_LeafChappy") == 0, "cave-id");
        check(std::strcmp(row->cavePath,
                          "user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt") == 0,
              "cave-path");
        check(std::strcmp(row->sourceSha256,
                          "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf") == 0,
              "source-sha");
        check(row->uiIndex == 17, "ui-index-17");
        check(row->tableOrder == 4, "table-order-4");
        check(row->floors == 2, "floors-2");
        check(row->floorSeconds[0] == 85.0f && row->floorSeconds[1] == 100.0f,
              "floor-seconds-85-100");
        check(row->roster[0][0] == 10 && row->roster[1][0] == 10 &&
              row->roster[2][0] == 10, "starting-roster-3x10");
        check(row->roster[3][0] == 0 && row->roster[6][2] == 0, "roster-rest-zero");
        check(row->bitterSprays == 1 && row->spicySprays == 1, "sprays-1-1");
        check(row->legacyTime == 400.0f, "legacy-time-400");
        check(row->treasureCountField == 11, "treasure-field-11");
        if (leafchappyRowMatches(row)) {
            emitResolved(row);
        }
    }
    // 3. Lookup resolves the known id and refuses everything else.
    {
        const LeafchappyStageRow* hit = leafchappyLookup("ch_ABEM_LeafChappy");
        check(hit != nullptr && hit == leafchappyRow(), "lookup-known-id");
        const char* badIds[] = {nullptr, "", "ch_NARI_01kusachi", "CH_ABEM_LEAFCHAPPY",
                                "ch_ABEM_LeafChappy ", "ch_ABEM_LeafChappy!"};
        for (std::size_t i = 0; i < sizeof(badIds) / sizeof(badIds[0]); ++i) {
            const LeafchappyStageRow* miss = leafchappyLookup(badIds[i]);
            check(miss == nullptr, "lookup-refuses-unknown");
            if (miss == nullptr) {
                emitRefused("unknown-key");
            }
        }
        char oversize[70];
        std::memset(oversize, 'a', sizeof(oversize) - 1);
        oversize[sizeof(oversize) - 1] = '\0';
        check(leafchappyLookup(oversize) == nullptr, "lookup-refuses-oversize");
    }
    // 4. Mutation detector: a tampered row must NOT match.
    {
        LeafchappyStageRow tampered = *leafchappyRow();
        tampered.uiIndex = 18;
        check(!leafchappyRowMatches(&tampered), "tampered-ui-rejected");
        tampered = *leafchappyRow();
        tampered.roster[0][0] = 11;
        check(!leafchappyRowMatches(&tampered), "tampered-roster-rejected");
        check(!leafchappyRowMatches(nullptr), "null-row-rejected");
    }
    std::printf("checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
