// #1166 proposal: native title -> default card -> empty file menu. No game slot selected.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#if defined(_WIN32) && defined(WIN32)
#undef WIN32
#endif
#include "App.h"
#include "BaseInf.h"
#include "Boss.h"
#include "ItemMgr.h"
#include "NaviMgr.h"
#include "PikiMgr.h"
#include "Section.h"
#include "Node.h"
#include "teki.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_blank_card_input.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>

namespace {
SDL_Joystick* pad=nullptr;
std::filesystem::path cardRoot;
void require(bool ok,const char* why){if(!ok){std::printf("FAIL P2_BLANK_CARD_UI %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
void input(bool a){require(SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,a?1:0)==0,"SDL button");SDL_JoystickUpdate();}
bool forbidden(){
    if(naviMgr || pikiMgr || itemMgr || bossMgr || tekiMgr || pc_randomizer_enabled() || pc_bbft_enabled())return true;
    for(int c=0;c<3;++c)for(int m=0;m<3;++m)if(pikiInfMgr.mPikiCounts[c][m])return true;
    return gameflow.mIsChallengeMode || gameflow.mPlayState.mSaveStatus==PlayState::ReadyToSave
        || (gameflow.mCurrGameSectionID==SECTION_OnePlayer && gameflow.mNextOnePlayerSectionID>ONEPLAYER_CardSelect);
}
bool generations(){
    const auto campaign=cardRoot.parent_path();
    if(!std::filesystem::exists(campaign))return false;
    for(const auto& f:std::filesystem::directory_iterator(campaign))if(f.path().extension()==".sav")return true;
    return false;
}
class BlankCardApp final:public PlugPikiApp {
    blankcard::Policy policy;
    unsigned frames=0;
    const std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
public:
    int idle() override {
        require(!forbidden() && !generations(),"pre-engine no gameplay/stock/campaign");
        pc_blank_card_snapshot=PcBlankCardSnapshot{};pc_blank_card_publications=0;
        const int result=PlugPikiApp::idle();
        const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        require(++frames<=7200,"frame bound");
        const auto s=pc_blank_card_snapshot;
        const auto action=policy.step(s,pc_blank_card_publications,forbidden(),generations(),elapsed);
        std::printf("P2_BLANK_CARD_OBSERVE frame=%u seconds=%.3f title=%d card=%d active=%d memory=%d default=%d ready=%d file=%d slots=%d,%d,%d action=%d\n",
            frames,elapsed,int(s.title),int(s.card),int(s.active),s.memoryState,s.defaults.state,int(s.defaults.confirmationReady),int(s.fileReady),s.slots[0],s.slots[1],s.slots[2],int(action));
        require(action!=blankcard::Input::Refuse,"strict ordinary title/card transition");
        input(action==blankcard::Input::A);
        if(action==blankcard::Input::Complete){
            require(!gsys->mIsCardSaving,"native card I/O finished");
            require(std::filesystem::is_directory(cardRoot/"card0"),"native backing exists");
            std::puts("PASS P2_BLANK_CARD_UI slots_fresh=3 campaign_generations=0 field_entered=0 actors=0 native_ui=1");
            std::fflush(nullptr);std::_Exit(0);
        }
        return result;
    }
};
}
int main(int argc,char** argv){
#if !defined(VERSION_GPIE01_01)
    require(false,"unsupported native UI version");
#endif
    require(argc==3 && !std::strcmp(argv[1],"--blank-card-root"),"exact blank-card arguments");
    cardRoot=std::filesystem::path(argv[2]);
    require(cardRoot.is_absolute() && cardRoot.filename()=="card" && cardRoot.parent_path().filename()=="campaign","private card path shape");
    require(cardRoot==std::filesystem::weakly_canonical(cardRoot),"canonical private card path");
    const char* env=std::getenv("NECTAR_SAVE_DIR");require(env && cardRoot==std::filesystem::path(env),"exact NECTAR_SAVE_DIR binding");
    require(!std::filesystem::exists(cardRoot),"fresh backing required");
    for(auto p=cardRoot;!p.empty();p=p.parent_path()){
        require(!std::filesystem::is_symlink(std::filesystem::symlink_status(p)),"no card path symlinks");
        if(p==p.parent_path())break;
    }
    require(!generations(),"zero initial campaign generations");
    const char* shader=std::getenv("PIKMIN_SHADER_CACHE");
    require(shader && !std::strcmp(shader,"0"),"initializer-only shader cache disabled");
    SDL_SetMainReady();pc_gpu_preference_apply();
    char* ordinary[]={argv[0]};pc_bbft_init(1,ordinary);
    require(!pc_bbft_enabled()&&!pc_randomizer_enabled(),"ordinary title boot");
    require(!std::strcmp(pc_bbft_save_root(),"save"),"ordinary card root honors NECTAR_SAVE_DIR");
    require(pc_window_init("Native blank card initialization",960,540),"window");
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* w=SDL_GL_GetCurrentWindow();int width=0,height=0,x=0,y=0;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect bounds{};
    require(SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&bounds)==0 && width==960 && height==540
        && std::abs(x-(bounds.x+(bounds.w-width)/2))<=2 && std::abs(y-(bounds.y+(bounds.h-height)/2))<=2,"centered960x540");
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    const int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual SDL pad");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    const std::string map=std::string(guid)+",Blank card SDL pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
    require(SDL_GameControllerAddMapping(map.c_str())>=0 && SDL_IsGameController(device),"SDL mapping");
    pad=SDL_JoystickOpen(device);require(pad && SDL_JoystickIsVirtual(device),"open virtual SDL pad");
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    input(false);pc_blank_card_observer_enabled=true;
    std::puts("P2_BLANK_CARD_BOOT ordinary_title=1 size=960x540 centered=1 native_input=SDL generation=0");
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new BlankCardApp());
    require(false,"engine exited without blank-card completion");return 1;
}
