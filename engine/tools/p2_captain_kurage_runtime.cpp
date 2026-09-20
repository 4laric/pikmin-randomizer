// #130: real engine provider/consumer lifecycle diagnostic, ported from
// codex/p2-lane12-review (7 commits ba9d7f3a0..6f67ca7a5) onto the
// claude/p2-deepseek-wave-native captain API (reduced lane rd-captain-kurage).
//
// The line's captain API is epoch-based (no ticket struct): a capture is
// identified by (captorEpoch, actor), stale epochs are rejected, and rollback
// restores the previous owner when passed P2CaptainInvalid. All six ported
// behaviours are preserved: captive-actor claim rejection, revocable squad
// captures bound to receiver generation ticks, generator-birth fixture Pikmin,
// diagnostic receiver eligibility override, squad-action release before
// clearing ownership, and replacement-capture preservation.
//
// Admission, owner death and test births are injected; natural species combat
// is not asserted. NOT YET RUN: captain-safety adoption (#632,
// scripts/p2_fixture_captain_guard.h) is required before the first GL run;
// this file is compile-checked only (p2_captain_kurage_runtime_compile).
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "GameStat.h"
#include "Section.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "Collision.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "pc_p2_captain.h"
#include "pc_p2_kurage_arena.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
void require(bool ok, const char* message) {
    if (!ok) { std::printf("FAIL CAPTAIN_KURAGE %s\n",message); std::fflush(stdout); std::_Exit(1); }
}
GameCoreSection* findCore(CoreNode* node, int depth=0) {
    if (!node || depth>20) return nullptr;
    if (auto* core=dynamic_cast<GameCoreSection*>(node)) return core;
    for (auto* child=node->Child();child;child=child->Next())
        if (auto* core=findCore(child,depth+1)) return core;
    return nullptr;
}
void capture(const char* path) {
    pc_gfx_flush_batch();
    auto bind=reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind!=nullptr,"framebuffer entrypoint");
    GLint previous=0; glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous); bind(GL_FRAMEBUFFER,0);
    int w=0,h=0; SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(),&w,&h);
    std::vector<unsigned char> pixels(size_t(w)*h*3);
    glPixelStorei(GL_PACK_ALIGNMENT,1); glReadPixels(0,0,w,h,GL_RGB,GL_UNSIGNED_BYTE,pixels.data());
    bind(GL_FRAMEBUFFER,previous); require(glGetError()==GL_NO_ERROR,"capture read");
    FILE* file=std::fopen(path,"wb"); require(file!=nullptr,"capture file");
    std::fprintf(file,"P6\n%d %d\n255\n",w,h);
    for(int y=h-1;y>=0;--y) std::fwrite(pixels.data()+size_t(y)*w*3,1,size_t(w)*3,file);
    std::fclose(file);
}
class CaptainApp final:public PlugPikiApp {
    int frames=0,ready=0,travel=0,stage=0;
    bool setup=false,shot=false;
    Piki* target=nullptr;
    Piki* control=nullptr;
    Navi* controlOwner=nullptr;
    std::uint64_t previousSceneEpoch=0;
    int resets=0;
    Piki* birth(Navi* n) {
        auto* p=static_cast<Piki*>(pikiMgr->birth()); require(p!=nullptr,"test birth");
        GameStat::workPikis.inc(Red); GameStat::update();
        p->init(n); p->Creature::init(Vector3f(0,120,0));
        // Match generator birth: initBirth resets the visual shape, so colour
        // must be finalized afterward to refresh matching collision matrices.
        p->initColor(Red); p->changeMode(PikiMode::FormationMode,n);
        // Existing private Kurage receiver requires mayIstick (Attack/Carry/
        // Flying), unlike a complete source suction receiver. Explicitly inject
        // this diagnostic eligibility; do not widen production admission here.
        p->mMode=PikiMode::AttackMode;
        p->mNavi=n; // explicit fixture squad assignment
        return p;
    }
public:
    void softReset() override {
        PlugPikiApp::softReset();
        ++resets;
    }
    int idle() override {
        const int result=PlugPikiApp::idle(); require(++frames<1200,"startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi()
            || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        if (++ready<30) return result;
        Navi* n=naviMgr->getNavi();
        if(stage==2) {
            require(resets>=2,"section reconstruction occurred");
            require(pc_p2_captain::captive_count()==0,"old scene captures revoked");
            int live=0; Iterator squad(pikiMgr);
            CI_LOOP(squad) {
                auto* p=static_cast<Piki*>(*squad);
                if(p && p->isAlive()) { ++live; if(!control) control=p; }
            }
            require(live>=20 && control,"fresh scene starting squad");
            controlOwner=control->mNavi;
            target=birth(n);
            require(pc_p2_captain::capture_actor(700,target),"fresh scene capture");
            require(!pc_p2_captain::release_actor(previousSceneEpoch,target,P2CaptainInvalid)
                && pc_p2_captain::is_captive_for(700,target),"stale release preserves fresh capture");
            require(pc_p2_captain::release_actor(700,target,P2CaptainInvalid) && target->mNavi==n
                && control->mNavi==controlOwner,"fresh scene release and control");
            std::printf("P2_CAPTAIN_REENTRY resets=%d live=%d stale_rejected=1 fresh_capture=1 control_preserved=1\n",resets,live);
            std::puts("PASS CAPTAIN_KURAGE live_squad=20 window=960x540 travel=1 stomach=1 interruption=1 stale_ticket=1 predeath=1 stage_exit=1 scene_reentry=1 injected_admission=1");
            std::fflush(stdout); std::_Exit(0);
        }
        if (!setup) {
            int live=0; Iterator squad(pikiMgr);
            CI_LOOP(squad) {
                auto* p=static_cast<Piki*>(*squad);
                if (p && p->isAlive()) { ++live; if(!control) control=p; }
            }
            require(live>=20 && control,"starting live squad"); controlOwner=control->mNavi;
            std::printf("P2_CAPTAIN_SQUAD live=%d active_gameplay=1 extinction=0\n",live);
            n->resetPosition(Vector3f(0,0,-250));
            require(pc_p2_kurage_arena_setup("p2-kurage-arena.txt"),"Kurage host setup");
            require(pc_p2_kurage_receiver_setup(pc_p2_kurage_arena_owner(),pc_p2_kurage_arena_mouth()),"receiver setup");
            target=birth(n);
            require(pc_p2_captain::health(0)==n->mHealth && pc_p2_captain::health(1)==0,"live slot0 health");
            require(pc_p2_kurage_receiver_admit(target),"injected mouth admission");
            require(target->mNavi==nullptr && pc_p2_captain::captive_count()==1,"capture clears only target owner");
            require(target->mActiveAction->mCurrActionIdx==PikiAction::NOACTION,"capture releases prior formation action");
            // Interrupt before attachment, then admit again for real mouth travel.
            pc_p2_kurage_receiver_release_all();
            require(pc_p2_captain::captive_count()==0 && target->isAlive(),"travel interruption");
            require(control->mNavi==controlOwner,"control after interruption");
            target->mNavi=n;
            require(pc_p2_kurage_receiver_admit(target),"second mouth admission");
            setup=true;
            std::fflush(stdout); return result;
        }
        require(control->isAlive() && control->mNavi==controlOwner,"ordinary control ownership");
        if (stage==0) {
            require(++travel<240,"mouth travel timeout");
            require(pc_p2_kurage_arena_update(1.0f/60.0f,true),"host update");
            if (pc_p2_kurage_receiver_stomach_count()==1 && shot) stage=1;
            return result;
        }
        if(stage==1) {
            require(target->mNavi==nullptr && target->isStickTo(),"attached captive squad state");
            pc_p2_kurage_receiver_update(0,false,false,false); // injected owner interruption
            require(target->isAlive() && !target->isStickTo() && target->mNavi==nullptr
                && pc_p2_captain::captive_count()==0,"stomach release");
            Piki* late=birth(n);
            target->mNavi=n;
            require(pc_p2_captain::capture_actor(700,target),"epoch capture");
            require(pc_p2_captain::release_actor(700,target,P2CaptainInvalid) && target->mNavi==n,"rollback restore");
            require(pc_p2_captain::capture_actor(701,target),"repeat capture");
            require(!pc_p2_captain::release_actor(700,target,P2CaptainInvalid)
                && pc_p2_captain::is_captive_for(701,target),"stale capture rejected");
            require(late->mNavi==n && control->mNavi==controlOwner,"late/control ownership");
            target->kill(false); // actual Creature::kill predeath -> provider forget
            require(!pc_p2_captain::is_captive_for(701,target) && pc_p2_captain::captive_count()==0,"predeath revocation");
            target=birth(n);
            require(pc_p2_captain::capture_actor(702,target),"replacement capture");
            require(!pc_p2_captain::release_actor(701,target,P2CaptainInvalid)
                && pc_p2_captain::is_captive_for(702,target),"replacement lifetime protected");
            std::printf("P2_CAPTAIN_LIFETIME stale_rejected=1 late_control_preserved=1\n");
            require(pc_p2_captain::release_actor(702,target,P2CaptainInvalid),"replacement release");
            require(pc_p2_captain::capture_actor(703,late),"ticket retained across scene");
            previousSceneEpoch=703;
            // Scene cleanup through the real exit path; no actor dereference afterward.
            require(pc_p2_kurage_receiver_capture(target),"capture before stage exit");
            auto* core=findCore(gameflow.mGameSection); require(core!=nullptr,"core section");
            core->exitStage();
            require(pc_p2_captain::captive_count()==0 && pc_p2_kurage_receiver_count()==0,"stage exit cleanup");
            // Mirror the engine's quitting-state transition, then let normal
            // PlugPikiApp::idle reconstruct the section on its next frame.
            target=nullptr; control=nullptr; controlOwner=nullptr;
            setup=false; ready=0; stage=2;
            gameflow.mNextOnePlayerSectionID=ONEPLAYER_NewPikiGame;
            gsys->softReset();
            std::puts("P2_CAPTAIN_EXIT pending_soft_reset=1 captures=0");
            std::fflush(stdout); return result;
        }
        return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if(!setup) return;
        pc_p2_kurage_arena_draw(gfx);
        if(!shot && pc_p2_kurage_receiver_stomach_count()==1) { capture("captain-kurage-stomach.ppm"); shot=true; }
    }
};
}
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1"); pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires experimental room");
    if(!pc_window_init("Lane 12 captain/Kurage diagnostic",960,540)) return 3;
    pc_settings_init(); // persisted settings must precede fixture window policy
    SDL_Window* window=SDL_GL_GetCurrentWindow();
    SDL_SetWindowFullscreen(window,0); SDL_SetWindowSize(window,960,540); pc_window_center();
    int w=0,h=0,x=0,y=0; SDL_GetWindowSize(window,&w,&h); SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{}; SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    const bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2 && std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;
    std::printf("P2_CAPTAIN_WINDOW size=%dx%d pos=%d,%d centered=%d after_settings=1\n",w,h,x,y,int(centered));
    require(w==960 && h==540 && centered,"standard window");
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr=new NodeMgr();
    gsys->run(new CaptainApp()); return 0;
}
