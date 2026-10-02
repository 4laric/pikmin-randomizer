// #1166 offline P1 SDL switched-captain Onion ownership, ordinary save/load.
// Derived from #1130; no production state writes on the positive path.
#include <SDL2/SDL.h>
#include <GL/gl.h>
// MinGW's GL headers restore WIN32 after -UWIN32. Engine headers reserve
// that spelling for the incompatible legacy renderer; keep host _WIN32.
#if defined(_WIN32) && defined(WIN32)
#undef WIN32
#endif
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
#include "pc_diary_observer.h"
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
    enum OwnerStage { Boot, Deposit, SwitchOne, Withdraw, Settle, Owned };
    OwnerStage ownerStage=Boot;
    int ownerFrames=0, switchFrames=0;
    bool menuSeen=false, menuConfirm=false;
    int menuFrames=0, diaryActions=0;
    bool releaseDiaryInput=false;
    bool diaryRevealObserved=false, diaryAdvanceObserved=false;
    PcDiaryAction lastDiaryAction=PcDiaryAction::Unavailable;
    void elapsed(const char* phase){std::printf("P2_SAVE_TIME phase=%s elapsed_ms=%lld\n",phase,(long long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count());}
    bool saving=false,shot=false,sawWhistle=false,initialized[2]={false,false},retired=false;
    int teardownGapFrames=0;
    int controlStage=0;
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
    int liveCount(){int n=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++n;}return n;}
    // validSlot observes the used-slot boundary without accessing protected layout.
    // More occupied slots than live Pikmin fails the observation immediately.
    int plateCount(Navi* n){require(n&&n->mPlateMgr,"captain plate exists");int limit=liveCount();for(int i=0;i<=limit;++i)if(!n->mPlateMgr->validSlot(i))return i;require(false,"plate exceeds live population");return -1;}
    int formation(Navi* n){int count=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mMode==PikiMode::FormationMode&&p->mNavi==n)++count;}return count;}
    void owned(const char* stage){
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);
        require(liveCount()==20&&storedCount()==0,"owned field20 stock0");
        require(formation(a)==0&&formation(b)==20,"all20 actual formation owner captain1");
        require(a->mPlateMgr&&b->mPlateMgr&&plateCount(a)==0&&plateCount(b)==20,"CPlate agrees with observed ownership");
        if(stage)std::printf("P2_ONION_OWNER stage=%s owner0=0 owner1=20 plate0=0 plate1=20 live=20 stored=0 input_player=1 switched_captain=1\n",stage);
    }
    void onionMenu(Navi* n,int target){
        require(naviMgr->getActiveNavi()==n,"Onion input owner is selected captain");
        auto* onion=itemMgr?itemMgr->getContainer(pc_randomizer_start_color()):nullptr;require(onion,"real starting Onion");
        if(n->getCurrState()->getID()==NAVISTATE_Container){
            require(containerWindow,"ordinary offline Onion UI");
            const int state=containerWindow->getStatus(), squad=containerWindow->getMyPikiDisp();
            if(!menuSeen){menuSeen=true;elapsed(target?"withdraw_menu_open":"deposit_menu_open");}
            if(ownerFrames%30==0)std::printf("P2_ONION_MENU captain=%d target=%d displayed=%d stock=%d live=%d state=%d\n",n->mNaviID,target,squad,storedCount(),liveCount(),state);
            require(squad>=0&&squad<=20,"ordinary menu selection bounded20");
            if(state==zen::DrawContainer::STATE_Operation&&squad==target){pad(menuConfirm?KBBTN_A:0);menuConfirm=true;}
            else pad(0,0,state==zen::DrawContainer::STATE_Operation?(target? -65:65):0);
        }else if(!menuSeen){
            const Vector3f goal=onion->getPosition();const float dx=goal.x-n->getPosition().x,dz=goal.z-n->getPosition().z,d=std::sqrt(dx*dx+dz*dz);
            const Vector3f axis=n->controlCamera()->mViewXAxis;
            if(d>12)pad(0,int(65*(dx*axis.x+dz*axis.z)/d),int(65*(dx*axis.z-dz*axis.x)/d));
            else pad(frames%20<2?KBBTN_A:0);
        }else pad();
    }
public:
    CaptainSaveApp(){initialCards=cards();require(resumePhase?initialCards==1:initialCards==0,"expected committed generation before phase");}
    void draw(Graphics& gfx)override{PlugPikiApp::draw(gfx);if(tick>=0&&!shot)shot=capture("captain-campaign.ppm");if(saving&&menuFrames==120)require(capture("pause-menu.ppm"),"ordinary pause menu capture");if(resumePhase&&withdrawQueued&&frames%240==0){const std::string path="onion-menu-"+std::to_string(frames)+".ppm";require(capture(path.c_str()),"ordinary Onion menu capture");}}
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

        if(resumePhase&&tick<0&&!withdrawQueued){
            const bool menu=!naviMgr||gameflow.mIsUIOverlayActive;
            if(menu&&!resumeMenuLogged){resumeMenuLogged=true;std::puts("P2_SAVE_RESUME_MENU ordinary_A_input=1 area_day_injected=0");}
            pad(menu&&frames%20<4?KBBTN_A:0);
        }
        if(saving){
            // Observe actual diary eligibility; ordinary A remains the fallback
            // for results/card prompts. B is never emitted outside eligibility.
            const bool confirming=gameflow.mWorldClock.mCurrentDay==startDay+1;
            if(confirming&&!dayAdvanced){dayAdvanced=true;elapsed("day_advanced");}
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
            const PcDiaryAction diary=pc_diary_observe();
            if(diary!=lastDiaryAction){
                std::printf("P2_ONION_DIARY observed=%d elapsed_stage=diary_eligibility\n",int(diary));
                elapsed("diary_eligibility_changed");lastDiaryAction=diary;
            }
            if(releaseDiaryInput){pad();releaseDiaryInput=false;}
            else if(diary==PcDiaryAction::RevealPage || diary==PcDiaryAction::AdvancePage){
                require(++diaryActions<240,"bounded ordinary diary actions");
                const bool reveal=diary==PcDiaryAction::RevealPage;
                diaryRevealObserved|=reveal;diaryAdvanceObserved|=!reveal;
                pad(reveal?KBBTN_B:KBBTN_A);releaseDiaryInput=true;
                std::printf("P2_ONION_DIARY input=%s observed=%d action=%d ordinary_SDL=1\n",reveal?"B":"A",int(diary),diaryActions);
            }else pad(frames%20<18?KBBTN_A:0); // Ordinary A during fades and results/card; never B.
            if(cards()==initialCards+1 && gameflow.mWorldClock.mCurrentDay==startDay+1){
                require(diaryRevealObserved&&diaryAdvanceObserved,"observed actual diary reveal and advance inputs");
                elapsed("native_commit_observed");
                std::printf("PASS P2_CAPTAIN_ONION_OWNER_SAVE day_before=%d day_after=%d native_card_generation_count=%d scripted_sunset=1 scripted_results_input=1 saved_bytes_injected=0\n",startDay,gameflow.mWorldClock.mCurrentDay,cards());std::fflush(nullptr);std::_Exit(0);
            }
            require(cards()<=initialCards+1,"unexpected extra checkpoint");
        }
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(saving)return result;
        if(!pc_randomizer_enabled()||!pc_randomizer_ready()||!naviMgr||!naviMgr->getActiveNavi()||(gameflow.mPauseAll && !withdrawQueued)||(gameflow.mIsUIOverlayActive && !withdrawQueued))return result;
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);require(a&&b,"two campaign captains");
        if(!a->getCurrState()||!b->getCurrState())return result; // Initial startup readiness; initialized guards above fail closed.
        if(tick<0){
            require(pc_randomizer_resumed()==resumePhase,"actual production campaign load state");
            int live=liveCount();
            if(ownerStage==Boot){
                if(a->getCurrState()->getID()!=NAVISTATE_Walk || b->getCurrState()->getID()!=NAVISTATE_Walk)return result;
                if(!resumePhase && live<20)return result;
                require(resumePhase?live==0:live==20,"actual initial field count");
                require(a->mPlateMgr && b->mPlateMgr,"initialized captain formation plates");
                if(!resumePhase && (formation(a)!=20 || plateCount(a)!=20))return result;
                startDay=gameflow.mWorldClock.mCurrentDay;
                withdrawnFromTotal=live+storedCount();require(withdrawnFromTotal==20,"actual total20 baseline");
                selected(0);withdrawQueued=true;elapsed("ownership_boot");
                if(sForceCaptainDown||sForceInactiveDown||forceNullState||forceMissingManager){pendingNegative=true;gameflow.mPauseAll=TRUE;return result;}
                if(!resumePhase){require(formation(a)==20 && formation(b)==0,"fresh actual captain0 formation20");ownerStage=Deposit;}
                else ownerStage=SwitchOne;
            }
            require(++ownerFrames<1800,"bounded ordinary ownership preparation");
            if(ownerStage==Deposit){
                if(live==0 && storedCount()==20 && a->getCurrState()->getID()!=NAVISTATE_Container){
                    pad();menuSeen=false;menuConfirm=false;ownerStage=SwitchOne;elapsed("deposit20_complete");
                }else{onionMenu(a,0);return result;}
            }
            if(ownerStage==SwitchOne){
                if(switchFrames==0){pad(KBBTN_DPAD_UP);++switchFrames;return result;}
                pad();++switchFrames;
                if(naviMgr->getActiveNavi()!=b){require(switchFrames<60,"SDL switch to captain1");return result;}
                selected(1);require(live==0&&storedCount()==20,"real stock before captain1 withdrawal");
                ownerStage=Withdraw;menuSeen=false;menuConfirm=false;elapsed("captain1_withdraw_begin");
            }
            if(ownerStage==Withdraw){
                if(live==20 && b->getCurrState()->getID()!=NAVISTATE_Container){pad();ownerStage=Settle;elapsed("withdraw20_spawned");}
                else{require(live<=20,"Onion field cap20");onionMenu(b,20);return result;}
            }
            if(ownerStage==Settle){
                pad();require(live+storedCount()==withdrawnFromTotal,"withdrawal conserves actual total");
                if(formation(b)!=20)return result;
                owned("withdraw_complete");ownerStage=Owned;elapsed("captain1_formation20");
            }
            require(live<=20,"campaign field exceeds20live");
            if(live<20)return result; // fresh production TEST_BACKGROUND withdrawal
            require(live==20,"campaign20live baseline");
            require(pc_p2_captain::adapter()&&pc_p2_captain::captive_count()==0,"fresh live binding");
            selected(1);tick=0;elapsed("scene_ready");
            std::printf("P2_SAVE_SCENE phase=%s resumed=%d day=%d live=%d stored=%d health0=%.3f health1=%.3f active_selected=1 ownership_observed_after_UI=1 ownership_restoration_not_assumed=1\n",resumePhase?"resume":"save",int(pc_randomizer_resumed()),startDay,live,storedCount(),a->mHealth,b->mHealth);
            if(sForceCaptainDown||sForceInactiveDown||forceNullState||forceMissingManager){
                pendingNegative=true;gameflow.mPauseAll=TRUE;return result;
            }
        }
        owned(nullptr);
        if(b->getCurrState()->getID()==NAVISTATE_Gather)sawWhistle=true;
        require(++tick<180,"bounded ownership switch/whistle control stages");
        // Replace the old100-tick movement demonstration with observation-gated
        // ownership switches and whistle. Walking to the Onion already exercises
        // actual selected movement; no additional mirrored-input claim is made.
        switch(controlStage){
        case 0:pad(KBBTN_DPAD_UP);controlStage=1;break;
        case 1:
            pad();if(naviMgr->getActiveNavi()!=a)break;
            selected(0);owned("switched_to0");elapsed("switch0_owner_retained");controlStage=2;break;
        case 2:pad(KBBTN_DPAD_UP);controlStage=3;break;
        case 3:
            pad();if(naviMgr->getActiveNavi()!=b)break;
            selected(1);owned("switched_back1");elapsed("switch1_owner_retained");controlStage=4;break;
        case 4:pad(KBBTN_B);controlStage=5;break;
        case 5:
            if(!sawWhistle)break;
            pad();owned("whistle1");elapsed("whistle1_observed");controlStage=6;break;
        case 6:
            pad();if(!shot)break;
            owned("before_sunset_or_resume_exit");
            if(resumePhase){require(cards()==initialCards,"resume did not commit another generation");std::printf("PASS P2_CAPTAIN_ONION_OWNER_RESUME day=%d generations=%d controls=1 camera=1 onion_movement=1 whistle=1 stored=%d saved_bytes_injected=0\n",startDay,cards(),storedCount());std::fflush(nullptr);std::_Exit(0);}
            pad(KBBTN_START);saving=true;elapsed("ordinary_pause_requested");std::puts("P2_SAVE_SUNSET ordinary_pause_UI=1 direct_forceDayEnd=0 dayendflag_writes=0");
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
