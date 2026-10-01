// #1079 bounded native campaign save/resume with scripted switching, movement
// and actual native card commit/load; scripted sunset/results input is disclosed.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "CPlate.h"
#include "GameCoreSection.h"
#include "GameStat.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "Section.h"
#include "BaseInf.h"
#include "PlayerState.h"
#include "pc_randomizer.h"
#include <filesystem>
#include <fstream>
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
#include <chrono>
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




GameCoreSection* findCore(CoreNode* node,int depth=0){
    if(!node||depth>20)return nullptr;
    if(auto* c=dynamic_cast<GameCoreSection*>(node))return c;
    for(auto* c=node->Child();c;c=c->Next())if(auto* found=findCore(c,depth+1))return found;
    return nullptr;
}
bool resumePhase=false,forceNullState=false,forceMissingManager=false;
int storedCount(){int n=0;for(int c=0;c<3;++c)for(int m=0;m<3;++m)n+=pikiInfMgr.mPikiCounts[c][m];return n;}
int cards(){int n=0;const auto d=std::filesystem::path("../../campaign");if(std::filesystem::exists(d))for(auto& f:std::filesystem::directory_iterator(d))if(f.path().extension()==".sav")++n;return n;}
class CaptainSaveApp final:public PlugPikiApp {
    int frames=0,tick=-1,startDay=-1,initialCards=0;
    const std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
    bool dayAdvanced=false,resumeMenuLogged=false,withdrawQueued=false;
    int withdrawnFromTotal=-1;
    int diaryFrames=0;
    void elapsed(const char* phase){std::printf("P2_SAVE_TIME phase=%s elapsed_ms=%lld\n",phase,(long long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count());}
    bool saving=false,shot=false,sawWhistle=false,initialized[2]={false,false},retired=false;
    int teardownGapFrames=0;
    Vector3f movementStart,inactiveStart;
    bool pendingNegative=false;
    void guardLiveState(){
        if(retired){require(!naviMgr && !pc_p2_captain::adapter(),"unexpected captain rebirth during bounded map gap");require(++teardownGapFrames<180,"bounded expected map transition gap");return;}
        if(!naviMgr && (initialized[0]||initialized[1])){
            // Only the actual quitter path may retire initialized captains:
            // exitStage unbinds the adapter and nulls NaviMgr, then queues map
            // selection and softReset after the native day advances.
            const bool actualExit=saving && !pc_p2_captain::adapter() && gsys->resetPending()
                && gameflow.mNextOnePlayerSectionID==ONEPLAYER_MapSelect
                && gameflow.mWorldClock.mCurrentDay==startDay+1;
            if(!actualExit)requireCaptain(nullptr,tick);
            retired=true;teardownGapFrames=0;
            std::puts("P2_SAVE_TEARDOWN actual_quitter_map_soft_reset=1 bounded_gap=180");return;
        }
        if(naviMgr)for(int i=0;i<2;++i){auto* n=naviMgr->getNavi(i);
            if(n&&n->getCurrState())initialized[i]=true;
            if(initialized[i])requireCaptain(n,tick);
        }
    }
    void pad(unsigned keys=0,int x=0,int y=0){pc_p2_input_script_set(1,keys,x,y);}
    void selected(int slot){auto* n=naviMgr->getNavi(slot);require(naviMgr->getActiveNavi()==n,"selected captain");require(cameraMgr->mController==n->mKontroller && cameraMgr->mCamera->mTargetCreature==n,"camera binding");std::printf("P2_SAVE_SELECTED phase=%s slot=%d camera=1\n",resumePhase?"resume":"save",slot);}
public:
    CaptainSaveApp(){initialCards=cards();require(resumePhase?initialCards==1:initialCards==0,"expected committed generation before phase");}
    void draw(Graphics& gfx)override{PlugPikiApp::draw(gfx);if(tick>30&&!shot)shot=capture("captain-campaign.ppm");}
    int idle()override{
        if(pendingNegative){
            // Queue mutation until the next ordinary pre-engine guard. This
            // avoids rendering a deliberately null state before that guard.
            auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);
            if(forceNullState)b->mCurrState=nullptr;
            else if(forceMissingManager)naviMgr=nullptr;
            else (sForceInactiveDown?b:a)->mHealth=0;
            pendingNegative=false;
        }
        guardLiveState(); // also protects the engine from negative null-state setup
        const int result=PlugPikiApp::idle();require(++frames<7200,"frame bound");
        guardLiveState(); // never bypass initialized actors for movie/readiness/pause

        if(resumePhase&&tick<0){
            const bool menu=!naviMgr||gameflow.mIsUIOverlayActive;
            if(menu&&!resumeMenuLogged){resumeMenuLogged=true;std::puts("P2_SAVE_RESUME_MENU ordinary_A_input=1 area_day_injected=0");}
            pad(menu&&frames%20<4?KBBTN_A:0);
        }
        if(saving){
            // Ordinary held A speeds diary text through ogMessage.cpp; release
            // two frames per cycle preserves edges for results/card prompts.
            const bool confirming=gameflow.mWorldClock.mCurrentDay==startDay+1;
            if(confirming&&!dayAdvanced){dayAdvanced=true;elapsed("day_advanced");}
            // With neutral input the diary cannot leave its first page. One
            // ordinary B reveals it; never repeat B in results/card dialogs.
            if(confirming)++diaryFrames;
            if(diaryFrames==60){pad(KBBTN_B);elapsed("single_diary_B");}
            else if(diaryFrames>61)pad(frames%20<18?KBBTN_A:0);
            else pad();
            if(cards()==initialCards+1 && gameflow.mWorldClock.mCurrentDay==startDay+1){
                elapsed("native_commit_observed");
                std::printf("PASS P2_CAPTAIN_CAMPAIGN_SAVE day_before=%d day_after=%d native_card_generation_count=%d scripted_sunset=1 scripted_results_input=1 saved_bytes_injected=0\n",startDay,gameflow.mWorldClock.mCurrentDay,cards());std::fflush(nullptr);std::_Exit(0);
            }
            require(cards()<=initialCards+1,"unexpected extra checkpoint");
        }
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(saving)return result;
        if(!pc_randomizer_enabled()||!pc_randomizer_ready()||!naviMgr||!naviMgr->getActiveNavi()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);require(a&&b,"two campaign captains");
        if(tick<0){
            if(a->getCurrState()->getID()!=NAVISTATE_Walk||b->getCurrState()->getID()!=NAVISTATE_Walk)return result;
            require(pc_randomizer_resumed()==resumePhase,"actual production campaign load state");
            startDay=gameflow.mWorldClock.mCurrentDay;
            int live=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++live;}
            if(resumePhase){
                if(!withdrawQueued){
                    require(live==0 && storedCount()>=20,"restored stock before ordinary withdrawal");
                    GoalItem* onion=itemMgr?itemMgr->getContainer(pc_randomizer_start_color()):nullptr;
                    require(onion&&onion->getTotalStorePikis()>=20,"restored starting-color Onion stock");
                    withdrawnFromTotal=live+storedCount();withdrawQueued=true;onion->exitPikis(20);
                    std::printf("P2_SAVE_WITHDRAW queued=20 actual_exitPikis=1 total_before=%d injected_population=0\n",withdrawnFromTotal);
                    return result;
                }
                require(live<=20,"ordinary withdrawal exceeded20live");
                if(live<20)return result;
                require(live+storedCount()==withdrawnFromTotal,"ordinary withdrawal population conservation");
            }
            require(live<=20,"campaign field exceeds20live");
            if(live<20)return result; // fresh production TEST_BACKGROUND withdrawal
            require(live==20,"campaign20live baseline");
            require(pc_p2_captain::adapter()&&pc_p2_captain::captive_count()==0,"fresh live binding");
            selected(0);tick=0;elapsed("scene_ready");
            std::printf("P2_SAVE_SCENE phase=%s resumed=%d day=%d live=%d stored=%d health0=%.3f health1=%.3f active_reset=0 ownership_restoration_not_assumed=1\n",resumePhase?"resume":"save",int(pc_randomizer_resumed()),startDay,live,storedCount(),a->mHealth,b->mHealth);
            if(sForceCaptainDown||sForceInactiveDown||forceNullState||forceMissingManager){
                pendingNegative=true;gameflow.mPauseAll=TRUE;return result;
            }
        }
        if(b->getCurrState()->getID()==NAVISTATE_Gather)sawWhistle=true;
        ++tick;
        switch(tick){
        case 5:pad(KBBTN_DPAD_UP);break;
        case 15:selected(1);break;
        case 20:pad();movementStart=b->getPosition();inactiveStart=a->getPosition();break;
        case 25:pad(0,60,0);break;
        case 45:{const float d=(b->getPosition()-movementStart).length();require(d>1,"selected walks");const Vector3f delta=a->getPosition()-inactiveStart;const float inactive=std::sqrt(delta.x*delta.x+delta.z*delta.z);require(inactive<2.0f,"inactive captain horizontal position stable during selected input");std::printf("P2_SAVE_MOVE distance=%.3f inactive_xz=%.3f\n",d,inactive);pad();break;}
        case 50:pad(KBBTN_B);break;
        case 65:require(sawWhistle,"selected whistle input");pad();break;
        case 75:pad(KBBTN_DPAD_UP);break;
        case 85:selected(0);pad();break;
        case 100:
            require(shot,"render capture");
            if(resumePhase){require(cards()==initialCards,"resume did not commit another generation");std::printf("PASS P2_CAPTAIN_CAMPAIGN_RESUME day=%d generations=%d controls=1 camera=1 movement=1 whistle=1 stored=%d saved_bytes_injected=0\n",startDay,cards(),storedCount());std::fflush(nullptr);std::_Exit(0);}
            {auto* core=findCore(gameflow.mGameSection);require(core,"live campaign core");pad();core->forceDayEnd();gameflow.mIsDayEndTriggered=TRUE;saving=true;elapsed("ordinary_sunset_requested");std::puts("P2_SAVE_SUNSET ordinary_forceDayEnd=1 injected_day=0 injected_population=0");}
            break;
        }
        std::fflush(stdout);return result;
    }
};
} // namespace
int main(int argc,char** argv){
    for(int i=1;i<argc;++i){resumePhase|=std::string(argv[i])=="--resume-phase";sForceCaptainDown|=std::string(argv[i])=="--force-captain-down";sForceInactiveDown|=std::string(argv[i])=="--force-inactive-down";forceNullState|=std::string(argv[i])=="--force-null-state";forceMissingManager|=std::string(argv[i])=="--force-missing-manager";}
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_randomizer_second_captain(),"generated bootstrap captain option required");
    require(pc_randomizer_enabled()&&!pc_pikipelago_room_preview(),"ordinary randomizer campaign required");
    if(!pc_window_init("Captain native campaign save/resume",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&bounds);
    require(width==960&&height==540&&std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2,"centered fixture baseline");
    std::printf("P2_SAVE_WINDOW size=%dx%d centered=1 after_settings=1\n",width,height);
    pc_coop_set_pending(false);pc_p2_input_script_set(1,0);pc_p2_input_script_set(2,0);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CaptainSaveApp());return 0;
}
