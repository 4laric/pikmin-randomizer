#pragma once
// P2 challenge stage extension table: LeafChappy + 02tile (lane
// challenge-stage-table-extension-native, issue #730).
//
// The engine kP2ChallengeStages table (pc_port/pc_bbft.cpp, lane #675) holds
// only ch_NARI_01kusachi, so neither ch_ABEM_LeafChappy (#550) nor
// ch_NARI_02tile (#537) can resolve. This additive extension table carries
// exactly those two rows, pinned from docs/PIKMIN_CONTENT_IMPORT_LANES.json
// and the family issues, plus a lookup. It never touches the engine table:
// wiring it in is the serialized one-line pc_bbft.cpp integration owned by
// READY #728 (see docs/PIKMIN2_CHALLENGE_STAGE_TABLE_EXTENSION.md).
// Engine-free (only <cstddef>); safe in every target.
#include <cstddef>

struct P2ChallengeStageExtRow {
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

// Number of rows in the extension table (exactly 2: LeafChappy, 02tile).
std::size_t pc_p2_challenge_stages_ext_count();

// Lookup by cave_id. Returns null for unknown keys (including kusachi: the
// engine table owns kusachi and this table must never shadow it).
const P2ChallengeStageExtRow* pc_p2_challenge_stages_ext_lookup(const char* caveId);
