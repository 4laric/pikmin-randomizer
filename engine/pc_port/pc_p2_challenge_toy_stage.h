#pragma once
// Challenge 03toy stage table row + lookup (lane toy-stage-table-row-native, #752).
//
// Standalone boot-table row for ch_NARI_03toy, pinned from the #746 P0 source
// (issue #540 import lane, done+integrated). Engine-free by design: plain data
// + printf markers, no engine includes, no save-tree writes. This TU is NOT a
// member of any CMake target (serialized integration); the guarded fixture TU
// compiles it in as its single definition site. The pc_bbft.cpp table
// integration + CMakeLists membership are a specified follow-on owned by the
// #710/#736 line (blocked); they are NOT implemented here.
//
// Row transcribed read-only from the #540 import baseline:
// source user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt, ui_index 5,
// table_order 2, floors 2, timers [100.0, 150.0], roster total 100 at [2][2],
// sprays bitter 2 / spicy 2, legacy 0.0, treasure field 0.
#include <cstddef>

namespace p2toystage {

struct ToyStageRow {
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

// Resolve a stage key into the pinned row. Fail-closed: null/empty/oversize/
// unknown cave_id refuses with no marker and no state change.
bool lookupStage(const char* caveId, const ToyStageRow** out);

// Emit the resolution markers for a resolved row (exact probe lines).
void emitResolved(const ToyStageRow* row);

// Introspection for tests/diagnostics (no markers).
std::size_t rowCount();

} // namespace p2toystage
