#pragma once

#include <cstddef>

// Pinned tutorial challenge stage row for the #534 consumer
// (issue #754, lane tutorial-stage-table-row-native).
//
// ch_ABEM_tutorial (P2 Challenge 01, ui_index 0) is absent from the
// engine boot table (pc_bbft.cpp kP2ChallengeStages carries only
// ch_NARI_01kusachi), so the boot selects no stage. This module carries the
// single pinned row plus a fail-closed lookup, mirroring the field layout
// of P2ChallengeStageRow read-only; it never modifies shared tables.
//
// Source facts (#534 P1 import contract, read-only):
//   cave_id ch_ABEM_tutorial, cave_path
//   user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt,
//   source_sha256 e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d,
//   table_order 0, ui_index 0, floors 2, floor_seconds [100.0, 100.0],
//   starting roster color 1 maturity 0 x50, legacy_time 0.0,
//   bitter_sprays 2, spicy_sprays 2, treasure_count_field 0.
//
// SERIALIZED integration (NOT done here): appending this row to
// pc_bbft.cpp kP2ChallengeStages and wiring the CMake target needs owner
// #186 review first (shared pc_bbft.cpp/CMakeLists.txt are owned by the
// #736 line). Specified as follow-on in
// docs/PIKMIN2_TUTORIAL_STAGE_TABLE_ROW.md. Nothing here claims gameplay
// acceptance.
//
// Engine-free boundary: this header and its .cpp compile with -Ipc_port
// only (cstddef/cstring/cstdio). No engine includes, no file I/O, no
// ledger writes.

namespace p2tutorialstage {

// One pinned retail stage row. Field order mirrors P2ChallengeStageRow.
struct TutorialStageRow {
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

// The single pinned ch_ABEM_tutorial row (ui 0). Pointer-stable.
const TutorialStageRow* tutorialRow();

// Fail-closed lookup by cave_id: null/empty/oversize/unknown refuses
// (nullptr) with no state change. Exact match only; the only known id is
// "ch_ABEM_tutorial".
const TutorialStageRow* tutorialLookup(const char* caveId);

// Field-by-field agreement of a row against the pinned values above.
// Used by the guarded fixture; no markers, no I/O.
bool tutorialRowMatches(const TutorialStageRow* row);

// Number of rows carried (exactly 1: this module never grows a table;
// multi-row boot tables stay with the engine owner).
std::size_t tutorialRowCount();

} // namespace p2tutorialstage
