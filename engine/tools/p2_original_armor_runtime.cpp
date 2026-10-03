// Native birth/resource/lifecycle diagnostic. Human mode leaves the actual
// authored Cloaking Burrow-nit encounter running; no HP/state/transport writes.
#include <SDL2/SDL.h>
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
#include "pc_p2_original_armor_native.h"
#include "pc_p2_original_group_engine.h"
#include "pc_p2_armor.h"
#include "pc_p2_batch2.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
namespace {
using namespace p2original;
bool human=false;
void require(bool yes,const char* text){if(!yes){std::fprintf(stderr,"FAIL P2_ORIGINAL_ARMOR %s\n",text);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool yes,const std::string& e){if(!yes)std::fprintf(stderr,"P2_ORIGINAL_ARMOR_ERROR %s\n",e.c_str());require(yes,"native provider call");}
CatalogRow retail(){
 CatalogRow r;r.course="tutorial";r.member="initgen.txt";r.index=32;r.sourceKey="tutorial/initgen.txt#32";
 auto& a=r.enemy;a.uid=1385422481u;a.source=15;a.birthType=0;a.count=1;a.spawnType=1;a.directionDegrees=0;
 a.position={532.630676f,106.218262f,45.448071f};a.appearRadius=100;a.enemySize=0;a.generatorVersion="????";
 a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=3;a.pelletProbability=.5f;return r;
}
class ArmorApp:public PlugPikiApp {
 std::unique_ptr<armor::Native> native;std::unique_ptr<Generator> generator;
 GeneratorState state;Creature* actor=nullptr;unsigned token=0;int frame=0,age=0,entries=0,before=0;
 void enter(){
  struct Heap{int prior;Heap():prior(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(prior);}} heap;
  if(!native)native=std::make_unique<armor::Native>();
  if(!generator)generator=std::make_unique<Generator>();
  require(!generator->mGenType,"genuine original null P1 GenType boundary");
  generator->mRespawnInterval=state.resurrectionDays;
  generator->mCarryOverFlags=state.reserved;
  std::string e;checked(pc_p2_original_course_install({{generator.get(),state}},native->provider(),e),e);
  bool handled=false;checked(pc_p2_original_generator_init(generator.get(),handled,e),e);require(handled,"actual original generator handled");
  actor=nullptr;Iterator it(tekiMgr);CI_LOOP(it){auto* t=static_cast<BTeki*>(*it);unsigned source=0,found=0;
   if(originalActors().query(t,source,found)&&source==15){require(!actor,"one literal source birth");actor=t;token=found;}}
  require(actor&&token&&native->provider().size()==1,"physical actor registered");
  auto* t=static_cast<BTeki*>(actor);const char* clip=nullptr;float phase=0;
  require(pc_p2_armor_registered(t)&&pc_p2_armor_clip(t,clip,phase)&&t->mHealth==300&&t->mMaxHealth==300&&t->mTekiType==TEKI_Chappy,"actual P2 family health/FSM/chassis");
  InstanceIdentity id;unsigned source=0,found=0;require(originalActors().query(actor,source,found,&id)&&id.generator==retail().enemy.uid&&id.ordinal==0&&id.activation==unsigned(entries+1),"complete original registry identity");
  require(t->mSRT.t.x==retail().enemy.position.x&&t->mSRT.t.z==retail().enemy.position.z,"authored source XZ preserved");
  std::printf("P2_ORIGINAL_ARMOR_RUNTIME_BIRTH uid=%u token=%u activation=%llu clip=%s health=%.1f x=%.3f y=%.3f z=%.3f\n",id.generator,token,(unsigned long long)id.activation,clip,t->mHealth,t->mSRT.t.x,t->mSRT.t.y,t->mSRT.t.z);
  // These ordinary setup hooks must preserve an already admitted original actor.
  pc_p2_armor_setup();pc_p2_batch2_setup();
  require(pc_p2_armor_registered(t)&&pc_p2_batch2_registered(t),"normal setup preserves original family/bank");
  age=0;
 }
public:
 ArmorApp(){state.uid=retail().enemy.uid;state.count=1;state.reserved=5;state.resurrectionDays=3;}
 int idle()override{
  int result=PlugPikiApp::idle();require(++frame<18000||human,"bounded frame budget");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(!n||!n->getCurrState()||!pikiMgr||!tekiMgr||!pelletMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  require(n->mHealth>0&&!GameStat::orimaDead,"captain remains alive");
  if(!native){if(n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
   unsigned live=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p->isAlive())++live;}
   require(live==20,"20 live Pikmin fixture baseline");before=tekiMgr->getSize();enter();}
  if(human)return result;
  if(++age<180)return result;
  unsigned alive=0;require(pc_p2_original_groups().state(generator.get(),state,alive)&&alive==1,"original group retained live actor");
  std::string e;checked(pc_p2_original_course_unload(e),e);
  unsigned source=0,found=0;require(!originalActors().query(actor,source,found)&&native->provider().size()==0&&tekiMgr->getSize()==before,"real pool/registry cleanup");
  if(++entries==1){enter();return result;}
  std::puts("PASS P2_ORIGINAL_ARMOR_RUNTIME actual_native_birth=1 source_row=1 resource_bank=1 cleanup_reentry=1 natural_attack=0 save_resume=0");std::fflush(nullptr);std::_Exit(0);
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i)if(!std::strcmp(argv[i],"--manual-encounter"))human=true;
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial"),"ordinary imported tutorial course");
 require(pc_window_init("Original Cloaking Burrow-nit provider fixture",960,540),"window init");
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect b{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&b);
 require(width==960&&height==540&&std::abs(x-(b.x+(b.w-width)/2))<=2&&std::abs(y-(b.y+(b.h-height)/2))<=2,"960x540 centered baseline");
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
 std::string e;checked(originalActors().install(std::string(64,'a'),{retail()},armor::admits,e),e);
 gsys->run(new ArmorApp());return 0;
}
