#include "pc_p2_challenge_persistence.h"

#include <cstdio>
#include <cstring>

namespace p2challengepersist {
namespace {

// Stage table transcribed read-only from the #708 adapter STAGES (retail
// table order; ui_index covers 0..29 exactly; zero inventory mismatches).
const StageRow kStages[] = {
    {"ch_ABEM_tutorial", 0, 2},
    {"ch_NARI_07whitepurple", 20, 2},
    {"ch_NARI_03toy", 5, 2},
    {"ch_NARI_01kusachi", 3, 1},
    {"ch_ABEM_LeafChappy", 17, 2},
    {"ch_NARI_05start3easy", 15, 2},
    {"ch_MUKI_metal", 1, 2},
    {"ch_MAT_limited_time", 11, 1},
    {"ch_MAT_t_hunter_hana", 14, 1},
    {"ch_MUKI_damagumo", 6, 1},
    {"ch_MAT_t_hunter_enemy", 10, 5},
    {"ch_MAT_conc_cave", 2, 3},
    {"ch_NARI_04series", 12, 7},
    {"ch_MAT_t_hunter_otakara", 23, 1},
    {"ch_MUKI_bigfoot", 7, 1},
    {"ch_MIYA_oopan", 21, 1},
    {"ch_MAT_yellow_purple_white", 19, 1},
    {"ch_MUKI_redblue", 18, 2},
    {"ch_NARI_08tobasare", 24, 2},
    {"ch_NARI_02tile", 4, 2},
    {"ch_MAT_crawler", 29, 2},
    {"ch_MAT_route_rover", 27, 1},
    {"ch_MUKI_enemyzero", 13, 1},
    {"ch_NARI_09suikomi", 25, 1},
    {"ch_MUKI_houdai", 8, 2},
    {"ch_NARI_06start3hard", 16, 3},
    {"ch_MAT_flier", 28, 1},
    {"ch_MIYA_trap", 26, 1},
    {"ch_MUKI_bombing", 22, 1},
    {"ch_MUKI_king", 9, 5},
};

bool validKeyChar(char c) {
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
           (c >= '0' && c <= '9') || c == '_';
}

bool validCaveId(const char* caveId, std::size_t* lengthOut) {
    if (caveId == nullptr) return false;
    std::size_t len = std::strlen(caveId);
    if (len == 0 || len >= sizeof(StageAnchors::caveId)) return false;
    for (std::size_t i = 0; i < len; ++i) {
        if (!validKeyChar(caveId[i])) return false;
    }
    if (lengthOut != nullptr) *lengthOut = len;
    return true;
}

const StageRow* findRow(const char* caveId) {
    for (std::size_t i = 0; i < sizeof(kStages) / sizeof(kStages[0]); ++i) {
        if (std::strcmp(kStages[i].caveId, caveId) == 0) return &kStages[i];
    }
    return nullptr;
}

void emit(const char* stem, const char* caveId) {
    // Exact probe line: P2_CHALLENGE_<STEM> stage=<cave_id>, nothing else.
    std::printf("P2_CHALLENGE_%s stage=%s\n", stem, caveId);
    std::fflush(stdout);
}

void refuse(const char* reason) {
    std::printf("P2_CHALLENGE_PERSISTENCE_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
}

} // namespace

int compute_score(int pokos, double timeLeftSeconds, int population) {
    if (pokos < 0 || population < 0 || !(timeLeftSeconds >= 0.0)) return -1;
    return pokos * 10 + static_cast<int>(timeLeftSeconds) + population * 10;
}

bool selectStage(const char* caveId, StageAnchors* out) {
    if (out == nullptr || !validCaveId(caveId, nullptr)) {
        refuse("bad-stage-key");
        return false;
    }
    const StageRow* row = findRow(caveId);
    if (row == nullptr) {
        refuse("unknown-stage");
        return false;
    }
    std::memset(out, 0, sizeof(*out));
    std::strncpy(out->caveId, row->caveId, sizeof(out->caveId) - 1);
    out->uiIndex = row->uiIndex;
    out->floors = row->floors;
    std::snprintf(out->saveKey, sizeof(out->saveKey), "p2_challenge_save_%s", row->caveId);
    std::snprintf(out->loadKey, sizeof(out->loadKey), "p2_challenge_load_%s", row->caveId);
    std::snprintf(out->clearKey, sizeof(out->clearKey), "p2_challenge_clear_%s", row->caveId);
    std::snprintf(out->highKey, sizeof(out->highKey), "p2_challenge_highscore_%s", row->caveId);
    std::snprintf(out->unlockKey, sizeof(out->unlockKey), "p2_challenge_unlock_%s", row->caveId);
    out->lastReceiptId = -1;
    return true;
}

bool recordSave(StageAnchors* anchors) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    anchors->saveSeen = true;
    emit("SAVE_KEY", anchors->caveId);
    return true;
}

bool recordLoad(StageAnchors* anchors) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    anchors->loadSeen = true;
    emit("LOAD_KEY", anchors->caveId);
    return true;
}

bool recordClear(StageAnchors* anchors) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    anchors->cleared = true;
    emit("CLEAR", anchors->caveId);
    return true;
}

bool recordHighscore(StageAnchors* anchors, int pokos, double timeLeftSeconds, int population) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    const int score = compute_score(pokos, timeLeftSeconds, population);
    if (score < 0) {
        refuse("bad-score-input");
        return false;
    }
    anchors->highscore = score;
    emit("HIGHSCORE", anchors->caveId);
    return true;
}

bool recordUnlock(StageAnchors* anchors) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    anchors->unlocked = true;
    emit("UNLOCK", anchors->caveId);
    return true;
}

bool recordReceipt(StageAnchors* anchors, int receiptId) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    if (receiptId < 0) {
        refuse("bad-receipt-id");
        return false;
    }
    if (receiptId == anchors->lastReceiptId) {
        ++anchors->dedupHits;
    } else {
        ++anchors->receiptCount;
        anchors->lastReceiptId = receiptId;
    }
    emit("RECEIPT_DEDUP", anchors->caveId);
    return true;
}

bool recordReentry(StageAnchors* anchors) {
    if (anchors == nullptr || anchors->caveId[0] == '\0') {
        refuse("no-stage");
        return false;
    }
    anchors->reentered = true;
    emit("REENTRY", anchors->caveId);
    return true;
}

std::size_t stageCount() {
    return sizeof(kStages) / sizeof(kStages[0]);
}

const StageRow* stageAt(std::size_t index) {
    if (index >= stageCount()) return nullptr;
    return &kStages[index];
}

} // namespace p2challengepersist
