// Private runtime check of real settings toggles and unchanged manual App guard.
#include "manual-app.inc"
#include "GoalItem.h"
#include <array>
#include <cstring>
static bool f1=false,injecting=false;
static int confirmations=0;
extern "C" const Uint8* __wrap_SDL_GetKeyboardState(int* count){
 static std::array<Uint8,SDL_NUM_SCANCODES> keys{};keys.fill(0);keys[SDL_SCANCODE_F1]=f1;
 if(count)*count=SDL_NUM_SCANCODES;return keys.data();
}
extern "C" Uint8 __wrap_SDL_GameControllerGetButton(SDL_GameController*,SDL_GameControllerButton){return 0;}
extern "C" Sint16 __wrap_SDL_GameControllerGetAxis(SDL_GameController*,SDL_GameControllerAxis){return 0;}
extern "C" int __wrap_SDL_ShowMessageBox(const SDL_MessageBoxData*,int* choice){
 check(!settingsOpen,"confirmation while settings open");++confirmations;*choice=1;
 std::puts("P2_SETTINGS_CLOSED_CONFIRM");return 0;
}
static int controlledFilter(void* data,SDL_Event* event){
 if((event->type==SDL_KEYDOWN || event->type==SDL_KEYUP) && !injecting)return 0;
 return filterInput(data,event);
}
static void injectF6(){
 SDL_Event event{};event.type=SDL_KEYDOWN;event.key.state=SDL_PRESSED;
 event.key.keysym.scancode=SDL_SCANCODE_F6;event.key.keysym.sym=SDLK_F6;
 injecting=true;check(SDL_PushEvent(&event)>=0,"settings F6 injection");injecting=false;
}
static bool transferExists(){std::ifstream f("p2-cave-transfer.txt");return bool(f);}
class SettingsFixtureApp:public ManualEntranceApp {
 int frames=0,ready=0,phase=0,phaseFrames=0;std::string mode;
public:
 SettingsFixtureApp(){std::ifstream cfg("settings-fixture.txt");cfg>>mode;check(mode=="settings" || mode=="drift","settings fixture mode");}
 int idle() override {
  int result=ManualEntranceApp::idle();check(++frames<1800,"settings fixture timeout");
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !pc_p2_cave_floor())return result;
  Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState() || n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
  ++ready;
  if(mode=="drift"){
   if(ready==1 || ready==30 || ready==60 || ready==90){
    std::printf("P2_DRIFT frame=%d position=%.9g,%.9g,%.9g velocity=%.9g,%.9g,%.9g ground=%.9g\n",ready,
       n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true));std::fflush(stdout);
    std::printf("P2_DRIFT_FORCE frame=%d volatile=%.9g,%.9g,%.9g collision=%u radius=%.9g\n",ready,n->mVolatileVelocity.x,n->mVolatileVelocity.y,n->mVolatileVelocity.z,n->mCollisionOccurred,n->mCollisionRadius);
    float nearest=1e9f;Piki* near=nullptr;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()){
     float dx=p->mSRT.t.x-n->mSRT.t.x,dz=p->mSRT.t.z-n->mSRT.t.z,dist=std::sqrt(dx*dx+dz*dz);if(dist<nearest){nearest=dist;near=p;}
    }}
    if(near)std::printf("P2_DRIFT_NEAR frame=%d distance=%.9g position=%.9g,%.9g,%.9g radius=%.9g state=%d\n",ready,nearest,near->mSRT.t.x,near->mSRT.t.y,near->mSRT.t.z,near->mCollisionRadius,near->getState());
    if(auto pod=pc_p2_preview_goal())std::printf("P2_DRIFT_POD frame=%d position=%.9g,%.9g,%.9g radius=%.9g\n",ready,pod->mSRT.t.x,pod->mSRT.t.y,pod->mSRT.t.z,pod->mCollisionRadius);
    std::fflush(stdout);
   }
   if(ready==90){check(!transferExists(),"drift observation transitioned");std::puts("PASS P2_DRIFT_OBSERVATION");std::fflush(nullptr);std::_Exit(0);}
   return result;
  }
  if(ready<30)return result;
  if(phase==0){check(!settingsOpen,"settings initially open");f1=true;phase=1;return result;}
  if(phase==1){
   check(settingsOpen,"real F1 toggle did not open settings callback");f1=false;
   check(pc_settings_consume_game_input(),"real settings menu did not consume game input");
   std::puts("P2_SETTINGS_REAL_MENU_OPEN");injectF6();check(!descend,"open menu queued F6");phase=2;return result;
  }
  if(phase==2){
   check(settingsOpen && pc_settings_consume_game_input(),"settings closed unexpectedly");
   check(!confirmations && !transferExists() && !descend,"open-menu F6 escaped guard");
   if(++phaseFrames<5)return result;
   std::puts("P2_SETTINGS_F6_SUPPRESSED dialogs=0 transfer=0");f1=true;phase=3;return result;
  }
  if(phase==3){
   check(!settingsOpen,"real F1 toggle did not close settings callback");f1=false;
   check(!pc_settings_consume_game_input(),"closed settings consumed game input");
   std::puts("P2_SETTINGS_REAL_MENU_CLOSED");injectF6();check(descend,"closed menu rejected F6");phase=4;return result;
  }
  check(++phaseFrames<20,"closed-menu F6 failed to transition");return result;
 }
};
int main(int argc,char**argv){
 std::ifstream entry("p2-cave-entry.txt");std::string header;entry>>header>>entryToken;
 check(header=="P2_CAVE_ENTRY_1" && entryToken.size()==32,"settings entry token");
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
 _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 check(pc_pikipelago_room_preview(),"settings preview flag");if(!pc_window_init("P2 settings/drift fixture",960,720))return 3;
 pc_settings_init();SDL_SetEventFilter(controlledFilter,nullptr);gsys->Initialise();pc_settings_p2d_init();
 nodeMgr=new NodeMgr();gsys->run(new SettingsFixtureApp());return 0;
}
