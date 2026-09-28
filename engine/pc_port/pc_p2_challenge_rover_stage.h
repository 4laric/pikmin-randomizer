#pragma once

#include <cstddef>

// Pinned rover challenge stage row for the persistence call site
// (issue #734, lane rover-stage-table-row-native).
//
// ch_MAT_route_rover (P2 Challenge 28, ui_index 27) is absent from the
// engine boot table (pc_bbft.cpp kP2ChallengeStages carries only
// ch_NARI_01kusachi), so the boot selects no stage. This module carries the
// single pinned row plus a fail-closed lookup, mirroring the field layout
// of P2ChallengeStageRow read-only; it never modifies shared tables.
//
// Source facts (issue #561 contract, read-only):
//   cave_id ch_MAT_route_rover, cave_path
//   user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt,
//   source_sha256 e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79,
//   table_order 21, ui_index 27, floors 1, floor_seconds [90.0],
//   starting roster colors 0..2 maturity 2 x20 each, legacy_time 300.0,
//   bitter_sprays 2, spicy_sprays 2, treasure_count_field 0.
//
// SERIALIZED integration (NOT done here): appending this row to
// pc_bbft.cpp kP2ChallengeStages and wiring the CMake target needs owner
// #186 review first (shared pc_bbft.cpp/CMakeLists.txt are owned by the
// #728/#725 lines). Specified as follow-on in
// docs/PIKMIN2_ROVER_STAGE_TABLE_ROW.md. Nothing here claims gameplay
// acceptance.
//
// Engine-free boundary: this header and its .cpp compile with -Ipc_port
// only (cstddef/cstring/cstdio). No engine includes, no file I/O, no
// ledger writes.

namespace p2roverstage {

// One pinned retail stage row. Field order mirrors P2ChallengeStageRow.
struct RoverStageRow {
    const char* caveId;
    const char* cavePath;
    const char* sourceSha256;
    int uiIndex;
    int tableOrder;
    int floors;
    float floorSeconds[8];
    int roster[7][3];
    int bitterSprays;
    int spicySprays;
    float legacyTime;
    int treasureCountField;
};

// The single pinned ch_MAT_route_rover row (ui 27). Pointer-stable.
const RoverStageRow* roverRow();

// Fail-closed lookup by cave_id: null/empty/oversize/unknown refuses
// (nullptr) with no state change. Exact match only; the only known id is
// "ch_MAT_route_rover".
const RoverStageRow* roverLookup(const char* caveId);

// Field-by-field agreement of a row against the pinned values above.
// Used by the guarded fixture; no markers, no I/O.
bool roverRowMatches(const RoverStageRow* row);

// Number of rows carried (exactly 1: this module never grows a table;
// multi-row boot tables stay with the engine owner).
std::size_t roverRowCount();

} // namespace p2roverstage
