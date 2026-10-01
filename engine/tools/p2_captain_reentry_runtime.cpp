// #1074 bounded two-captain scene reentry with scripted switching, movement
// and transient captures. Real exitStage/softReset; no native save-resume claim.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "CPlate.h"
#include "GameCoreSection.h"
#include "GameStat.h"
#include "Section.h"
#include "Graphics.h"
#include "MapMgr.h"
#include <cmath>
#include "Interactions.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
#include "pc_p2_input_script.h"
#include "pc_coop.h"
#include "Node.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiAI.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gfx.h"
#include "pc_gpu_preference.h"
#include "pc_p2_captain.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include "teki.h"
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

namespace {
bool sForceCaptainDown = false;
bool sForceInactiveDown = false;

void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL P2_CAPTAIN_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

// Fixture-only equivalent of root scripts/p2_fixture_captain_guard.h. CI is
// standalone native, so this observer carries the same fail-closed semantics.
void requireCaptain(Navi* n, int tick) {
    const float hp=n?n->mHealth:0;
    const bool dead=!n || !naviMgr || !n->getCurrState() || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead;
    if(!GameStat::orimaDead && !dead && std::isfinite(hp) && hp>1.0f)return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",tick,hp,int(GameStat::orimaDead),int(dead));
    std::fflush(nullptr);std::_Exit(86);
}

// Reusable P6 PPM capture after a real draw (mirrors the other room fixtures).
// Returns true (and writes the file) only when the captured frame is non-black,
// so a caller can retry across the setup fade-in.
bool capture(const char* path)
{
    pc_gfx_flush_batch();
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind != nullptr, "framebuffer entry point unavailable");
    GLint previous = 0; glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous); bind(GL_FRAMEBUFFER, 0);
    int width = 0, height = 0; SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &width, &height);
    std::vector<unsigned char> pixels(size_t(width) * size_t(height) * 3);
    glReadBuffer(GL_BACK); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bind(GL_FRAMEBUFFER, previous);
    bool visible = false; for (unsigned char value : pixels) visible |= value > 8;
    if (!visible) return false;
    FILE* file = std::fopen(path, "wb"); require(file != nullptr, "capture file");
    std::fprintf(file, "P6\n%d %d\n255\n", width, height);
    for (int y = height - 1; y >= 0; --y) std::fwrite(pixels.data() + size_t(y) * width * 3, 1, size_t(width) * 3, file);
    std::fclose(file);
    return true;
}



GameCoreSection* findCore(CoreNode* node,int depth=0) {
    if(!node || depth>20)return nullptr;
    if(auto* core=dynamic_cast<GameCoreSection*>(node))return core;
    for(auto* child=node->Child();child;child=child->Next())
        if(auto* core=findCore(child,depth+1))return core;
    return nullptr;
}
class CaptainReentryApp final:public PlugPikiApp {
    int frames=0,tick=-1,scene=0,resets=0,exitResets=0;
    Navi *a=nullptr,*b=nullptr;
    Piki* target=nullptr;
    Vector3f movementStart;
    bool shot=false,transition=false;
    void pad(unsigned keys=0,int x=0,int y=0){pc_p2_input_script_set(1,keys,x,y);}
    void selected(int slot){
        auto* n=naviMgr->getNavi(slot);
        require(naviMgr->getActiveNavi()==n,"selected fresh captain");
        require(cameraMgr->mController==n->mKontroller && cameraMgr->mCamera->mTargetCreature==n,"fresh camera binding");
        std::printf("P2_REENTRY_SELECTED scene=%d slot=%d camera=1\n",scene,slot);
    }
public:
    void softReset() override {PlugPikiApp::softReset();++resets;}
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if(tick>30 && !shot){char name[80];std::snprintf(name,sizeof(name),"captain-reentry-%d.ppm",scene);shot=capture(name);}
    }
    int idle() override {
        const int result=PlugPikiApp::idle();require(++frames<3600,"frame bound");
        // Guard every initialized live scene before movie/pause/preview returns.
        // Only our explicit exit/reconstruction gap permits missing managers.
        if(tick>=0){
            require(!transition && naviMgr && naviMgr->getActiveNavi(),"live scene manager unexpectedly disappeared");
            requireCaptain(naviMgr->getNavi(0),tick);requireCaptain(naviMgr->getNavi(1),tick);
        }else {
            if(scene>0)require(transition,"unexplained scene gap");
            // A newly initialized captain is guarded even before the Walk-ready
            // observation; absent/uninitialized objects during loading are not death.
            if(naviMgr)for(int slot=0;slot<2;++slot){
                auto* n=naviMgr->getNavi(slot);
                if(n && n->getCurrState())requireCaptain(n,tick);
            }
        }
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!pc_p2_preview_ready() || !naviMgr || !naviMgr->getActiveNavi())return result;
        requireCaptain(naviMgr->getActiveNavi(),tick);
        if(gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
        if(tick<0){
            a=naviMgr->getNavi(0);b=naviMgr->getNavi(1);require(a && b,"two fresh captains");
            if(a->getCurrState()->getID()!=NAVISTATE_Walk || b->getCurrState()->getID()!=NAVISTATE_Walk)return result;
            requireCaptain(a,tick);requireCaptain(b,tick);
            require(pc_p2_captain::adapter()!=nullptr && pc_p2_captain::captive_count()==0,"fresh adapter without old captures");
            require(scene==0 || resets>exitResets,"actual section reconstruction");
            int live=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p && p->isAlive()){++live;if(!target)target=p;}}
            require(live==20 && target,"fresh generator squad exactly20");
            selected(0);tick=0;transition=false;
            std::printf("P2_REENTRY_SCENE scene=%d resets=%d live=%d active=0 transient_captures=0\n",scene,resets,live);
            if(sForceCaptainDown || sForceInactiveDown){
                (sForceInactiveDown?b:a)->mHealth=0;
                // Next frame must fail the ordinary early guard, not a special
                // direct assertion; this also exercises inactive-captain coverage.
                gameflow.mPauseAll=TRUE;return result;
            }
        }
        ++tick;
        switch(tick){
        case 5:pad(KBBTN_DPAD_UP);break;
        case 15:selected(1);break;
        case 20:pad();movementStart=b->getPosition();break;
        case 25:pad(0,60,0);break;
        case 45:{const float distance=(b->getPosition()-movementStart).length();require(distance>1,"fresh selected captain moves");std::printf("P2_REENTRY_MOVE scene=%d distance=%.3f\n",scene,distance);pad();break;}
        case 55:pad(KBBTN_DPAD_UP);break;
        case 65:selected(0);break;
        case 70:pad();break;
        case 80:{
            Navi* owner=target->mNavi;
            const std::uint64_t epoch=107400+scene;
            require(pc_p2_captain::capture_actor(epoch,target),"fresh transient capture");
            require(!pc_p2_captain::release_actor(epoch-1,target,P2CaptainInvalid) && pc_p2_captain::is_captive_for(epoch,target),"stale previous epoch rejected");
            require(pc_p2_captain::release_actor(epoch,target,P2CaptainInvalid) && target->mNavi==owner,"fresh release preserves owner");
            require(pc_p2_captain::capture_actor(epoch,target),"capture retained through exit");
            std::printf("P2_REENTRY_CAPTURE scene=%d stale_rejected=1 released=1 retained_for_exit=1\n",scene);break;
        }
        case 100:{
            require(shot,"scene rendered capture");
            if(scene==2){require(pc_p2_captain::release_actor(107402,target,P2CaptainInvalid),"final release");std::puts("PASS P2_CAPTAIN_REENTRY scenes=3 reconstructions=2 scripted_transition=1 native_save_resume=0");std::fflush(nullptr);std::_Exit(0);}
            auto* core=findCore(gameflow.mGameSection);require(core,"active game core");
            core->exitStage();
            require(pc_p2_captain::adapter()==nullptr && pc_p2_captain::captive_count()==0 && naviMgr==nullptr,"actual exit clears adapter and manager");
            a=nullptr;b=nullptr;target=nullptr;tick=-1;shot=false;transition=true;++scene;exitResets=resets;pad();
            gameflow.mNextOnePlayerSectionID=ONEPLAYER_NewPikiGame;gsys->softReset();
            std::printf("P2_REENTRY_EXIT next_scene=%d adapter_unbound=1 manager_null=1 scripted_soft_reset=1\n",scene);break;
        }}
        std::fflush(stdout);return result;
    }
};
} // namespace
int main(int argc,char** argv) {
    for(int i=1;i<argc;++i){sForceCaptainDown|=std::string(argv[i])=="--force-captain-down";sForceInactiveDown|=std::string(argv[i])=="--force-inactive-down";}
    _putenv_s("PIKMIN_P2_SECOND_CAPTAIN","1");
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
    pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"experimental room required");
    if(!pc_window_init("P2 Captain scene reentry acceptance",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2 && std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;
    require(w==960 && h==540 && centered,"fresh fixture window baseline after settings");
    std::printf("P2_SWITCH_WINDOW size=%dx%d pos=%d,%d centered=%d after_settings=1\n",w,h,x,y,int(centered));std::fflush(stdout);
    pc_coop_set_pending(false);pc_p2_input_script_set(1,0);pc_p2_input_script_set(2,0);
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CaptainReentryApp());return 0;
}

