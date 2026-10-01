// Guarded standalone fixture for the pinned rover stage row (#734).
//
// Compiles with -Ipc_port ONLY (no engine headers: the engine-free policy
// boundary is enforced by the build itself):
//
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port
//       tools/p2_rover_stage_table_fixture.cpp
//       pc_port/pc_p2_challenge_rover_stage.cpp
//       -o p2_rover_stage_table_fixture
//
// Proves the rover row resolves by cave_id and by ui index contract, the
// pinned fields match exactly, and unknown/malformed keys refuse fail-closed.
// Emits P2_ROVER_STAGE_* marker lines on stdout plus a checks summary; exit 0
// only when every check passes. A printed row alone cannot pass: every claim
// below executes the provider lookup and asserts the outcome.
//
// This fixture boots no game world, so captain-safety #632 has no Navi to
// observe (same construction as the #727 load proof). The guard header
// scripts/p2_fixture_captain_guard.h (sha256 recorded in the handoff doc) is
// adopted by reference for any future game-world run of this harness; no
// blanket invincibility exists anywhere here.
#include <cstdio>
#include <cstring>

#include "pc_p2_challenge_rover_stage.h"

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

void emitResolved(const p2roverstage::RoverStageRow* row)
{
    std::printf("P2_ROVER_STAGE_RESOLVED cave=%s ui=%d floors=%d\n",
                row->caveId, row->uiIndex, row->floors);
    std::fflush(stdout);
}

void emitRefused(const char* reason)
{
    std::printf("P2_ROVER_STAGE_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
}

} // namespace

int main()
{
    using namespace p2roverstage;

    // 1. Row count contract: exactly one pinned row, never a table.
    check(roverRowCount() == 1, "row-count-is-one");

    // 2. Pinned row fields match the #561 source contract exactly.
    {
        const RoverStageRow* row = roverRow();
        check(row != nullptr, "row-present");
        check(roverRowMatches(row), "row-matches-pinned");
        check(std::strcmp(row->caveId, "ch_MAT_route_rover") == 0, "cave-id");
        check(std::strcmp(row->cavePath,
                          "user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt") == 0,
              "cave-path");
        check(std::strcmp(row->sourceSha256,
                          "e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79") == 0,
              "source-sha");
        check(row->uiIndex == 27, "ui-index-27");
        check(row->tableOrder == 21, "table-order-21");
        check(row->floors == 1, "floors-1");
        check(row->floorSeconds[0] == 90.0f, "floor-seconds-90");
        check(row->roster[0][2] == 20 && row->roster[1][2] == 20 &&
              row->roster[2][2] == 20, "starting-roster-3x20");
        check(row->roster[3][2] == 0 && row->roster[6][2] == 0, "roster-rest-zero");
        check(row->bitterSprays == 2 && row->spicySprays == 2, "sprays-2-2");
        check(row->legacyTime == 300.0f, "legacy-time-300");
        check(row->treasureCountField == 0, "treasure-field-0");
        if (roverRowMatches(row)) {
            emitResolved(row);
        }
    }
    // 3. Lookup resolves the known id and refuses everything else.
    {
        const RoverStageRow* hit = roverLookup("ch_MAT_route_rover");
        check(hit != nullptr && hit == roverRow(), "lookup-known-id");
        const char* badIds[] = {nullptr, "", "ch_NARI_01kusachi", "CH_MAT_ROUTE_ROVER",
                                "ch_MAT_route_rover ", "ch_MAT_route_rover!"};
        for (std::size_t i = 0; i < sizeof(badIds) / sizeof(badIds[0]); ++i) {
            const RoverStageRow* miss = roverLookup(badIds[i]);
            check(miss == nullptr, "lookup-refuses-unknown");
            if (miss == nullptr) {
                emitRefused("unknown-key");
            }
        }
        char oversize[70];
        std::memset(oversize, 'a', sizeof(oversize) - 1);
        oversize[sizeof(oversize) - 1] = '\0';
        check(roverLookup(oversize) == nullptr, "lookup-refuses-oversize");
    }
    // 4. Mutation detector: a tampered row must NOT match.
    {
        RoverStageRow tampered = *roverRow();
        tampered.uiIndex = 28;
        check(!roverRowMatches(&tampered), "tampered-ui-rejected");
        tampered = *roverRow();
        tampered.roster[0][2] = 21;
        check(!roverRowMatches(&tampered), "tampered-roster-rejected");
        check(!roverRowMatches(nullptr), "null-row-rejected");
    }
    std::printf("checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
