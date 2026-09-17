// P2 challenge stage content-loading boot fixture (#694).
//
// Complete standalone replacement-main translation unit built by the
// maintained scripts/build_pikmin2_fixture.py (RoomApp splice heritage from
// tools/preview_p2_room.cpp; that preview TU is not linked here, so this
// file carries its own engine includes, require helper, neutral fixture
// controller, RoomApp and main).
//
// Scenario: a worker-staged stage-content sidecar (p2-challenge-content.txt)
// plus a caller-staged p2-cave-generate.txt manifest select one P2 challenge
// stage floor. The fixture validates the selection through
// p2_challenge_content::select(), verifies staged spawn intents cover the
// stage roster, then observes LIVE squad/actors with finite positions in the
// running engine. Generation and births stay with the integrated engine paths
// (#129 generator, actor-manager birth); this fixture never provisions arenas,
// births actors, writes saves, or touches the economy. A stall is an honest
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
#include "pc_p2_challenge_content_loading.h"
// Lane-local unity bridge: #694 registered no CMake target for the binder and
// this lane owns no CMakeLists edits, so the binder TU is compiled into the
// fixture object. Downstream promotion (#562) registers
// pc_port/pc_p2_challenge_content_loading.cpp as a first-class target and
// drops this include. Anonymous-namespace symbols stay internal to fixture.obj.
#include "../pc_port/pc_p2_challenge_content_loading.cpp"
// Engine context (mirrors tools/preview_p2_room.cpp plus the guarded-boot
// fixture set); the maintained builder compiles this TU with pc_main.cpp's
// flags, so every declaration used below must be included here.
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
#include "PikiMgr.h"
#include "Pellet.h"
#include "PelletState.h"
#include "MapMgr.h"
#include "Camera.h"
#include "LifeGauge.h"
#include "Light.h"
#include "Shape.h"
#include "Material.h"
#include "Mesh.h"
#include "PlayerState.h"
#include "Demo.h"
#include "teki.h"
#include "Traversable.h"
#include "GameStat.h"
#include "gameflow.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
static void require(bool value,const char* message) { if(!value) { std::printf("FAIL challenge content: %s\n",message);std::fflush(stdout);std::_Exit(1); } }
// Neutral fixture controller: the captain is parked outside attack reach and
// takes no input. Local to this TU (preview_p2_room.cpp's walk controller is
// not linked into the fixture).
class ChallengeContentController : public Kontroller {
public:
    ChallengeContentController() : Kontroller(1) {}
    void update() override { mMainStickX=0;mMainStickY=0;mSubStickX=0;mSubStickY=0; }
};

class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0;
    bool selected=false;
    p2_challenge_content::Expectation expect;
    int liveSquadPeak=0,liveActorsPeak=0;
    int liveSquad() {
        int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++count;}return count;
    }
    int liveActors() {
        int count=0;Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->isAlive())++count;}return count;
    }
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<90000,"challenge content timeout");
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
        n->mKontroller=new ChallengeContentController();
        require(p2_challenge_content::select("p2-challenge-content.txt",expect),"stage content selection");
        require(expect.valid,"selection valid");
        require(p2_challenge_content::verifyCoverage(expect),"spawn coverage");
        int squad=liveSquad();
        require(squad>=1,"live starting squad");
        // Park the captain well outside attack reach (not under test).
        Vector3f park=n->mSRT.t+Vector3f(150.0f,0.0f,0.0f);
        park.y=mapMgr->getMinY(park.x,park.z,true);n->resetPosition(park);
        std::printf("P2_CHALLENGE_CONTENT_READY cave=%s floor=%d squad=%d captain_parked=1\n",
                    expect.caveId.c_str(),expect.floor,squad);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        int squad=liveSquad(),actors=liveActors();
        if(squad>liveSquadPeak)liveSquadPeak=squad;
        if(actors>liveActorsPeak)liveActorsPeak=actors;
        require(p2_challenge_content::positionsFinite(),"nonfinite actor position");
        if(observed%90==0){std::printf("P2_CHALLENGE_CONTENT_OBSERVE squad=%d actors=%d tick=%d\n",squad,actors,observed);std::fflush(stdout);}
        if(liveSquadPeak>=1&&liveActorsPeak>=1){
            std::printf("P2_CHALLENGE_CONTENT_LIVE squad=%d actors=%d tick=%d\n",liveSquadPeak,liveActorsPeak,observed);
            std::puts("PASS P2_CHALLENGE_CONTENT_RUN content=1");
            std::fflush(stdout);std::_Exit(0);
        }
        if(observed>=6000){std::puts("FAIL P2_CHALLENGE_CONTENT no_live_content");std::fflush(stdout);std::_Exit(1);}
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
    if(!pc_window_init("P2 challenge content-loading fixture",windowWidth,windowHeight))return 3;
    pc_settings_init();
    if(smallWindow){
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(windowWidth,windowHeight);
    pc_window_center();
    }
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new RoomApp());return 0;
}