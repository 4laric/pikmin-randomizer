#pragma once

#include <cstddef>

// Pinned leafchappy challenge stage row for the #550 consumer
// (issue #774, lane challenge-2-leafchappy-bridge-row).
//
// ch_ABEM_LeafChappy (P2 Challenge 06, ui_index 17) is absent from the
// engine boot table (which at the pinned base carries no challenge stage
// rows at all), so the boot selects no stage. This module carries the
// single pinned row plus a fail-closed lookup, mirroring the field layout
// of P2ChallengeStageRow read-only; it never modifies shared tables.
//
// Source facts (lane-plan contract, read-only):
//   cave_id ch_ABEM_LeafChappy, cave_path
//   user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt,
//   source_sha256 49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf,
//   table_order 4, ui_index 17, floors 2, floor_seconds [85.0, 100.0],
//   starting roster colors 0-2 maturity 0 x10 each, legacy_time 400.0,
//   bitter_sprays 1, spicy_sprays 1, treasure_count_field 11.
//
// SERIALIZED integration (NOT done here): appending this row to
// pc_bbft.cpp kP2ChallengeStages and wiring the CMake target needs owner
// #186 review first. Specified as follow-on in
// docs/PIKMIN2_LEAFCHAPPY_STAGE_TABLE_ROW.md. Nothing here claims gameplay
// acceptance.
//
// Engine-free boundary: this header and its .cpp compile with -Ipc_port
// only (cstddef/cstring/cstdio). No engine includes, no file I/O, no
// ledger writes.

namespace p2leafchappystage {

// One pinned retail stage row. Field order mirrors P2ChallengeStageRow.
struct LeafchappyStageRow {
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

// The single pinned ch_ABEM_LeafChappy row (ui 17). Pointer-stable.
const LeafchappyStageRow* leafchappyRow();

// Fail-closed lookup by cave_id: null/empty/oversize/unknown refuses
// (nullptr) with no state change. Exact match only; the only known id is
// "ch_ABEM_LeafChappy".
const LeafchappyStageRow* leafchappyLookup(const char* caveId);

// Field-by-field agreement of a row against the pinned values above.
// Used by the guarded fixture; no markers, no I/O.
bool leafchappyRowMatches(const LeafchappyStageRow* row);

// Number of rows carried (exactly 1: this module never grows a table;
// multi-row boot tables stay with the engine owner).
std::size_t leafchappyRowCount();

} // namespace p2leafchappystage
