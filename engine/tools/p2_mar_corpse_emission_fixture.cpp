// P2 Mar corpse-emission proof fixture (#716).
//
// Standalone replacement-main translation unit built by the maintained
// scripts/build_pikmin2_fixture.py. Boots the room preview over a staged Mar
// arena (generator 375001, same contract as the #375 observer), kills the
// bound Mar (TEKI_Mar) with REAL squad Attack orders (no mHealth write, no
// TransportMode write anywhere in this file), and proves a corpse Pellet is
// emitted on natural Mar death with mPelletView bound to the dead actor such
// that the #668 receipt arm resolves it.
//
// Markers: P2_MAR_CORPSE_* only (plus engine P2_MAR_DEAD from pc_p2_mar.cpp).
// PASS only on observed corpse + receipt resolution. A stall is an honest
// FAIL, never a fallback credit. Gate 6 stays UNTESTED (no re-entry).
//
// Captain safety (#632): the canonical guard runs FIRST after engine idle and
// BEFORE movie/pause/UI early returns, readiness gates, observation counters
// or PASS markers; CAPTAIN_DOWN exits 86 BLOCKED. The captain is parked outside
// attack reach (captain damage is not this test). No blanket invincibility.
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Inline tested equivalent of scripts/p2_fixture_captain_guard.h (recorded hash
// alongside the lane); never changes captain health or game state.
#include <cmath>
#include <cstdio>
#include <cstdlib>
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86);
}
#endif
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "Piki.h"
#include "PikiAI.h"
#include "Generator.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "PelletState.h"
#include "MapMgr.h"
#include "Camera.h"
#include "PlayerState.h"
#include "Demo.h"
#include "teki.h"
#include "Traversable.h"
#include "GameStat.h"
#include "gameflow.h"
#include "pc_p2_mar.h"
#include "pc_p2_mar_receipt.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstring>
#include <string>
#include <vector>
static void require(bool value,const char* message) { if(!value) { std::printf("FAIL mar corpse: %s\n",message);std::fflush(stdout);std::_Exit(1); } }
// Neutral fixture controller: the captain is parked outside attack reach and
// takes no input.
class MarCorpseController : public Kontroller {
public:
    MarCorpseController() : Kontroller(1) {}
    void update() override { mMainStickX=0;mMainStickY=0;mSubStickX=0;mSubStickY=0; }
};
class RoomApp : public PlugPikiApp {
    static const unsigned MAR_GENERATOR = 375001u;
    int frames=0,observed=0,stage=0;
    float marMinHealth=1e9f,marStartHealth=0.0f;
    bool marDied=false,corpseProven=false,receiptProven=false;
    Teki* mar=nullptr;
    Pellet* corpse=nullptr;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    int liveSquad(){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(v&&v->isAlive())++n;}return n;}
    int clumpAttack(Teki* target,const Vector3f& c){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        if(v->isStickTo()||(v->mActiveAction&&v->mActiveAction->mCurrActionIdx==PikiAction::Attack)){++n;continue;}
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(c.x+10.0f*std::sin(ang),0,c.z+10.0f*std::cos(ang));
        pt.y=mapMgr->getMinY(pt.x,pt.z,true);v->resetPosition(pt);
        v->mSRT.r.y=ang+3.14159265f;
        v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
        v->mActiveAction->mChildActions[PikiAction::Attack].initialise(target);v->mMode=PikiMode::AttackMode;++n;}return n;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<120000,"mar corpse timeout");
    // Captain guard FIRST, before movie/pause/UI returns and any observation.
    if(naviMgr&&pikiMgr&&tekiMgr){
        Navi* guardN=naviMgr->getNavi();
        if(guardN){p2_fixture_require_captain(GameStat::orimaDead,guardN->mStateMachine->getCurrID(guardN)==NAVISTATE_Dead,guardN->mHealth,observed);}
    }
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        n->mKontroller=new MarCorpseController();
        mar=byGenerator(MAR_GENERATOR);
        require(mar,"bound Mar actor present (stage the Mar arena: generator 375001)");
        require(mar->mTekiType==TEKI_Mar,"bound actor is TEKI_Mar");
        marStartHealth=mar->mHealth;marMinHealth=marStartHealth;
        require(marStartHealth>0.0f,"Mar already dead at bind");
        // Park the captain far outside attack reach (not under test).
        Vector3f park=n->mSRT.t+Vector3f(600.0f,0.0f,0.0f);
        park.y=mapMgr->getMinY(park.x,park.z,true);n->resetPosition(park);
        std::printf("P2_MAR_CORPSE_READY_RECORDED cave=mar_arena generator=%u squad=%d captain_parked=1 start_health=%.1f\n",
                    MAR_GENERATOR,liveSquad(),marStartHealth);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        if(!mar||!mar->isAlive()){
            marDied=true;
            std::printf("P2_MAR_CORPSE_OBSERVED_DEAD generator=%u min_health=%.1f\n",MAR_GENERATOR,marMinHealth);
            std::fflush(stdout);stage=2;return result;
        }
        if(mar->mHealth<marMinHealth)marMinHealth=mar->mHealth;
        // Natural kill only: real squad Attack orders, no mHealth writes.
        clumpAttack(mar,mar->mSRT.t);
        if(observed%600==0){std::printf("P2_MAR_CORPSE_OBSERVE health=%.1f min=%.1f squad=%d tick=%d\n",mar->mHealth,marMinHealth,liveSquad(),observed);std::fflush(stdout);}
        if(observed>=90000){std::puts("FAIL P2_MAR_CORPSE kill_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    if(stage==2){
        require(marDied,"corpse stage without observed death");
        corpse=corpseOf(mar);
        if(corpse){
            corpseProven=true;
            std::printf("P2_MAR_CORPSE_EMITTED_OBSERVED generator=%u source_id=29 pellet=%p\n",MAR_GENERATOR,(void*)corpse);
            std::fflush(stdout);
            unsigned gen=0;
            if(pc_p2_mar_receipt(static_cast<PelletView*>(mar),gen)&&gen==MAR_GENERATOR){
                receiptProven=true;
                std::printf("P2_MAR_CORPSE_RECEIPT_RESOLVED generator=%u source_id=29\n",gen);
                std::puts("PASS P2_MAR_CORPSE_EMISSION corpse=1 receipt=1 injected=0");
                std::fflush(stdout);std::_Exit(0);
            }
        }
        if(observed%600==0){std::printf("P2_MAR_CORPSE_WAIT tick=%d corpse=%d\n",observed,corpse?1:0);std::fflush(stdout);}
        if(observed>=100000){std::puts("FAIL P2_MAR_CORPSE no_corpse_pellet");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    std::fflush(stdout);return result;
}};
int main(int argc,char** argv) {
    // Automated fixture only: keep the real mixer/timing, never open a speaker device.
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);
    SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires --experimental-pikmin2-room");
    // Custom fixture entrypoint: mirror pc_main.cpp's mandatory small centered
    // preview window (default 960x540, overridable with PIKMIN_P2_ROOM_WINDOW=WxH).
    int windowWidth=960,windowHeight=540;bool smallWindow=true;
    if(const char* value=std::getenv("PIKMIN_P2_ROOM_WINDOW")){
        if(!std::strcmp(value,"off")||!std::strcmp(value,"0"))smallWindow=false;
        int customWidth=0,customHeight=0;
        if(std::sscanf(value,"%dx%d",&customWidth,&customHeight)==2&&customWidth>=320&&customHeight>=240){windowWidth=customWidth;windowHeight=customHeight;}
    }
    if(!pc_window_init("P2 Mar corpse emission fixture",windowWidth,windowHeight))return 3;
    pc_settings_init();
    if(smallWindow){
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(windowWidth,windowHeight);
    pc_window_center();
    }
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new RoomApp());return 0;
}