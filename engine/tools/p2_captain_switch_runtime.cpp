// #928 CI-built, bounded local acceptance. Live scripted input drives switching,
// disband/recruit/hold/release; explicit spatial/unsafe/death injections are
// labeled and cannot establish natural enemy combat or campaign completion.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "CPlate.h"
#include "GameCoreSection.h"
#include "GameStat.h"
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
bool sSingle = false;
bool sCoop = false;
bool sPrimaryDown = false;
bool sForceCaptainDown = false;

void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL P2_CAPTAIN_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

// Fixture-only equivalent of root scripts/p2_fixture_captain_guard.h. CI is
// standalone native, so this observer carries the same fail-closed semantics.
void requireCaptain(Navi* n, int tick) {
    const float hp=n?n->mHealth:0;
    const bool dead=!n || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead;
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


// Scripted-pad observer: no direct production switch call is used. Unsafe and
// knockout setup is explicitly injected and cannot establish natural combat.
class CaptainSwitchApp final : public PlugPikiApp {
    int frames=0, tick=-1;
    Navi *a=nullptr,*b=nullptr;
    Vector3f movementStart;
    float dragStart=0;
    int zoomStart=0;
    bool sawGather=false,sawFlying=false;
    Piki* heldPiki=nullptr;
    int deathTransitions=0, firstDeadTick=-1, damagedFormation=0;
    bool previousDead=false;
    std::vector<Piki*> squad;
    std::vector<Navi*> owners;
    bool screenshot=false;
    void pad(unsigned keys=0,int x=0,int y=0) { pc_p2_input_script_set(1,keys,x,y); }
    int squadFacts(const char* phase) {
        int owned=0, free=0, near=0, index=0; float closest=1.0e9f;
        for(Piki* p:squad) {
            const Vector3f delta=p->getPosition()-b->mCursorWorldPos;
            std::printf("P2_SWITCH_PIKI phase=%s index=%d owner=%d mode=%d state=%d alive=%d callable=%d buried=%d cursor_distance=%.2f pos=%.2f,%.2f,%.2f\n",
                phase,index++,p->mNavi?p->mNavi->mNaviID:-1,p->mMode,p->getState(),int(p->isAlive()),int(p->mIsCallable),int(p->isBuried()),
                std::sqrt(delta.x*delta.x+delta.z*delta.z),p->getPosition().x,p->getPosition().y,p->getPosition().z);
            if(!p->isAlive())continue;
            if(p->mMode==PikiMode::FreeMode)++free;
            if(p->mNavi==b && p->mMode==PikiMode::FormationMode) {
                ++owned; const float distance=(p->getPosition()-b->getPosition()).length();
                if(distance<closest)closest=distance;
                if(distance<80 && p->getState()==PIKISTATE_Normal && p->isThrowable())++near;
            }
        }
        std::printf("P2_SWITCH_SQUAD phase=%s tick=%d owned1=%d free=%d nearby_throwable=%d closest=%.2f cursor=%.2f,%.2f captain=%.2f,%.2f\n",
            phase,tick,owned,free,near,closest,b->mCursorWorldPos.x,b->mCursorWorldPos.z,b->getPosition().x,b->getPosition().z);
        return near;
    }
    void active(int slot) {
        require(naviMgr->getActiveNavi()->mNaviID==slot,"selected captain");
        Navi* n=slot?b:a;
        require(cameraMgr->mController==n->mKontroller,"camera controller selection");
        require(cameraMgr->mCamera->mTargetCreature==n,"camera target selection");
        std::printf("P2_SWITCH_SELECTED tick=%d slot=%d camera=1\n",tick,slot);
    }
public:
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if(tick>40 && !screenshot) screenshot=capture("captain-switch.ppm");
    }
    int idle() override {
        int result=PlugPikiApp::idle();
        require(++frames<1800,"fixture frame bound");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip(); return result;
        }
        if(!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi()) return result;
        requireCaptain(naviMgr->getActiveNavi(),tick);
        if(gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        if(tick<0) {
            a=naviMgr->getNavi(0);
            if(a->getCurrState()->getID()!=NAVISTATE_Walk) return result;
            if(!sSingle) {b=naviMgr->getNavi(1); require(b!=nullptr,"second captain exists");}
            if(b && b->getCurrState()->getID()!=NAVISTATE_Walk) return result;
            Iterator it(pikiMgr); CI_LOOP(it) {
                auto* p=static_cast<Piki*>(*it);
                if(p && p->isAlive()){squad.push_back(p);owners.push_back(p->mNavi);}
            }
            require(squad.size()==20,"fresh live squad exactly20");
            std::printf("P2_SWITCH_ADOPTION live=20 active_gameplay=1 extinction=0 captains=%d\n",naviMgr->getNaviCount());
            tick=0;pad();
            if(sForceCaptainDown) { a->mHealth=0;requireCaptain(a,tick); }
            return result;
        }
        ++tick;
        Navi* selected=naviMgr->getActiveNavi();
        requireCaptain(selected,tick);
        if(sSingle || sCoop) {
            require(!pc_p2_captain::single_player_switch_enabled(),"single/co-op excluded");
            if(tick==5) pad(KBBTN_DPAD_UP);
            if(tick==20) {require(naviMgr->getActiveNavi()==a,"excluded mode no switch");pad();}
            if(tick==50) {
                std::printf("P2_SWITCH_EXCLUSION single=%d coop=%d observed=1\n",int(sSingle),int(sCoop));
                std::puts("PASS P2_CAPTAIN_SWITCH_RUNTIME");std::fflush(nullptr);std::_Exit(0);
            }
            return result;
        }
        if(tick<90) for(size_t i=0;i<squad.size();++i) require(squad[i]->mNavi==owners[i],"switch preserved squad ownership");
        if(tick>8 && tick<55) {
            require(a->mKontroller->mCurrentInput==0 && a->mKontroller->mMainStickX==0,"inactive neutral controls");
        }
        int state=selected->getCurrState()->getID();
        if(tick>=175 && tick<245 && state==NAVISTATE_Gather)sawGather=true;
        Iterator it(pikiMgr); CI_LOOP(it) {
            auto* p=static_cast<Piki*>(*it);
            if(p && p->isAlive() && p->mNavi==b && tick>=250 && tick<290
                && p->getState()==PIKISTATE_Hanged) {
                require(!heldPiki || heldPiki==p,"one held Pikmin identity");heldPiki=p;
            }
            if(heldPiki && p==heldPiki && tick>290 && p->isAlive()
                && p->getState()==PIKISTATE_Flying)sawFlying=true;
        }
        if(tick>380) {
            Navi* downed=sPrimaryDown?a:b;
            require(selected==(sPrimaryDown?b:a),"survivor remains selected on repeated frames and held Up");
            require(cameraMgr->mController==selected->mKontroller && cameraMgr->mCamera->mTargetCreature==selected,"survivor camera remains bound");
            const bool dead=naviMgr->isNaviDead(downed);
            if(dead && !previousDead) { ++deathTransitions;firstDeadTick=tick; }
            require(!previousDead || dead,"native death roster remains recorded");previousDead=dead;
            if(dead) {
                int formation=0,live=0;Iterator liveIt(pikiMgr);CI_LOOP(liveIt) {
                    auto* p=static_cast<Piki*>(*liveIt);if(!p || !p->isAlive())continue;++live;
                    if(p->mNavi==downed && p->mMode==PikiMode::FormationMode)++formation;
                }
                require(formation==0,"native death released original formation");
                require(live==20,"survivor retains fresh live Pikmin population");
            }
        }
        switch(tick) {
        case 5:pad(KBBTN_DPAD_UP);break;
        case 10:active(1);break;
        case 15:active(1);pad();break;
        case 16:
            dragStart=cameraMgr->mCamera->mPolarDir.mAzimuth;
            pc_window_add_camera_drag_player(0,0.1f);break;
        case 17:
            require(pc_window_take_camera_drag_player(0)==0,"selected camera consumed physical player0 drag");
            require(std::abs(cameraMgr->mCamera->mPolarDir.mAzimuth-dragStart)>0.2f,"selected camera rotated from queued drag");
            std::puts("P2_SWITCH_CAMERA drag_queue_player=0 consumed=1 rotated=1");break;
        case 25:movementStart=b->getPosition();pad(0,60,0);break;
        case 40: {
            Vector3f delta=b->getPosition()-movementStart;
            require(delta.length()>1,"selected captain walked");
            std::printf("P2_SWITCH_MOVE distance=%.3f inactive_input=0 ownership_preserved=1\n",delta.length());pad();break;
        }
        case 45:zoomStart=cameraMgr->mCamera->mZoomLevel;pad(KBBTN_R);break;
        case 50:
            require(cameraMgr->mCamera->mZoomLevel!=zoomStart,"selected captain camera zoom through live pad");
            std::puts("P2_SWITCH_CAMERA pad_zoom=1");pad();break;
        case 55:pad(KBBTN_DPAD_UP);break;
        case 60:active(0);break;
        case 65:pad();break;
        case 75:pad(KBBTN_DPAD_UP);break;
        case 80:active(1);break;
        case 85:pad();break;
        // The other captain's formation cannot be stolen by a whistle.
        // Disband it through its owner's real input only AFTER preservation
        // assertions, then recruit through the selected captain's whistle.
        case 95:pad(KBBTN_DPAD_UP);break;
        case 100:active(0);pad();break;
        case 110:pad(KBBTN_X);break;
        case 115:pad();squadFacts("disbanding");break;
        case 160:require(a->getCurrState()->getID()==NAVISTATE_Walk,"owner finished disbanding");pad(KBBTN_DPAD_UP);break;
        case 165:active(1);pad();break;
        case 170: {
            // Clear the stock ship collision volume for this input observation.
            // Use observed live landing terrain rather than assuming every
            // staged room has collision beneath the prototype's origin.
            Vector3f open=a->getPosition();open.y=mapMgr->getMinY(open.x,open.z,true)+1;
            b->resetPosition(open);a->resetPosition(open+Vector3f(25,0,20));break;
        }
        case 175: {
            int staged=0;
            for(Piki* p:squad) {
                require(p->isAlive() && p->mMode==PikiMode::FreeMode,"live disbanded squad before spatial staging");
                Vector3f pos=b->mCursorWorldPos+Vector3f((staged%5-2)*4,0,(staged/5-2)*4);
                pos.y=mapMgr->getMinY(pos.x,pos.z,true)+1;p->resetPosition(pos);
                p->mVelocity=p->mTargetVelocity=Vector3f(0,0,0);++staged;
            }
            std::printf("P2_SWITCH_STAGE free_positions_injected=%d captain_positions_injected=2 ownership_injected=0\n",staged);
            squadFacts("before_whistle");pad(KBBTN_B);break;
        }
        case 235:pad();break;
        case 245:require(sawGather,"selected captain whistle state");require(squadFacts("after_whistle")>0,"selected captain recruited nearby throwable squad");break;
        case 250:pad(KBBTN_A);break;
        case 280:squadFacts("hold");require(heldPiki && heldPiki->isAlive() && heldPiki->getState()==PIKISTATE_Hanged,"selected captain actually holds identified Pikmin");pad(KBBTN_A|KBBTN_DPAD_UP);break;
        case 288:active(1);require(heldPiki && heldPiki->getState()==PIKISTATE_Hanged,"held Pikmin retained during rejected switch");std::puts("P2_SWITCH_UNSAFE held_rejected=1");break;
        case 290:pad();break;
        case 325:require(sawFlying,"selected captain threw Pikmin through live input");std::puts("P2_SWITCH_ACTIONS whistle=1 identified_hanged=1 same_pikmin_flying_after_release=1");break;
        case 330:require(pc_p2_captain::capture_captain(0,928),"inject target captivity");break;
        case 335:pad(KBBTN_DPAD_UP);break;
        case 340:active(1);std::puts("P2_SWITCH_UNSAFE injected_captive_rejected=1");break;
        case 345:pad();require(pc_p2_captain::release_captain(0,928),"release injected captivity");break;
        case 355:a->mHealth=0;break;
        case 360:pad(KBBTN_DPAD_UP);break;
        case 365:active(1);std::puts("P2_SWITCH_UNSAFE injected_zero_health_rejected=1");break;
        case 370:pad();a->mHealth=100;break;
        case 375:if(sPrimaryDown)pad(KBBTN_DPAD_UP);break;
        case 378:if(sPrimaryDown){active(0);pad();}break;
        case 380: {
            Navi* downed=sPrimaryDown?a:b;Iterator before(pikiMgr);CI_LOOP(before) {
                auto* p=static_cast<Piki*>(*before);if(p && p->isAlive() && p->mNavi==downed && p->mMode==PikiMode::FormationMode)++damagedFormation;
            }
            // Keep Up physically held across lethal damage; this must not become
            // a fresh switch edge or bounce control back during death animation.
            pad(KBBTN_DPAD_UP);
            InteractAttack hit(nullptr,nullptr,500.0f,false);hit.actNavi(downed);
            std::puts("P2_SWITCH_SURVIVOR injected_attack_receiver=1");break;
        }
        case 390:active(sPrimaryDown?1:0);break;
        case 420:pad();break;
        case 550:
            require(deathTransitions==1 && firstDeadTick>380,"one native death roster transition after attack");
            std::printf("P2_SWITCH_SURVIVOR primary_down=%d active=%d death_transitions=%d first_dead_tick=%d formation_before=%d formation_after=0 repeated_frames=170 held_up_no_bounce=1\n",int(sPrimaryDown),naviMgr->getActiveNavi()->mNaviID,deathTransitions,firstDeadTick,damagedFormation);
            require(screenshot,"render capture");std::puts("PASS P2_CAPTAIN_SWITCH_RUNTIME");std::fflush(nullptr);std::_Exit(0);
        }
        if(tick%10==0) {std::printf("P2_SWITCH_TICK tick=%d active=%d states=%d,%d\n",tick,naviMgr->getActiveNavi()->mNaviID,a->getCurrState()->getID(),b->getCurrState()->getID());std::fflush(stdout);}
        return result;
    }
};
} // namespace
int main(int argc,char** argv) {
    for(int i=1;i<argc;++i){sSingle|=std::string(argv[i])=="--single";sCoop|=std::string(argv[i])=="--coop";sPrimaryDown|=std::string(argv[i])=="--primary-down";sForceCaptainDown|=std::string(argv[i])=="--force-captain-down";}
    _putenv_s("PIKMIN_P2_SECOND_CAPTAIN",sSingle?"0":"1");
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
    pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"experimental room required");
    if(!pc_window_init("P2 Captain switch acceptance",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2 && std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;
    require(w==960 && h==540 && centered,"fresh fixture window baseline after settings");
    std::printf("P2_SWITCH_WINDOW size=%dx%d pos=%d,%d centered=%d after_settings=1\n",w,h,x,y,int(centered));std::fflush(stdout);
    pc_coop_set_pending(sCoop);pc_p2_input_script_set(1,0);pc_p2_input_script_set(2,0);
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CaptainSwitchApp());return 0;
}

