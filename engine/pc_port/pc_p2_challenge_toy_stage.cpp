#include "pc_p2_challenge_toy_stage.h"

#include <cstdio>
#include <cstring>

namespace p2toystage {
namespace {

// Pinned ch_NARI_03toy row (transcribed read-only from the #540 baseline).
const ToyStageRow kToyRow = {
    "ch_NARI_03toy",
    "user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt",
    "d74b49ac3d9a2388288b9cb868dd8717ff893fd522453b309740519be841f03c",
    5, 2, 2,
    {100.0f, 150.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f},
    {{0, 0, 0}, {0, 0, 0}, {0, 0, 100}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}},
    2, 2, 0.0f, 0,
};

bool validCaveId(const char* caveId, std::size_t* lengthOut) {
    if (caveId == nullptr) return false;
    std::size_t len = std::strlen(caveId);
    if (len == 0 || len >= 64) return false;
    for (std::size_t i = 0; i < len; ++i) {
        const char c = caveId[i];
        const bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                        (c >= '0' && c <= '9') || c == '_';
        if (!ok) return false;
    }
    if (lengthOut != nullptr) *lengthOut = len;
    return true;
}

void refuse(const char* reason) {
    std::printf("P2_TOY_STAGE_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
}

} // namespace

bool lookupStage(const char* caveId, const ToyStageRow** out) {
    if (out == nullptr || !validCaveId(caveId, nullptr)) {
        refuse("bad-stage-key");
        return false;
    }
    if (std::strcmp(kToyRow.caveId, caveId) != 0) {
        refuse("unknown-stage");
        return false;
    }
    *out = &kToyRow;
    std::printf("P2_TOY_STAGE_TABLE stage=%s ui_index=%d floors=%d\n",
                kToyRow.caveId, kToyRow.uiIndex, kToyRow.floors);
    std::fflush(stdout);
    return true;
}

void emitResolved(const ToyStageRow* row) {
    if (row == nullptr) {
        refuse("no-row");
        return;
    }
    int total = 0;
    for (int c = 0; c < 7; ++c)
        for (int h = 0; h < 3; ++h) total += row->roster[c][h];
    std::printf("P2_TOY_STAGE_RESOLVED stage=%s ui_index=%d floors=%d roster_total=%d\n",
                row->caveId, row->uiIndex, row->floors, total);
    std::fflush(stdout);
}

std::size_t rowCount() {
    return 1;
}

} // namespace p2toystage
