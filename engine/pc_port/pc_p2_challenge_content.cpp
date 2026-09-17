// P2 challenge stage content wiring (lane kusachi-content-engine-wiring-native,
// #728; #186 review before shared-line landing).
//
// Engine-dependent half: registered into pc_bbft_update() via
// p2_challenge_content_set_hook (see the header for why the call is indirect).
// Linked ONLY into pikmin_pc (and the replacement fixture link once CMake
// membership lands via #725), never into pc_bbft_test.
//
// Each tick with a valid selected stage row: find the roster's nonzero color
// row, convert live squad pikis to that color through public Piki::setColor
// (validated, safe fallback), and count the bound content. Emits
// P2_CHALLENGE_CONTENT_WIRED. Test-only binding, labeled; never aborts the
// game (a dead captain only stops further binding for that tick).
#include "pc_p2_challenge_content.h"
#include "pc_p2_challenge_runtime.h"
#include "App.h"
#include "Node.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Creature.h"
#include "GameStat.h"
#include "gameflow.h"
#include "system.h"
#include "teki.h"
#include <cmath>
#include <cstdio>

namespace {

int sWired = 0;
int sTotal = 0;
int sTargetColor = -1;
int sTicks = 0;
int sMarks = 0;

int countSquadByColor(int color, int& total) {
    int matched = 0;
    total = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        ++total;
        if (p->mColor == color) ++matched;
    }
    return matched;
}

void bindSquadToColor(int color) {
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        if (p->mColor != color) p->setColor(color);
    }
}

void update() {
    static int frames = 0;
    ++frames;
    P2ChallengeStageParams params{};
    if (!p2_challenge_stage_params(params)) {
        return; // Silent inert path: no valid stage key selected.
    }
    if (!naviMgr || !tekiMgr || !pikiMgr) return;
    Navi* n = naviMgr->getNavi();
    if (!n) return;
    // NOTE: movie/pause gating lives in the fixture idle loop, not here; this
    // module only binds content and never alters run control.
    // Target color: first nonzero roster row (kusachi row 0 = blue).
    int target = -1;
    for (int c = 0; c < 7 && target < 0; ++c) {
        for (int h = 0; h < 3; ++h) {
            if (params.roster[c][h] > 0) { target = c; break; }
        }
    }
    if (target < 0) return;
    sTargetColor = target;
    // Test-only binding: convert live squad to the roster color through the
    // validated public setter, then count what is bound.
    bindSquadToColor(target);
    int total = 0;
    sWired = countSquadByColor(target, total);
    sTotal = total;
    ++sTicks;
    // Throttled marker (every 60 ticks) plus an immediate one on first bind.
    if (sTicks == 1 || (sTicks % 60) == 0) {
        std::printf("P2_CHALLENGE_CONTENT_WIRED wired=%d total=%d target_color=%d cave=%s\n",
                    sWired, sTotal, sTargetColor, params.caveId);
        std::fflush(stdout);
        ++sMarks;
        (void)sMarks;
    }
}

struct ContentRegistrar {
    ContentRegistrar() { p2_challenge_content_set_hook(&update); }
};
ContentRegistrar sContentRegistrar;

} // namespace

int p2_challenge_content_wired() { return sWired; }
