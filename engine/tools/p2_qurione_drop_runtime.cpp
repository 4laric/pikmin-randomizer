// Private real-GL cleanup/re-entry fixture (lane 15, Honeywisp EnemyID 16).
//
// It drives the wisp through TWO appear cycles in one session and then lets the
// natural Pikmin-contact drop kill it:
//   1. on active Walk it parks the 20 reds far away and moves the captain near
//      the wisp, so cycle 1 (appear -> move -> disappear -> stay) cannot drop;
//   2. when the wisp is stationary again it repositions one red at the wisp's
//      XZ, so nearestTarget (SIGHT 200) fires a SECOND appear;
//   3. that nearby red then trips pikiContact (< HIT_RADIUS 30) on the second
//      Move frame -> Drop -> Dead -> Egg release/break -> death.
// The lane-07 forget seam prints P2_QURIONE_FORGET when the actor is unbound.
// No health is written anywhere; all P2_QURIONE_* markers come from production.
#include <SDL2/SDL.h>
#include "App.h"
#include "Node.h"
#include "Generator.h"
#include "MapMgr.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "GlobalGameOptions.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_preview.h"
#include "teki.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include "gameflow.h"
#include <cstdio>
#include <cstdlib>

namespace {
void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL QURIONE_DROP %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

class QurioneDropApp final : public PlugPikiApp {
    enum Phase { SETTLE, CYCLE1, CYCLE2, DONE };
    int frames = 0;
    Phase phase = SETTLE;
    bool sawMove = false;
public:
    Teki* findWisp() {
        Iterator tit(tekiMgr); CI_LOOP(tit) {
            Teki* t = static_cast<Teki*>(*tit);
            if (t && t->mTekiType == TEKI_Qurione && t->mGenerator && t->mGenerator->_70 == 203001u) return t;
        }
        return nullptr;
    }
    Piki* findRed() {
        Iterator pit(pikiMgr); CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit);
            if (p && p->isAlive() && p->mColor == Red) return p;
        }
        return nullptr;
    }
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 2400, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_pikipelago_room_preview() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        Navi* n = naviMgr->getNavi();

        if (phase == SETTLE) {
            // Park every red at the far ufo-goal so cycle 1 cannot drop. The
            // goal is valid terrain (the earlier off-map z=-180 spot fell out of
            // the map, extinguished the squad and ended the day).
            Iterator pit(pikiMgr); CI_LOOP(pit) {
                Piki* p = static_cast<Piki*>(*pit);
                if (p && p->isAlive()) {
                    p->resetPosition(Vector3f(206.0f, mapMgr->getMinY(206.0f, 1858.0f, true), 1858.0f));
                }
            }
            n->resetPosition(Vector3f(-104.0f, mapMgr->getMinY(-104.0f, 1816.0f, true), 1816.0f));
            std::printf("P2_QURIONE_SETTLE reds_parked=1 captain_near=1\n");
            std::fflush(stdout);
            phase = CYCLE1;
            return result;
        }
        if (phase == DONE) return result;

        Teki* wisp = findWisp();
        if (!wisp) { phase = DONE; return result; }
        const float speed = wisp->mVelocity.length();

        if (phase == CYCLE1) {
            if (speed > 20.0f) sawMove = true;
            if (sawMove && speed < 1.0f) {
                // cycle 1 complete, wisp back in Stay. Put one red at its XZ so
                // nearestTarget re-triggers a second appear.
                Piki* red = findRed();
                require(red != nullptr, "no red for re-appear trigger");
                const Vector3f p = wisp->mSRT.t;
                red->resetPosition(Vector3f(p.x, mapMgr->getMinY(p.x, p.z, true), p.z));
                std::printf("P2_QURIONE_REAPPEAR_TRIGGER pos=(%.2f,%.2f,%.2f)\n", p.x, p.y, p.z);
                std::fflush(stdout);
                phase = CYCLE2;
            }
        } else if (phase == CYCLE2) {
            if (speed > 20.0f) {
                std::printf("P2_QURIONE_SECOND_MOVE pos=(%.2f,%.2f,%.2f)\n",
                            wisp->mSRT.t.x, wisp->mSRT.t.y, wisp->mSRT.t.z);
                std::fflush(stdout);
                phase = DONE;  // let the nearby red finish drop -> dead -> forget
            }
        }
        return result;
    }
};
}

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    if (!pc_window_init("P2 Qurione cleanup fixture", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new QurioneDropApp());
    return 0;
}
