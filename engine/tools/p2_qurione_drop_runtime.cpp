// Private real-GL drop fixture (lane 15, Honeywisp EnemyID 16). Throws a red
// Pikmin at the bound wisp so the natural flyCollisionCallBack proxy
// (pc_p2_qurione pikiContact, an XZ < HIT_RADIUS proximity test) fires
// Drop -> Dead -> Egg release/break/birth with no health write. The wisp's
// lifecycle markers (P2_QURIONE_*) are printed by the production module and
// captured by the outer runner; this fixture only performs the throw.
#include <SDL2/SDL.h>
#include "App.h"
#include "Node.h"
#include "Generator.h"
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
    int frames = 0;
    bool thrown = false;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 2100, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll) return result;
        Navi* n = naviMgr->getNavi();
        const bool captainReady = n->getCurrState() && n->getCurrState()->getID() == NAVISTATE_Walk;
        if (!captainReady || thrown) return result;
        Teki* wisp = nullptr;
        Iterator tit(tekiMgr); CI_LOOP(tit) {
            Teki* t = static_cast<Teki*>(*tit);
            if (t && t->mTekiType == TEKI_Qurione && t->mGenerator && t->mGenerator->_70 == 203001u) { wisp = t; break; }
        }
        Piki* red = nullptr;
        Iterator pit(pikiMgr); CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit);
            if (p && p->isAlive() && p->mColor == Red) { red = p; break; }
        }
        require(wisp && red, "wisp or red Pikmin missing");
        red->changeMode(PikiMode::FreeMode, n);
        red->mFSM->transit(red, PIKISTATE_Flying);
        n->throwPiki(red, wisp->mSRT.t);
        thrown = true;
        std::printf("P2_QURIONE_DROP_THROW wisp=(%.2f,%.2f,%.2f)\n", wisp->mSRT.t.x, wisp->mSRT.t.y, wisp->mSRT.t.z);
        std::fflush(stdout);
        return result;
    }
};
}

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    if (!pc_window_init("P2 Qurione drop fixture", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new QurioneDropApp());
    return 0;
}
