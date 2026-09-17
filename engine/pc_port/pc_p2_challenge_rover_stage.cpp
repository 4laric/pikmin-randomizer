#include "pc_p2_challenge_rover_stage.h"

#include <cstdio>
#include <cstring>

namespace p2roverstage {
namespace {

const RoverStageRow kRoverRow = {
    "ch_MAT_route_rover",
    "user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt",
    "e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79",
    27,   // uiIndex
    21,   // tableOrder
    1,    // floors
    {90.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f},
    {{0, 0, 20}, {0, 0, 20}, {0, 0, 20},
     {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}},
    2,      // bitterSprays
    2,      // spicySprays
    300.0f, // legacyTime
    0,      // treasureCountField
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

const RoverStageRow* roverRow() {
    return &kRoverRow;
}

const RoverStageRow* roverLookup(const char* caveId) {
    if (!validKey(caveId, nullptr)) return nullptr;
    if (std::strcmp(caveId, kRoverRow.caveId) == 0) return &kRoverRow;
    return nullptr;
}

bool roverRowMatches(const RoverStageRow* row) {
    if (row == nullptr) return false;
    if (!sameString(row->caveId, kRoverRow.caveId)) return false;
    if (!sameString(row->cavePath, kRoverRow.cavePath)) return false;
    if (!sameString(row->sourceSha256, kRoverRow.sourceSha256)) return false;
    if (row->uiIndex != kRoverRow.uiIndex) return false;
    if (row->tableOrder != kRoverRow.tableOrder) return false;
    if (row->floors != kRoverRow.floors) return false;
    for (int i = 0; i < 8; ++i) {
        if (row->floorSeconds[i] != kRoverRow.floorSeconds[i]) return false;
    }
    for (int c = 0; c < 7; ++c) {
        for (int m = 0; m < 3; ++m) {
            if (row->roster[c][m] != kRoverRow.roster[c][m]) return false;
        }
    }
    if (row->bitterSprays != kRoverRow.bitterSprays) return false;
    if (row->spicySprays != kRoverRow.spicySprays) return false;
    if (row->legacyTime != kRoverRow.legacyTime) return false;
    if (row->treasureCountField != kRoverRow.treasureCountField) return false;
    return true;
}

std::size_t roverRowCount() {
    return 1;
}

} // namespace p2roverstage
