#pragma once
// Pinned ch_MUKI_damagumo stage row + lookup for the P1 boot (#742).
//
// Disjoint new files: this header mirrors the engine P2ChallengeStageRow
// shape (pc_port/pc_bbft.cpp, lane #675) field-for-field so the fixture can
// prove resolution without touching shared code. Values pinned from #740
// source: 1 floor, 150 s, 50 leaf (native color 2/maturity 2), bitter 0 /
// spicy 1, legacy 0.0, treasure field 0, ui 6, table order 9, source sha256
// c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e.
// SERIALIZED: landing this row into the engine table (pc_bbft.cpp) and the
// CMake membership are a follow-on requiring #186 review (not done here).

struct P2DamagumoStageRow {
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

// The single pinned row. Never mutated at runtime.
const P2DamagumoStageRow& p2_damagumo_stage_row();

// Lookup by exact cave id. Returns nullptr for anything else, including
// null (fail-closed; unknown stages are never treated as damagumo).
const P2DamagumoStageRow* p2_damagumo_stage_lookup(const char* caveId);
