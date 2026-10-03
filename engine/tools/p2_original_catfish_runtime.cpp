// Native birth/resource/lifecycle diagnostic. Human mode leaves the actual
// authored Water Dumple encounter running; no HP/state/transport writes.
#include <SDL2/SDL.h>
#include "p2_fixture_captain_guard_catfish.h"
#include "MapMgr.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "teki.h"
#include "Generator.h"
#include "GameStat.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_original_catfish_native.h"
#include "pc_p2_original_group_engine.h"
#include "pc_p2_catfish.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
namespace {
using namespace p2original;
bool human=false,negativeGuard=false;
void require(bool yes,const char* text){if(!yes){std::fprintf(stderr,"FAIL P2_ORIGINAL_CATFISH %s\n",text);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool yes,const std::string& e){if(!yes)std::fprintf(stderr,"P2_ORIGINAL_CATFISH_ERROR %s\n",e.c_str());require(yes,"native provider call");}
CatalogRow retail(){
 CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=25;r.sourceKey="tutorial/initgen.txt#25";
 auto& a=r.enemy;a.uid=1379145044u;a.source=26;a.birthType=0;a.count=1;a.spawnType=1;a.directionDegrees=0;
 a.position={340.793396f,15.0f,868.564026f};a.appearRadius=100;a.enemySize=0;a.generatorVersion="????";
 a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=2;a.pelletProbability=.4f;return r;
}
class CatfishApp:public PlugPikiApp {
 std::unique_ptr<catfish::Native> native;std::unique_ptr<Generator> generator;
 bool captainObserved=false,parked=false;Vector3f parkPosition;
 GeneratorState state;Creature* actor=nullptr;unsigned token=0;int frame=0,age=0,entries=0,before=0;
 void enter(){
  struct Heap{int prior;Heap():prior(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(prior);}} heap;
  if(!native)native=std::make_unique<catfish::Native>();
  if(!generator)generator=std::make_unique<Generator>();
  require(!generator->mGenType,"genuine original null P1 GenType boundary");
  generator->mRespawnInterval=state.resurrectionDays;
  generator->mCarryOverFlags=state.reserved;
  std::string e;checked(pc_p2_original_course_install({{generator.get(),state}},native->provider(),e),e);
  bool handled=false;checked(pc_p2_original_generator_init(generator.get(),handled,e),e);require(handled,"actual original generator handled");
  actor=nullptr;Iterator it(tekiMgr);CI_LOOP(it){auto* t=static_cast<BTeki*>(*it);unsigned source=0,found=0;
   if(originalActors().query(t,source,found)&&source==26){require(!actor,"one literal source birth");actor=t;token=found;}}
  require(actor&&token&&native->provider().lookup(actor)!=nullptr,"physical actor registered");
  auto* t=static_cast<BTeki*>(actor);const char* fsm="wait",*clip=nullptr;float phase=0;
  require(pc_p2_catfish_clip(t,clip,phase)&&pc_p2_catfish_suppress_ai(t)&&t->mHealth==200&&t->mMaxHealth==200&&t->mTekiType==TEKI_Namazu,"actual P2 family health/FSM/chassis");
  InstanceIdentity id;unsigned source=0,found=0;require(originalActors().query(actor,source,found,&id)&&id.generator==retail().enemy.uid&&id.ordinal==0&&id.activation==unsigned(entries+1),"complete original registry identity");
  require(t->mSRT.t.x==retail().enemy.position.x&&t->mSRT.t.z==retail().enemy.position.z,"authored source XZ preserved");
  std::printf("P2_ORIGINAL_CATFISH_RUNTIME_BIRTH uid=%u token=%u activation=%llu state=%s clip=%s health=%.1f x=%.3f y=%.3f z=%.3f\n",id.generator,token,(unsigned long long)id.activation,fsm,clip,t->mHealth,t->mSRT.t.x,t->mSRT.t.y,t->mSRT.t.z);
  age=0;
 }
public:
 CatfishApp(){state.uid=retail().enemy.uid;state.count=1;state.reserved=5;state.resurrectionDays=3;}
 int idle()override{
  int result=PlugPikiApp::idle();
  // Guard precedes movie/pause/readiness/frame/PASS observations.
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(GameStat::orimaDead)p2_fixture_require_captain(true,true,0.0f,age);
  if(n&&n->getCurrState()){
   captainObserved=true;
   p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState()->getID()==NAVISTATE_Dead||!n->isAlive(),n->mHealth,age);
  }else if(captainObserved)p2_fixture_require_captain(false,true,0.0f,age);
  require(++frame<18000||human,"bounded frame budget");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!n||!n->getCurrState()||!pikiMgr||!tekiMgr||!pelletMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  if(!human){
   // Diagnostic only: park at a real course floor outside the source bite
   // reach. No health/protection writes; human controls remain ordinary.
   if(!parked){parkPosition=n->getPosition();
    const auto authored=retail().enemy.position;
    const float dx=parkPosition.x-authored.x,dz=parkPosition.z-authored.z;
    if(dx*dx+dz*dz<700.0f*700.0f){parkPosition.set(authored.x+1000.0f,0,authored.z);
     require(mapMgr,"diagnostic parking terrain available");parkPosition.y=mapMgr->getMinY(parkPosition.x,parkPosition.z,true);}
    parked=true;
   }
   n->resetPosition(parkPosition);n->mVelocity.set(0,0,0);
  }
  if(!native){if(n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
   unsigned live=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p->isAlive())++live;}
   require(live==20,"20 live Pikmin fixture baseline");before=tekiMgr->getSize();enter();}
  if(human)return result;
  if(++age<180)return result;
  unsigned alive=0;require(pc_p2_original_groups().state(generator.get(),state,alive)&&alive==1,"original group retained live actor");
  std::string e;checked(pc_p2_original_course_unload(e),e);
  unsigned source=0,found=0;require(!originalActors().query(actor,source,found)&&native->provider().lookup(actor)==nullptr&&tekiMgr->getSize()==before,"real pool/registry cleanup");
  if(++entries==1){enter();return result;}
  std::puts("PASS P2_ORIGINAL_CATFISH_RUNTIME actual_native_birth=1 source_row=1 resource_bank=1 cleanup_reentry=1 natural_attack=0 save_resume=0");std::fflush(nullptr);std::_Exit(0);
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i){
  if(!std::strcmp(argv[i],"--manual-encounter"))human=true;
  if(!std::strcmp(argv[i],"--guard-negative-test"))negativeGuard=true;
 }
 if(negativeGuard){p2_fixture_require_captain(true,true,0.0f,0);return 1;}
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial"),"ordinary imported tutorial course");
 require(pc_window_init("Original Water Dumple provider fixture",960,540),"window init");
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect b{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&b);
 require(width==960&&height==540&&std::abs(x-(b.x+(b.w-width)/2))<=2&&std::abs(y-(b.y+(b.h-height)/2))<=2,"960x540 centered baseline");
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
 std::string e;checked(originalActors().install(std::string(64,'a'),{retail()},catfish::decode,e),e);
 gsys->run(new CatfishApp());return 0;
}
