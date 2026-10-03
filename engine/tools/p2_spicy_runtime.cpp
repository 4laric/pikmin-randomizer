// Private engine regression. Stocks and input are explicitly injected;
// this does not qualify natural Honey pickup or campaign save/resume.
#include <SDL2/SDL.h>
#include "App.h"
#include "Node.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "CPlate.h"
#include "Kontroller.h"
#include "GameStat.h"
#include "MoviePlayer.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include "pc_p2_sprays.h"
#include "pc_p2_original_resource_state.h"
#include "pc_p2_original_honey_bank.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
namespace {
void require(bool ok,const char* reason) {
    if (!ok) { std::printf("P2_SPICY_RUNTIME_FAIL %s\n",reason); std::fflush(nullptr); std::_Exit(1); }
}
// Equivalent to canonical scripts/p2_fixture_captain_guard.h; no healing.
void captainGuard(bool dead,bool deadState,float hp,int tick) {
    if (dead || deadState || !std::isfinite(hp) || hp <= 1) {
        std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",tick,hp,int(dead),int(deadState));
        std::fflush(nullptr); std::_Exit(86);
    }
}
struct Baseline { Piki* p; float attack,speed; int maturity; };
class SpicyApp : public PlugPikiApp {
    int ticks=0,phase=0,pauseTicks=0;
    bool sawCaptain=false;
    std::vector<Baseline> squad;
    p2originalresource::ResourceState stock;
    p2originalresource::EggContents contents;
    p2originalresource::honey::SourceBank bank;
    p2originalresource::honey::Resources resources;
    std::vector<float> pausedRemaining;
    float phaseTime=0;
    bool input(Navi* n) {
        auto previous=n->mKontroller->mInputPressed;
        n->mKontroller->mInputPressed=KBBTN_DPAD_UP;
        bool used=pc_p2_sprays_input(n);
        n->mKontroller->mInputPressed=previous;
        return used;
    }
public:
    int idle() override {
        int result=PlugPikiApp::idle();
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(n&&n->getCurrState()) { sawCaptain=true;captainGuard(GameStat::orimaDead,n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,ticks); }
        else require(!sawCaptain,"initialized captain disappeared");
        require(++ticks<7000,"frame timeout");
        auto* movies=gameflow.mMoviePlayer;
        if(movies&&movies->mIsActive) { movies->requestSkip(); return result; }
        if(!n||!n->getCurrState()||!pikiMgr||!playerState||gameflow.mIsUIOverlayActive) return result;
        if(phase==2) {
            for(unsigned i=0;i<squad.size();++i) require(squad[i].p->mP2Spicy.remaining==pausedRemaining[i],"effect timer advanced in pause");
            if(++pauseTicks<30) return result;
            gameflow.mPauseAll=false;
            require(input(n),"repeat input failed");
            for(const auto& b:squad) require(b.p->mP2Spicy.remaining==40,"repeat did not refresh");
            require(!input(n),"zero stock spent");
            phase=3;phaseTime=0;return result;
        }
        if(gameflow.mPauseAll||n->getCurrState()->getID()!=NAVISTATE_Walk) return result;
        if(phase==0) {
            Iterator pikis(pikiMgr);int alive=0;CI_LOOP(pikis) { auto* p=static_cast<Piki*>(*pikis);if(p&&p->isAlive()) ++alive; }
            require(alive==20,"fresh fixture must have exactly20 live Pikmin");
            Iterator party(n->mPlateMgr);CI_LOOP(party) { auto* p=static_cast<Piki*>(*party);if(p&&p->isAlive()&&p->getState()==PIKISTATE_Normal) squad.push_back({p,p->getAttackPower(),p->getSpeed(.25f),p->mHappa}); }
            require(!squad.empty(),"no eligible actual formation Pikmin");
            std::string e;p2originalresource::ResourceSnapshot injected;
            injected.sprayCounts[0]=2;require(stock.restore(injected,contents,e),"fixture inventory install");
            require(!pc_p2_sprays_bind(&stock,nullptr,e),"bind accepted missing source receiver");
            require(bank.resources(resources,e),"actual source Honey receiver bank missing");
            require(pc_p2_sprays_bind(&stock,&resources.receiverClips[1],e),"source-clock/inventory binding");
            require(input(n),"spicy input did not consume");
            require(stock.sprayCount(p2originalresource::HoneyKind::Spicy)==1,"wrong stock decrement");
            for(const auto& b:squad) require(!b.p->mP2Spicy.active()&&b.p->getState()==PIKISTATE_P2Dope,"effect committed before animation callback");
            std::printf("P2_SPICY_RUNTIME_START alive=%d formation=%zu stocks=injected input=injected receiver=actual_animation captain=unprotected\n",alive,squad.size());
            phase=1;return result;
        }
        phaseTime+=gsys->getFrameTime();
        if(phase==1) {
            bool ready=true;
            for(const auto& b:squad) ready=ready&&b.p->mP2Spicy.active()&&b.p->getState()==PIKISTATE_Normal;
            require(phaseTime<8,"missing Growup callback or return to normal");
            if(!ready) return result;
            for(const auto& b:squad) {
                require(b.p->mHappa==b.maturity,"spicy changed maturity");
                require(b.p->getAttackPower()==10&&b.p->getSpeed(.25f)==190,"source effects absent");
                pausedRemaining.push_back(b.p->mP2Spicy.remaining);
            }
            gameflow.mPauseAll=true;phase=2;return result;
        }
        if(phase==3) {
            bool recovered=true;for(const auto& b:squad) recovered=recovered&&!b.p->mP2Spicy.active();
            require(phaseTime<43,"40sec effect did not expire");
            if(!recovered) return result;
            require(phaseTime>=39,"effect expired early");
            for(const auto& b:squad) {
                require(b.p->isAlive()&&b.p->mHappa==b.maturity,"survival or maturity changed");
                require(b.p->getAttackPower()==b.attack&&b.p->getSpeed(.25f)==b.speed,"baseline effects not restored");
            }
            std::string e;require(pc_p2_sprays_bind(nullptr,nullptr,e),"detach");
            std::printf("P2_SPICY_RUNTIME_PASS formation=%zu actual_animation=1 source_stats=1 pause=1 refresh=1 stock_zero=1 recovery_seconds=%.3f injected_stock_and_input=1 natural_pickup=UNTESTED save_resume=UNTESTED\n",squad.size(),phaseTime);
            std::fflush(nullptr);std::_Exit(0);
        }
        return result;
    }
};
}
int main(int argc,char** argv) {
    for(int i=1;i<argc;++i)if(std::string(argv[i])=="--guard-negative")captainGuard(false,false,0,0);
    SDL_SetMainReady();pc_gpu_preference_apply();SDL_setenv("SDL_AUDIODRIVER","dummy",1);
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires experimental room");
    if(!pc_window_init("P2 spicy engine regression",960,540))return 3;
    pc_settings_init();pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&bounds);
    require(width==960&&height==540,"window dimensions");
    bool centered=std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2;
    require(centered,"window centering");
    std::printf("P2_SPICY_WINDOW width=%d height=%d centered=%d\n",width,height,int(centered));
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new SpicyApp);return 0;
}
