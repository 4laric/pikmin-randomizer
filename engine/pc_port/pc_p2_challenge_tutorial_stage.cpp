#include "pc_p2_challenge_tutorial_stage.h"

#include <cstdio>
#include <cstring>

namespace p2tutorialstage {
namespace {

const TutorialStageRow kTutorialRow = {
    "ch_ABEM_tutorial",
    "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt",
    "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d",
    0,    // uiIndex
    0,    // tableOrder
    2,    // floors
    {100.0f, 100.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f},
    {{0, 0, 0}, {50, 0, 0},
     {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}},
    2,    // bitterSprays
    2,    // spicySprays
    0.0f, // legacyTime
    0,    // treasureCountField
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

const TutorialStageRow* tutorialRow() {
    return &kTutorialRow;
}

const TutorialStageRow* tutorialLookup(const char* caveId) {
    if (!validKey(caveId, nullptr)) return nullptr;
    if (std::strcmp(caveId, kTutorialRow.caveId) == 0) return &kTutorialRow;
    return nullptr;
}

bool tutorialRowMatches(const TutorialStageRow* row) {
    if (row == nullptr) return false;
    if (!sameString(row->caveId, kTutorialRow.caveId)) return false;
    if (!sameString(row->cavePath, kTutorialRow.cavePath)) return false;
    if (!sameString(row->sourceSha256, kTutorialRow.sourceSha256)) return false;
    if (row->uiIndex != kTutorialRow.uiIndex) return false;
    if (row->tableOrder != kTutorialRow.tableOrder) return false;
    if (row->floors != kTutorialRow.floors) return false;
    for (int i = 0; i < 8; ++i) {
        if (row->floorSeconds[i] != kTutorialRow.floorSeconds[i]) return false;
    }
    for (int c = 0; c < 7; ++c) {
        for (int m = 0; m < 3; ++m) {
            if (row->roster[c][m] != kTutorialRow.roster[c][m]) return false;
        }
    }
    if (row->bitterSprays != kTutorialRow.bitterSprays) return false;
    if (row->spicySprays != kTutorialRow.spicySprays) return false;
    if (row->legacyTime != kTutorialRow.legacyTime) return false;
    if (row->treasureCountField != kTutorialRow.treasureCountField) return false;
    return true;
}

std::size_t tutorialRowCount() {
    return 1;
}

} // namespace p2tutorialstage
