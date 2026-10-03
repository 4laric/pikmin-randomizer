// Actual physical initializer/RNG seam only; not GenPiki or wild AI admission.
#include "system.h"
#include "App.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "GameStat.h"
#include "pc_p2_original_piki_init.h"
#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_coop.h"
#include "netplay/pc_sim_rng.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <SDL2/SDL.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
namespace {
unsigned checks=0;
void require(bool condition,const char* name) {
    ++checks;
    if(!condition){std::printf("FAIL ORIGINAL_PIKI_INIT %s\n",name);std::fflush(nullptr);std::_Exit(1);}
}
int field() {
    int count=0;Iterator it(pikiMgr);
    for(it.first();!it.isDone();it.next())++count;
    return count;
}
void run() {
    auto* mgr=pikiMgr;auto* captains=naviMgr;
    require(field()==20,"physical baseline20");
    require(!pc_bbft_color_access(Blue),"actual generated seed lacks Blue Onion");
    unsigned physicalBirths=0;
    for(int color=Blue;color<=Yellow;++color) {
        std::string error;PcSimRngCheckpoint before,after;
        require(pc_sim_rng_capture(before,error),"capture actual RNG before physical birth");
        auto* body=dynamic_cast<Piki*>(pikiMgr->birth());
        require(body!=nullptr,"actual manager physical birth");
        ++physicalBirths;
        // Match the native GenObjectPiki::birth population registration before
        // init/free can transfer the body between the work/free counters.
        GameStat::workPikis.inc(color);
        GameStat::update();
        {
            PcOriginalPikiInitScope source(body);
            require(source.valid(),"exact body source scope held");
            body->init(nullptr);
            require(source.consumed(),"actual Piki::init consumed source tag");
            require(body->mColor==Blue && body->mHappa==Leaf && body->mPikiSize==1.0f,
                    "actual source initial Blue Leaf unit base scale independent of AP color lock");
            body->initColor(color);
            body->changeMode(PikiMode::FreeMode,nullptr);
            require(body->mColor==color && body->mMode==PikiMode::FreeMode && body->mNavi==nullptr,
                    "authored native RGB species and source free entry");
            require(pc_sim_rng_capture(after,error),"capture actual RNG after initial free entry");
            std::printf("ORIGINAL_PIKI_INIT_RNG color=%d before_sim=%llu after_sim=%llu before_cosmetic=%llu after_cosmetic=%llu\n",
                        color,(unsigned long long)before.simDraws,(unsigned long long)after.simDraws,
                        (unsigned long long)before.cosmeticDraws,(unsigned long long)after.cosmeticDraws);
            require(before.profile==after.profile && before.simState==after.simState
                    && before.simDraws==after.simDraws,"no host simulation RNG draws in physical original initializer");
            require(field()==21 && body->isAlive(),"actual physical new body alive in native manager");
            require(GameStat::mapPikis==21,"new physical body counted in native field capacity");
        }
        require(!pc_p2_original_piki_init_held(body),"source scope expires before gameplay");
        body->kill(false);
        require(field()==20,"owned native body killed and pool baseline restored");
        require(GameStat::mapPikis==20,"native population counters restored after owned kill");
        require(pikiMgr==mgr && naviMgr==captains,"live managers preserved");
    }
    std::printf("PASS ORIGINAL_PIKI_INIT checks=%u physical_births=%u source_rgb=3 initializer_only=1 original_genpiki=0 wild_ai=0 full_course=0\n",checks,physicalBirths);
    std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp {
    std::chrono::steady_clock::time_point began=std::chrono::steady_clock::now();
public:int idle()override {
    require(std::chrono::steady_clock::now()-began<std::chrono::seconds(55),"bounded actual startup");
    int result=PlugPikiApp::idle();
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_randomizer_ready()||!pikiMgr||!naviMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    auto* captain=naviMgr->getActiveNavi();
    if(!captain||!captain->getCurrState()||captain->getCurrState()->getID()!=NAVISTATE_Walk)return result;
    require(!GameStat::orimaDead&&captain->mHealth>1,"live captain");
    if(field()!=20)return result;
    std::printf("ORIGINAL_PIKI_INIT_BASELINE pikmin=20 window=960x540\n");std::fflush(nullptr);
    run();return result;
}
};
}
int main(int argc,char** argv) {
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();
    pc_sim_rng_note_main_thread();std::string error;
    require(pc_sim_rng_begin_offline(0x148,0x248,error),"actual offline RNG profile");
    pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"real generated assets required");
    if(!pc_window_init("Original Piki initializer fixture",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    int width=0,height=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&width,&height);
    require(width==960&&height==540,"actual centered960 startup");
    pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
