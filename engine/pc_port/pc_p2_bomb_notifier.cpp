// Port Bomb birth hook notifier (lane bomb-birth-hook-notifier-port-native,
// #715; #186 review before shared-line landing).
//
// Strong pc_p2_bomb_birth_hook_notify() for the engine weak hook. Called by
// generalEnemyMgr.cpp only from the Bomb/BombOtakara manager-create arms, so
// every call names a real Bomb-family birth. Records into a bounded ring
// (never grows) and prints the receipt marker. Engine-free; no gameplay
// state, no blast routing, no save/ledger effects (those belong to the #616
// provider and the integrator bridge, item 3, out of scope here).
#include "pc_p2_bomb_notifier.h"

#include <cstdio>

namespace {
constexpr int kRing = 16;
int sRing[kRing] = {};
int sCount = 0;
int sHead = 0;
int sLast = -1;
} // namespace

// __attribute__((used)): the engine references this ONLY through a weak
// symbol (generalEnemyMgr.cpp), which LTO does not count as a use. Without
// this, the linker garbage-collects the strong definition and the hook dangles
// null. Marked used so the weak resolves to this body in the engine link.
__attribute__((used)) void pc_p2_bomb_birth_hook_notify(int enemyID) {
    sRing[sHead] = enemyID;
    sHead = (sHead + 1) % kRing;
    ++sCount;
    sLast = enemyID;
    std::printf("P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=%d count=%d\n", enemyID, sCount);
    std::fflush(stdout);
}

int p2_bomb_notifier_count() { return sCount; }
int p2_bomb_notifier_last() { return sLast; }
void p2_bomb_notifier_reset() {
    sCount = 0;
    sHead = 0;
    sLast = -1;
    for (int i = 0; i < kRing; ++i) sRing[i] = 0;
}
