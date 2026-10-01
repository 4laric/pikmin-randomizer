#pragma once
// Captain-less Pikmin after a P2 capture (#972 crash follow-up). Engine-free.
//
// A P2 captor (Jellyfloat suction, Sarai, ...) takes a Pikmin through the
// captain seam, which clears Piki::mNavi; a released Pikmin stays captain-less
// until a whistle reclaims it (Navi::callPikis sets mNavi first). P1 code that
// assumes every Pikmin has a captain then read the null pointer:
//   - Piki::changeMode(FormationMode) initialises ActCrowd with mNavi
//     (access violation reading 0x9c, ActCrowd::init);
//   - a captain's pending grab turned the captured Pikmin into PikiHangedState,
//     whose exec reads mNavi's current state (access violation reading 0xdd0).
// The rulings: no captain means no party (free mode) and nothing to hang from.
namespace p2captivenavi {

// PikiMode ids (include/Piki.h): FreeMode = 0, FormationMode = 1.
constexpr int kFreeMode = 0;
constexpr int kFormationMode = 1;

// The mode Piki::changeMode actually enters.
inline int modeFor(int requested, bool hasCaptain)
{
    return requested == kFormationMode && !hasCaptain ? kFreeMode : requested;
}

// Whether a captain may keep a Pikmin it picked to throw (held or pending).
inline bool keepThrowPick(bool pickHasCaptain) { return pickHasCaptain; }

// Whether a Pikmin in a hang state (GoHang/Hanged/WaterHanged) may stay in it.
inline bool mayHang(bool hasCaptain) { return hasCaptain; }

// One log line per guard kind per process (evidence that a guard fired).
inline void note(const char* kind);

} // namespace p2captivenavi

#include <cstdio>
inline void p2captivenavi::note(const char* kind)
{
    static int logged = 0;
    if (logged >= 16) return;
    ++logged;
    std::printf("P2_CAPTIVE_NAVI_GUARD kind=%s\n", kind);
    std::fflush(stdout);
}
