#include "pc_p2_challenge_leafchappy_stage.h"

#include <cstdio>
#include <cstring>

namespace p2leafchappystage {
namespace {

const LeafchappyStageRow kLeafchappyRow = {
    "ch_ABEM_LeafChappy",
    "user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt",
    "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf",
    17,   // uiIndex
    4,    // tableOrder
    2,    // floors
    {85.0f, 100.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f},
    {{10, 0, 0}, {10, 0, 0}, {10, 0, 0},
     {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}},
    1,      // bitterSprays
    1,      // spicySprays
    400.0f, // legacyTime
    11,     // treasureCountField
};

bool validKey(const char* caveId, std::size_t* lengthOut) {
    if (caveId == nullptr) return false;
    std::size_t len = std::strlen(caveId);
    if (len == 0 || len >= 64) return false;
    for (std::size_t i = 0; i < len; ++i) {
        char c = caveId[i];
        bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                  (c >= '0' && c <= '9') || c == '_';
        if (!ok) return false;
    }
    if (lengthOut != nullptr) *lengthOut = len;
    return true;
}

bool sameString(const char* a, const char* b) {
    if (a == nullptr || b == nullptr) return false;
    return std::strcmp(a, b) == 0;
}

} // namespace

const LeafchappyStageRow* leafchappyRow() {
    return &kLeafchappyRow;
}

const LeafchappyStageRow* leafchappyLookup(const char* caveId) {
    if (!validKey(caveId, nullptr)) return nullptr;
    if (std::strcmp(caveId, kLeafchappyRow.caveId) == 0) return &kLeafchappyRow;
    return nullptr;
}

bool leafchappyRowMatches(const LeafchappyStageRow* row) {
    if (row == nullptr) return false;
    if (!sameString(row->caveId, kLeafchappyRow.caveId)) return false;
    if (!sameString(row->cavePath, kLeafchappyRow.cavePath)) return false;
    if (!sameString(row->sourceSha256, kLeafchappyRow.sourceSha256)) return false;
    if (row->uiIndex != kLeafchappyRow.uiIndex) return false;
    if (row->tableOrder != kLeafchappyRow.tableOrder) return false;
    if (row->floors != kLeafchappyRow.floors) return false;
    for (int i = 0; i < 8; ++i) {
        if (row->floorSeconds[i] != kLeafchappyRow.floorSeconds[i]) return false;
    }
    for (int c = 0; c < 7; ++c) {
        for (int m = 0; m < 3; ++m) {
            if (row->roster[c][m] != kLeafchappyRow.roster[c][m]) return false;
        }
    }
    if (row->bitterSprays != kLeafchappyRow.bitterSprays) return false;
    if (row->spicySprays != kLeafchappyRow.spicySprays) return false;
    if (row->legacyTime != kLeafchappyRow.legacyTime) return false;
    if (row->treasureCountField != kLeafchappyRow.treasureCountField) return false;
    return true;
}

std::size_t leafchappyRowCount() {
    return 1;
}

} // namespace p2leafchappystage
