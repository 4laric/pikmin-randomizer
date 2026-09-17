#pragma once
// Challenge persistence anchors + score + marker emission (#713).
//
// Implements the native side of the #708 key/marker contract
// (p2-challenge-persistence-wiring-v1, read-only input; never duplicated
// here): per-stage save anchors for the 30 pinned retail challenge stages,
// result-screen score computation, and the exact 7 probe markers per stage
// run. Engine-free by design: plain data + printf markers, no engine
// includes, no save-tree writes. A future engine call site (owned by #710
// with #186 review; NOT this lane) will drive record*() from the P1
// challenge result path; until then the guarded fixture TU is the only
// caller.
//
// Stage table transcribed read-only from the #708 adapter STAGES
// (decoded retail user/Matoba/challenge/stages.txt, ui 0..29, zero
// inventory mismatches). Key scheme mirrors the #708 formula verbatim:
// p2_challenge_{save,load,clear,highscore,unlock}_{cave_id}.
// Score mirrors the #651 host-mode selectByUiIndex precedent consumed
// read-only: score = pokos*10 + floor(timeLeftSeconds) + population*10.
// Markers mirror the #708 stems verbatim: P2_CHALLENGE_{SAVE_KEY,LOAD_KEY,
// CLEAR,HIGHSCORE,UNLOCK,RECEIPT_DEDUP,REENTRY} stage=<cave_id>, one per
// line, nothing else on the line (the downstream #561 probe counts exact
// marker lines).
#include <cstddef>

namespace p2challengepersist {

// One pinned retail stage row.
struct StageRow {
    const char* caveId;
    int uiIndex;
    int floors;
};

// Per-stage save anchors (the PlayCommonData clear-flag/highscore/unlock
// anchors of the #708 NATIVE_HOOKUP, held here as fixture-scoped data until
// the #710 engine call site lands; never persisted to disk by this module).
struct StageAnchors {
    char caveId[64];
    int uiIndex;
    int floors;
    char saveKey[128];
    char loadKey[128];
    char clearKey[128];
    char highKey[128];
    char unlockKey[128];
    bool cleared;
    int highscore;
    bool unlocked;
    bool saveSeen;
    bool loadSeen;
    int receiptCount;
    int lastReceiptId;
    int dedupHits;
    bool reentered;
};

// Result-screen score. Precondition: non-negative inputs; returns -1 refused
// otherwise. Mirrors #651 host-mode score() read-only.
int compute_score(int pokos, double timeLeftSeconds, int population);

// Resolve a stage key into anchors. Fail-closed: null/empty/oversize/unknown
// cave_id, or a null out-pointer, refuses with no marker and no state change.
bool selectStage(const char* caveId, StageAnchors* out);

// Session recorders. Each mutates only its own anchor field(s), then emits
// exactly its marker line. Any refusal prints one
// P2_CHALLENGE_PERSISTENCE_REFUSED line and changes nothing.
bool recordSave(StageAnchors* anchors);
bool recordLoad(StageAnchors* anchors);
bool recordClear(StageAnchors* anchors);
bool recordHighscore(StageAnchors* anchors, int pokos, double timeLeftSeconds, int population);
bool recordUnlock(StageAnchors* anchors);
bool recordReceipt(StageAnchors* anchors, int receiptId);
bool recordReentry(StageAnchors* anchors);

// Introspection for tests/diagnostics (no markers).
std::size_t stageCount();
const StageRow* stageAt(std::size_t index);

} // namespace p2challengepersist
