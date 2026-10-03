// #1229 actual native mid-day F11 file menu, repeated SAVE and fresh-process load.
// Inputs are SDL events/virtual P1; no card or actor state is injected.
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
#include "pc_p2_surface_save.h"
#include "pc_p2_cave_campaign_party_engine.h"
#include "Generator.h"
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
class SurfaceSaveApp final:public PlugPikiApp {
    int frames=0,tick=-1,menuFrames=0,observedCards=0;
    bool initialized[2]={false,false},saving=false,shot=false;
    std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
    struct Policy {Generator* gen;unsigned flags;int limit;};
    std::vector<Policy> policies;
    void guard(){
        require(std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now()-started).count()<60,"60 second fixture bound");
        for(int i=0;i<2;++i){auto* n=naviMgr?naviMgr->getNavi(i):nullptr;
            if(n&&n->getCurrState())initialized[i]=true;
            if(initialized[i])requireCaptain(n,tick);}
    }
    void pad(unsigned keys=0,int x=0){
        const int id=SDL_JoystickInstanceID(virtualPad);
        pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,id);pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_UP,(keys&KBBTN_DPAD_UP)!=0);
        SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
        SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,0);SDL_JoystickUpdate();
    }
    void saveKey(){SDL_Event e{};e.type=SDL_KEYDOWN;e.key.keysym.scancode=SDL_SCANCODE_F11;
        e.key.keysym.sym=SDLK_F11;e.key.state=SDL_PRESSED;require(SDL_PushEvent(&e)==1,"ordinary F11 event");
        saving=true;menuFrames=0;std::printf("P2_SURFACE_FIXTURE_SAVE_REQUEST generation_before=%llu direct_commit=0\n",(unsigned long long)pc_randomizer_active_campaign_generation());}
    void verifyResume(){
        const auto& saved=pc_randomizer_surface_session();require(saved.present&&saved.valid(),"selected living surface descriptor");
        require(saved.party.bodies.size()==20,"selected saved twenty bodies");
        P2CaveCampaignParty actual=saved.party;
        require(pc_p2_cave_campaign_party_capture(actual,false),"actual restored party capture");
        require(actual.active==saved.party.active&&actual.bodies.size()==20&&actual.captains.size()==saved.party.captains.size(),"cold population and active owner");
        for(const auto& c:saved.party.captains){auto* n=naviMgr->getNavi(c.slot);
            require(n&&std::fabs(n->mHealth-c.health)<.001f,"cold captain health");
            require(std::fabs(n->mSRT.t.x-c.position.x)<2&&std::fabs(n->mSRT.t.z-c.position.z)<2,"cold captain position");}
        for(const auto& b:saved.party.bodies){const P2CavePartyBody* found=nullptr;
            for(const auto& candidate:actual.bodies)if(candidate.key==b.key)found=&candidate;
            require(found&&found->species==b.species&&found->growth==b.growth&&found->owner==b.owner
                &&found->mode==b.mode&&std::fabs(found->health-b.health)<.001f,"cold body typed state");}
        require(gameflow.mWorldClock.mCurrentDay==saved.day&&std::fabs(gameflow.mWorldClock.mTimeOfDay-saved.party.surfaceTime)<.2f,"cold day and clock");
        std::printf("P2_SURFACE_FIXTURE_COLD_STATE bodies=20 captains=%zu stock=%d generation=%llu\n",actual.captains.size(),storedCount(),(unsigned long long)pc_randomizer_active_campaign_generation());
    }
public:
    SurfaceSaveApp(){observedCards=cards();require(resumePhase?observedCards==2:observedCards==0,"expected immutable generations");}
    void draw(Graphics& gfx)override{PlugPikiApp::draw(gfx);if(tick>25&&!shot)shot=capture("surface-campaign.ppm");}
    int idle()override{
        if(tick==5&&(sForceCaptainDown||sForceInactiveDown||forceNullState||forceMissingManager)){
            auto* n=naviMgr->getNavi(sForceInactiveDown||forceNullState?1:0);
            if(forceMissingManager)naviMgr=nullptr;
            else if(forceNullState)n->mCurrState=nullptr;
            else n->mHealth=0;
        }
        guard();const int result=PlugPikiApp::idle();guard();require(++frames<7200,"frame bound");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(saving){
            require(++menuFrames<600,"native surface menu/save did not commit");
            pad(menuFrames%20<4?KBBTN_A:0);
            if(cards()>observedCards){
                require(cards()==observedCards+1,"exactly one generation per native menu choice");
                for(const auto& p:policies)require(p.gen->mCarryOverFlags==p.flags&&p.gen->mDayLimit==p.limit,"live authored source policy restored after SAVE");
                observedCards=cards();saving=false;pad();
                require(pc_randomizer_surface_session().party.bodies.size()==20,"SAVE contains real twenty-body party");
                if(observedCards==2){require(shot,"actual rendered frame");std::puts("PASS P2_SURFACE_NATIVE_SAVE repeated=2 same_day=1 ordinary_F11_menu=1 card_bytes_injected=0");std::fflush(nullptr);std::_Exit(0);}
                tick=100;std::puts("P2_SURFACE_FIXTURE_REPEAT_PENDING live_cache_policy_restored=1");
            }
            return result;
        }
        if(!pc_randomizer_ready()||!naviMgr||!naviMgr->getActiveNavi()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);require(a&&b,"two actual captains");
        if(!a->getCurrState()||!b->getCurrState()||a->getCurrState()->getID()!=NAVISTATE_Walk||b->getCurrState()->getID()!=NAVISTATE_Walk)return result;
        int live=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++live;}
        require(live<=20,"twenty-live baseline ceiling");if(live<20)return result;
        if(tick<0){
            require(pc_randomizer_resumed()==resumePhase,"actual fresh process campaign state");
            if(resumePhase)verifyResume();
            Generator* gen;FOREACH_NODE_REUSE(Generator,generatorList->mGenListHead->mChild,gen){
                policies.push_back({gen,gen->mCarryOverFlags,gen->mDayLimit});
                std::printf("P2_SURFACE_FIXTURE_SOURCE flags=%u count=%d deadline=%d latest=%d name=%08x version=%08x disk=%08x object=%08x area=%08x type=%08x list=%d\n",gen->mCarryOverFlags,gen->mAliveCount,gen->mDayLimit,int(gen->mLatestSpawnCreature!=nullptr),gen->mGeneratorName.mId,gen->mGeneratorVersion.mId,gen->_70,gen->mGenObject?gen->mGenObject->mID:0,gen->mGenArea?gen->mGenArea->mID:0,gen->mGenType?gen->mGenType->mID:0,gen->mGeneratorListIdx);}
            tick=0;
        }
        ++tick;
        if(tick==5)pad(0,40);if(tick==20)pad();
        if(tick==50){
            require(shot,"actual rendered surface frame");
            if(resumePhase){require(cards()==observedCards,"load did not publish card");std::puts("PASS P2_SURFACE_NATIVE_FRESH_PROCESS bodies=20 same_day=1 controls=1 card_bytes_injected=0");std::fflush(nullptr);std::_Exit(0);}
            saveKey();
        }
        if(tick==140)saveKey();
        std::fflush(stdout);return result;
    }
};
} // namespace
int main(int argc,char** argv){
    for(int i=1;i<argc;++i){resumePhase|=std::string(argv[i])=="--resume-phase";sForceCaptainDown|=std::string(argv[i])=="--force-captain-down";sForceInactiveDown|=std::string(argv[i])=="--force-inactive-down";forceNullState|=std::string(argv[i])=="--force-null-state";forceMissingManager|=std::string(argv[i])=="--force-missing-manager";}
    SDL_setenv("PIKMIN_P2_SURFACE_SAVE","1",1);SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
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
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new SurfaceSaveApp());return 0;
}
