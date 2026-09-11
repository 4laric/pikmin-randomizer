// Isolated regression main: production gameplay plus the existing disk/cache audit.
#define PIKMIN_RANDOMIZER_TEST_HOOKS 1
#include "../src/plugPikiKando/gameCoreSection.cpp"
#include <SDL2/SDL.h>
#include "App.h"
#include "Node.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings_p2d.h"
class CampaignApp : public PlugPikiApp {
    int frames=0;
public:
    int idle() override {
        int result=PlugPikiApp::idle();
        if (++frames>2400) { std::puts("FAIL campaign timeout"); std::fflush(stdout); std::_Exit(1); }
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) gameflow.mMoviePlayer->requestSkip();
        return result;
    }
};
int main(int argc,char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1"); pc_bbft_init(argc,argv);
    if (!pc_window_init("Campaign enemy regression",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr=new NodeMgr(); gsys->run(new CampaignApp()); return 0;
}
