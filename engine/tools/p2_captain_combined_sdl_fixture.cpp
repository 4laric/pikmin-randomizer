// #1130 current combined ordinary SDL native save/resume, switching, movement
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
#include "KeyConfig.h"
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
// Legacy inline UI helpers omit unused switch cases. Keep fixture warnings
// strict while allowing this unchanged production header's existing warnings.
#if defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wswitch"
#endif
#include "zen/DrawContainer.h"
#if defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

namespace {
SDL_Joystick* virtualPad=nullptr;
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
    int diaryFrames=0, menuFrames=0, withdrawFrames=0;
    bool withdrawConfirmQueued=false;
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
    void pad(unsigned keys=0,int x=0,int y=0){
        const int id=SDL_JoystickInstanceID(virtualPad);int selected=-1;
        if(pc_window_input_get_assignment(0,&selected)!=PC_INPUT_DEV_GAMEPAD||selected!=id){pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,id);pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);}
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_START,(keys&KBBTN_START)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_UP,(keys&KBBTN_DPAD_UP)!=0);
        SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
        SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));SDL_JoystickUpdate();
    }
    void selected(int slot){auto* n=naviMgr->getNavi(slot);require(naviMgr->getActiveNavi()==n,"selected captain");require(cameraMgr->mController==n->mKontroller && cameraMgr->mCamera->mTargetCreature==n,"camera binding");std::printf("P2_SAVE_SELECTED phase=%s slot=%d camera=1\n",resumePhase?"resume":"save",slot);}
public:
    CaptainSaveApp(){initialCards=cards();require(resumePhase?initialCards==1:initialCards==0,"expected committed generation before phase");}
    void draw(Graphics& gfx)override{PlugPikiApp::draw(gfx);if(tick>30&&!shot)shot=capture("captain-campaign.ppm");if(saving&&menuFrames==120)require(capture("pause-menu.ppm"),"ordinary pause menu capture");if(resumePhase&&withdrawQueued&&frames%240==0){const std::string path="onion-menu-"+std::to_string(frames)+".ppm";require(capture(path.c_str()),"ordinary Onion menu capture");}}
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

        if(resumePhase&&withdrawQueued&&tick<0&&frames%120==0){
            auto* a=naviMgr?naviMgr->getNavi(0):nullptr;auto* b=naviMgr?naviMgr->getNavi(1):nullptr;
            std::printf("P2_SAVE_RESUME_GATE frame=%d ready=%d pause=%d overlay=%d movie=%d active_state=%d inactive_state=%d ui_state=%d squad=%d stock=%d\n",frames,int(pc_randomizer_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),a&&a->getCurrState()?a->getCurrState()->getID():-1,b&&b->getCurrState()?b->getCurrState()->getID():-1,containerWindow?int(containerWindow->getStatus()):-1,containerWindow?containerWindow->getMyPikiDisp():-1,containerWindow?containerWindow->getContainerPikiDisp():-1);std::fflush(stdout);
        }

        if(resumePhase&&tick<0&&!withdrawQueued){
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
            if(!confirming){
                ++menuFrames;
                if(menuFrames<=3||menuFrames==45||menuFrames==50||menuFrames==65||menuFrames==66||menuFrames==125||menuFrames==126||menuFrames%120==0){
                    auto* core=findCore(gameflow.mGameSection);auto* ui=core?core->mController:nullptr;
                    std::printf("P2_SAVE_UI_OBSERVER frame=%d allowed=%d overlay=%d paused=%d movie=%d player_day=%d ui_present=%d held=%08x pressed=%08x frozen=%d axis_y=%.3f\n",menuFrames,int(gameflow.mIsPauseAllowed),int(gameflow.mIsUIOverlayActive),int(gameflow.mPauseAll),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),playerState->getCurrDay(),int(ui!=nullptr),ui?unsigned(ui->mCurrentInput):0,ui?unsigned(ui->mInputPressed):0,ui?int(ui->mIsControllerFrozen):-1,ui?ui->mMainStickY:0.0f);
                    std::fflush(stdout);
                }
                if(menuFrames==2)pad(); // Release START after its ordinary input edge.
                if(menuFrames==45)pad(0,0,-65); // Continue -> Go to Sunset.
                else if(menuFrames==50)pad();
                // Main-menu exit and submenu entry each take0.5s, followed
                // by the submenu's0.1s active delay. Wait beyond both fades.
                else if(menuFrames==65||menuFrames==125)pad(KBBTN_A); // Sunset, then Yes.
                else if(menuFrames==66||menuFrames==126)pad();
                if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive)gameflow.mMoviePlayer->requestSkip();
                return result;
            }
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
        if(!pc_randomizer_enabled()||!pc_randomizer_ready()||!naviMgr||!naviMgr->getActiveNavi()||(gameflow.mPauseAll && !(resumePhase&&withdrawQueued))||(gameflow.mIsUIOverlayActive && !(resumePhase&&withdrawQueued)))return result;
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);require(a&&b,"two campaign captains");
        if(!a->getCurrState()||!b->getCurrState())return result; // Initial startup readiness; initialized guards above fail closed.
        if(tick<0){
            // After established resume readiness the inactive captain may
            // naturally idle while ordinary Onion UI input runs. The live
            // initialized captain guard remains mandatory before this check.
            const bool inactiveReady=b->getCurrState()->getID()==NAVISTATE_Walk
                ||(resumePhase&&withdrawQueued&&b->getCurrState()->getID()==NAVISTATE_Idle);
            if((a->getCurrState()->getID()!=NAVISTATE_Walk && !(resumePhase&&withdrawQueued&&a->getCurrState()->getID()==NAVISTATE_Container))||!inactiveReady)return result;
            require(pc_randomizer_resumed()==resumePhase,"actual production campaign load state");
            startDay=gameflow.mWorldClock.mCurrentDay;
            int live=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++live;}
            if(resumePhase){
                if(!withdrawQueued){
                    require(live==0 && storedCount()>=20,"restored stock before ordinary withdrawal");
                    GoalItem* onion=itemMgr?itemMgr->getContainer(pc_randomizer_start_color()):nullptr;
                    require(onion&&onion->getTotalStorePikis()>=20,"restored starting-color Onion stock");
                    withdrawnFromTotal=live+storedCount();withdrawQueued=true;
                    std::printf("P2_SAVE_WITHDRAW_UI_BEGIN total_before=%d direct_exitPikis=0\n",withdrawnFromTotal);
                }
                if(live<20){
                    GoalItem* onion=itemMgr->getContainer(pc_randomizer_start_color());require(onion,"Onion unavailable");
                    if(a->getCurrState()->getID()==NAVISTATE_Container){
                        ++withdrawFrames;
                        require(containerWindow,"ordinary Onion window unavailable");
                        const int uiState=containerWindow->getStatus(), squad=containerWindow->getMyPikiDisp(), stock=containerWindow->getContainerPikiDisp();
                        if(withdrawFrames==1||withdrawFrames%30==0){std::printf("P2_SAVE_ONION_OBSERVER frame=%d state=%d squad=%d stock=%d live=%d stored=%d active_state=%d inactive_state=%d\n",withdrawFrames,uiState,squad,stock,live,storedCount(),a->getCurrState()->getID(),b->getCurrState()->getID());std::fflush(stdout);}
                        require(squad<=20,"ordinary Onion UI selection exceeds20");
                        if(uiState==zen::DrawContainer::STATE_Operation && squad==20){pad(withdrawConfirmQueued?KBBTN_A:0);withdrawConfirmQueued=true;}
                        else pad(0,0,uiState==zen::DrawContainer::STATE_Operation?-65:0);
                        if(withdrawFrames==1)std::puts("P2_SAVE_ONION_UI opened=1 direction=withdraw input=SDL_virtual");
                    }else if(withdrawFrames==0){
                        const Vector3f goal=onion->getPosition();float dx=goal.x-a->getPosition().x,dz=goal.z-a->getPosition().z,d=std::sqrt(dx*dx+dz*dz);
                        const Vector3f axis=a->controlCamera()->mViewXAxis;
                        if(d>12)pad(0,int(65*(dx*axis.x+dz*axis.z)/d),int(65*(dx*axis.z-dz*axis.x)/d));
                        else pad(frames%20<2?KBBTN_A:0);
                    }else pad();
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
            {pad(KBBTN_START);saving=true;elapsed("ordinary_pause_requested");std::puts("P2_SAVE_SUNSET ordinary_pause_UI=1 direct_forceDayEnd=0 dayendflag_writes=0");}
            break;
        }
        std::fflush(stdout);return result;
    }
};
} // namespace
int main(int argc,char** argv){
    for(int i=1;i<argc;++i){resumePhase|=std::string(argv[i])=="--resume-phase";sForceCaptainDown|=std::string(argv[i])=="--force-captain-down";sForceInactiveDown|=std::string(argv[i])=="--force-inactive-down";forceNullState|=std::string(argv[i])=="--force-null-state";forceMissingManager|=std::string(argv[i])=="--force-missing-manager";}
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_randomizer_second_captain(),"generated bootstrap captain option required");
    require(pc_randomizer_enabled()&&!pc_pikipelago_room_preview(),"ordinary randomizer campaign required");
    if(!pc_window_init("Captain native campaign save/resume",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&bounds);
    require(width==960&&height==540&&std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2,"centered fixture baseline");
    std::printf("P2_SAVE_WINDOW size=%dx%d centered=1 after_settings=1\n",width,height);
    pc_coop_set_pending(false);
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    const int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"attach virtual");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    const std::string mapping=std::string(guid)+",Combined captain SDL pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
    require(SDL_GameControllerAddMapping(mapping.c_str())>=0 && SDL_IsGameController(device),"mapped SDL virtual controller");
    virtualPad=SDL_JoystickOpen(device);require(virtualPad&&SDL_JoystickIsVirtual(device),"actual virtual P1");
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(virtualPad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    std::printf("P2_SAVE_SDL_ROUTING instance=%d virtual=1 player=1 input_script=0 background_test_seam=1\n",int(SDL_JoystickInstanceID(virtualPad)));
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CaptainSaveApp());return 0;
}
