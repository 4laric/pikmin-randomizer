// Private visual-only fixture. Existing room fixture prefix supplies capture/init headers.
#include "room-prefix.inc"
#include "pc_p2_breadbug_visual.h"
#include <fstream>
#include <sstream>
#include <string>
class BreadbugVisualFixture : public PlugPikiApp {
 int frames=0,ready=0,actorCount=0;bool enabled=false;std::string displayKind;
 int countActors(){int count=0;Iterator it(tekiMgr);CI_LOOP(it){if(*it)++count;}return count;}
public:
 int idle() override {
  int result=PlugPikiApp::idle();require(++frames<1800,"Breadbug visual timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||!n->getCurrState())return result;
  ++ready;
  if(ready==1){actorCount=countActors();n->mKontroller=new FixtureController();std::printf("P2_BREADBUG_FIXTURE_NAVI state=%d\n",n->getCurrState()->getID());for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);std::ifstream mode("breadbug-runtime-mode.txt");std::string value;mode>>value;enabled=value!="disabled";displayKind=value;require(value=="wait"||value=="move"||value=="nest"||value=="disabled","visual fixture mode");}
  if(ready==30&&enabled){
   std::ifstream source("breadbug-fixture-profile.txt");require(bool(source),"visual profile fixture");std::string a,b,c;std::getline(source,a);std::getline(source,b);std::getline(source,c);
   std::ofstream cfg("p2-breadbug-visual.txt");cfg<<a<<'\n'<<b<<'\n'<<c<<"\n1\n";
   int i=0;for(float dx:{-55.f}){float x=n->mSRT.t.x+dx,z=n->mSRT.t.z+60,y=mapMgr->getMinY(x,z,true);require(std::isfinite(y)&&std::fabs(y-n->mSRT.t.y)<100,"display ground unreasonable");
    const char* kind=displayKind.c_str();cfg<<i+1<<' '<<kind<<' '<<x<<' '<<y<<' '<<z<<" 0\n";
    std::printf("P2_BREADBUG_FIXTURE_GROUND display=%d kind=%s xyz=%.6f,%.6f,%.6f\n",i+1,kind,x,y,z);++i;
   }
   cfg.close();const int oldHeap=gsys->setHeap(SYSHEAP_App);pc_p2_breadbug_visual_setup();gsys->setHeap(oldHeap);require(countActors()==actorCount,"visual setup changed enemy count");
  }
  if(ready==60){capture("breadbug-pose-a.ppm");SDL_Delay(450);}
  if(ready==62){capture("breadbug-pose-b.ppm");require(countActors()==actorCount,"visual playback changed enemy count");pc_p2_breadbug_visual_reset();}
  if(ready==65){capture("breadbug-reset.ppm");require(countActors()==actorCount,"visual reset changed enemy count");std::puts("PASS P2_BREADBUG_VISUAL_FIXTURE visual_only unchanged_enemy_count");std::fflush(nullptr);std::_Exit(0);}
  return result;
 }
};
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 require(pc_pikipelago_room_preview(),"requires preview flag");if(!pc_window_init("Breadbug visual fixture",960,720))return 3;
 pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new BreadbugVisualFixture());return 0;
}
