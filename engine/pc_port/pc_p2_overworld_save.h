#pragma once
#include <cstddef>

// Overworld session save serializer (#736).
//
// Real engine save/load for an overworld session record (area tag, day,
// live squad census, highscore and unlock anchors) with deterministic output
// and strict, size-guarded, fail-closed parsing, per the #712 round-trip and
// size-guard rules. No invented values: the squad census is counted live from
// pikiMgr; area/day/highscore/unlock come only from explicit fixture context
// (setContext), never from defaults presented as observations.
//
// Fail-closed: any malformed input, oversize file, out-of-range field, census
// mismatch or round-trip inequality is refused with a marker and never
// produces a supported state. Absence of context or managers can never
// satisfy supported().
//
// The #573/#150 yakushima consumer calls setContext() with its session
// identity, then collectLiveSession() + verifyRoundTrip() (or the
// once-per-boot pc_p2_overworld_save_poll() driven from pc_bbft_update).
// New files only; no shared-hook changes beyond the documented pc_bbft.cpp
// call site (weak-linked so pc_bbft_test stays inert).
namespace p2overworldsave {

// Live squad census buckets by raw Piki mColor value; `other` counts alive
// Pikmin whose color falls outside [0,7] so total == sum(buckets)+other.
struct Session {
    char area[64];
    int day;
    int squad[8];
    int other;
    int total;
    int highscore;
    int unlocked;
};

bool validSession(const Session& s);
bool sessionEqual(const Session& a, const Session& b);

// Explicit fixture context (validated on set; required before collect).
bool setContext(const char* area, int day, int highscore, int unlocked);
bool hasContext();

// Count the live squad from pikiMgr into out (context must be set first).
bool collectLiveSession(Session& out);

// Strict file round-trip with size guard; emits SAVED/LOADED markers.
bool saveSession(const char* path, const Session& s);
bool loadSession(const char* path, Session& out, size_t maxBytes);

// Save, load and compare; emits SUPPORTED on success, REFUSED otherwise.
bool verifyRoundTrip(const char* path, const Session& s);

// Observation queries (read-only, no state change).
bool supported();
const char* lastPath();

void reset();
} // namespace p2overworldsave

// Once-per-boot session save+verify for the pc_bbft_update session path.
// No-op unless explicit context was set, so production runs that never set
// context perform no file I/O. Weak-linked from pc_bbft.cpp.
void pc_p2_overworld_save_poll();
