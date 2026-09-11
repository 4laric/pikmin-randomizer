#include <SDL2/SDL.h>
#include "../src/plugPikiColin/newPikiGame.cpp"
#include "App.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Node.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>

static bool confirmResults;
static bool resumeTest;
struct ResultController : Controller {
    int ticks=0;
    ResultController(): Controller(1) {}
    void update() override { updateCont(confirmResults && (++ticks%20==0) ? KBBTN_A : 0); }
};
class DayEndApp : public PlugPikiApp {
    int frames=0, ready=0, held=0;
    bool started=false, seen=false;
    ResultController* control=nullptr;
public:
    int idle() override {
        if (++frames>3000) finish(1,"timeout");
        int result=PlugPikiApp::idle();
        if (started && gameflow.mCurrGameSectionID != SECTION_OnePlayer) finish(2,"returned to title instead of results");
        if (resumeTest && pc_randomizer_resumed() && gameflow.mWorldClock.mCurrentDay == 8) {
            if (++held == 120) {
                if (playerState->mTotalBornPikiNum != 1234) finish(7,"born count did not restore");
                for (int color=0; color<3; ++color) {
                    if (pikiInfMgr.mPikiCounts[color][Flower] != 17 + color) finish(8,"flower population did not restore");
                    if (!playerState->hasBootContainer(color)) finish(9,"Onion boot flag did not restore");
                }
                finish(0,"campaign resumed on day 8; population, flowers and Onion flags restored");
            }
            return result;
        }
        MoviePlayer* movies=gameflow.mMoviePlayer;
        if (movies && movies->mIsActive && frames%5==0) movies->requestSkip();
        if (!started && gamecore && movies && !movies->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
            if (++ready==60) {
                started=true;
                if (resumeTest) {
                    gameflow.mWorldClock.mCurrentDay = 7;
                    playerState->mTotalBornPikiNum = 1234;
                    for (int color=0; color<3; ++color) {
                        GoalItem* onion = itemMgr->getContainer(color);
                        if (onion) onion->mHeldPikis[Flower] = 17 + color;
                        pikiInfMgr.mPikiCounts[color][Flower] = 17 + color;
                    }
                }
                gamecore->forceDayEnd();
                gameflow.mIsDayEndTriggered=TRUE;
                std::puts("DAYEND forced ordinary sunset");
            }
        }
        if (started && resultWindow) {
            if (!seen) {
                seen=true; control=new ResultController(); static_cast<GameMovieInterface*>(gameflow.mGameInterface)->mSetupSection->mController=control;
                std::puts("DAYEND results opened; repeatedly request Start skip");
            }
            DayOverModeState* state=static_cast<DayOverModeState*>(static_cast<GameMovieInterface*>(gameflow.mGameInterface)->mSetupSection->mCurrentModeState);
            if (!confirmResults && state->mState != DayOverModeState::STATE_PhaseTwo) finish(3,"background skip advanced into ending phases");
            if (++held==120) {
                confirmResults=true;
                std::puts("DAYEND results retained for 120 frames; confirming results/save with A");
            }
        }
        if (seen && static_cast<GameMovieInterface*>(gameflow.mGameInterface)->mSetupSection && static_cast<GameMovieInterface*>(gameflow.mGameInterface)->mSetupSection->mPendingOnePlayerSectionID==ONEPLAYER_MapSelect) finish(0,"results/save completed; next-day map requested");
        return result;
    }
    static void finish(int code,const char* text) { std::printf("%s DAYEND %s\n",code?"FAIL":"PASS",text);std::fflush(stdout);std::_Exit(code); }
};
int main(int argc,char** argv) {
    resumeTest = std::getenv("PIKMIN_CAMPAIGN_TEST") != nullptr;
    SDL_SetMainReady();pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    if(!pc_window_init("Day-end skip regression",640,480))return 4;
    pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
    gsys->run(new DayEndApp());return 0;
}
