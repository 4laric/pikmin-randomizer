// P2 challenge host-mode engine runtime bridge (lane
// challenge-hostmode-engine-hook-native, #710; #186 review before any
// shared-line landing).
//
// Engine-dependent half of the bridge: registered into pc_bbft_update() via
// p2_challenge_runtime_set_hook (see the header for why the call is indirect).
// Linked ONLY into pikmin_pc (and the replacement fixture link), never into
// pc_bbft_test. Reads live squad/captain/clock facts, binds the selected row
// to the landed HostState/StageEntry, and drives
// p2challenge::wiring::syncTick. Emits P2_CHALLENGE_MODE_BOOT on bind, then
// the wiring tick stream, then P2_CHALLENGE_MODE_DONE once on end.
//
// The bridge NEVER aborts the game: a dead captain ends the HostState with
// "captain_down" and the bridge goes inert. CAPTAIN_DOWN + BLOCKED exit is
// fixture behavior (the replacement fixture adopts the #632 guard); the
// engine path only records. No invented values: every runtime-varying field
// comes from the engine; red composition is not tracked and stays 0 with the
// constraint documented at the call site.
#include "pc_p2_challenge_runtime.h"
#include "pc_p2_challenge_mode.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "Generator.h"
#include "Section.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Collision.h"
#include "Creature.h"
#include "MoviePlayer.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include "pc_p2_species.h"
#include "teki.h"
#include <cmath>
#include <cstdio>

namespace {

bool sStarted = false;
bool sDone = false;
int sWaitMarks = 0;
int sTicks = 0;
p2challenge::StageEntry sEntry{};
p2challenge::HostState sState{};

int countSquad(int& reds) {
    int alive = 0;
    reds = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        ++alive;
        if (pc_p2_has_red_immunity(p)) ++reds;
    }
    return alive;
}

void waitMark(const char* reason, int frames) {
    if (frames % 600 == 0 && sWaitMarks < 48) {
        ++sWaitMarks;
        std::printf("P2_CHALLENGE_MODE_WAIT reason=%s frames=%d\n", reason, frames);
        std::fflush(stdout);
    }
}

void update() {
    static int frames = 0;
    ++frames;
    P2ChallengeStageParams params{};
    if (!p2_challenge_stage_params(params)) {
        return; // Silent inert path: no valid stage key selected.
    }
    if (!naviMgr || !tekiMgr || !pikiMgr) {
        waitMark("no-managers", frames);
        return;
    }
    Navi* n = naviMgr->getNavi();
    if (!n) {
        waitMark("no-navi", frames);
        return;
    }
    // Engine bridge only records; it never aborts the game on captain-down.
    const bool deadState = !n->isAlive();
    if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) return;
    if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return;
    int reds = 0;
    const int alive = countSquad(reds);
    if (!sStarted) {
        // A stage entry requires a live squad; without one there is nothing
        // to deliver and the bridge keeps waiting (fail closed).
        if (alive <= 0) {
            waitMark("no-squad", frames);
            return;
        }
        sEntry.caveId = params.caveId;
        sEntry.uiIndex = params.uiIndex;
        sEntry.floorCount = params.floors;
        for (int i = 0; i < 8; ++i) sEntry.floorSeconds[i] = params.floorSeconds[i];
        for (int c = 0; c < 7; ++c)
            for (int h = 0; h < 3; ++h) sEntry.roster[c][h] = params.roster[c][h];
        sEntry.bitterSprays = params.bitterSprays;
        sEntry.spicySprays = params.spicySprays;
        sState = p2challenge::start(sEntry);
        p2challenge::applySquadAndSprays(sState, params.bitterSprays, params.spicySprays);
        p2challenge::emit("BOOT", sState);
        sStarted = true;
        return;
    }
    if (sDone) return;
    float seconds = gsys ? gsys->getFrameTime() : 0.0f;
    if (!(seconds >= 0.0f) || !std::isfinite(seconds) || seconds > 0.5f) seconds = 0.0f;
    p2challenge::wiring::LiveFacts facts;
    facts.squad_alive = alive;
    facts.squad_reds = reds;
    facts.captain_down = GameStat::orimaDead || deadState || !std::isfinite(n->mHealth)
        || n->mHealth <= 1.0f;
    facts.seconds = seconds;
    ++sTicks;
    if (!p2challenge::wiring::syncTick(sState, facts)) {
        if (sState.ended) {
            p2challenge::emit("DONE", sState);
        }
        sDone = true;
    }
}

struct BridgeRegistrar {
    BridgeRegistrar() { p2_challenge_runtime_set_hook(&update); }
};
BridgeRegistrar sBridgeRegistrar;

} // namespace
