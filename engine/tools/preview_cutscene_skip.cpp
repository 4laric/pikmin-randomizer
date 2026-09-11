
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>

class SkipApp : public PlugPikiApp {
    int frames = 0, stable = 0, requests = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 1500) { std::puts("FAIL live skip timeout"); std::fflush(stdout); std::_Exit(1); }
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive) {
            for (MovieInfo* info = static_cast<MovieInfo*>(movies->mPlayInfoList.mChild); info;
                 info = static_cast<MovieInfo*>(info->mNext)) {
                if (info->mPlayer && !info->mPlayer->mSkipToEnd) {
                    std::printf("REQUEST skip movie=%d type=%u frame=%f\n",info->mMovieIndex,info->mPlayer->mType,info->mPlayer->mCurrentSceneFrame);
                    info->mPlayer->requestSkip(); ++requests;
                }
            }
        }
        if (requests && gameflow.mCurrGameSectionID == SECTION_OnePlayer && flowCont.mCurrentStage && movies && !movies->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
            if (++stable == 60) { std::printf("PASS live landing skip: %d movie(s), gameplay stable for 60 frames\n",requests); std::fflush(stdout); std::_Exit(0); }
        } else stable=0;
        return result;
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Cutscene skip fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new SkipApp());
    return 0;
}
