// Private runtime fixture. Generated include is extracted from the real manual
// App source before its main(), preserving its input/guard/position implementation.
#include "manual-app.inc"
#include "pc_p2_purple.h"
#include "pc_p2_cave_anchor.h"
#include "Teki.h"
#include <vector>

extern "C" int __wrap_SDL_ShowMessageBox(const SDL_MessageBoxData*,int* choice){
 *choice=1;std::puts("P2_REPEAT_CONFIRM_INJECTED");return 0;
}
class RepeatFixtureApp:public ManualEntranceApp {
 int ticks=0,frames=0;bool injected=false;
public:
 int idle() override {
  const int result=ManualEntranceApp::idle();check(++frames<3000,"repeat fixture timeout");
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready() || !pc_p2_cave_floor() || !naviMgr || !pikiMgr)return result;
  if(!ticks){Iterator enemies(tekiMgr);CI_LOOP(enemies){Teki* e=static_cast<Teki*>(*enemies);if(e && e->isAlive())e->kill(false);}}
  Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState() || n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
  static bool surfaceRun=[](){std::ifstream f("repeat-fixture.txt");std::string kind;f>>kind;return kind=="surface";}();
  if(++ticks<(surfaceRun?30:90) || injected)return result;
  std::ifstream entry("p2-cave-entry.txt");std::string header,token;int floor,count;float health;
  check(bool(entry>>header>>token>>floor>>health>>count),"repeat input");entryToken=token;
  int expected[4][3]={},actual[4][3]={};
  for(int i=0;i<count;++i){int c,h;check(bool(entry>>c>>h),"repeat squad input");++expected[c][h];}
  std::vector<Piki*> crew;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()){crew.push_back(p);++actual[pc_p2_is_purple(p)?3:p->mColor][p->mHappa];}}
  check(crew.size()==size_t(count),"repeat restored count");
  for(int c=0;c<4;++c)for(int h=0;h<3;++h)check(expected[c][h]==actual[c][h],"repeat restored species/maturity");
  check(std::fabs(n->mHealth/C_NAVI_PARM(n,mHealth)-health)<.0001f,"repeat restored health");
  std::ifstream cfg("repeat-fixture.txt");std::string kind;int visit,pokos;float sourceX,sourceY,sourceZ;
  check(bool(cfg>>kind>>visit>>pokos>>sourceX>>sourceY>>sourceZ),"repeat fixture config");
  check(pc_p2_preview_pokos()==pokos,"repeat restored receipts");
  std::printf("P2_REPEAT_RESTORE kind=%s visit=%d floor=%d count=%d health=%.9g pokos=%d\n",kind.c_str(),visit,floor,count,health,pokos);
  if(kind=="surface"){
   std::printf("P2_REPEAT_POSITION expected=%.9g,%.9g,%.9g actual=%.9g,%.9g,%.9g frames=%d\n",sourceX,sourceY,sourceZ,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,ticks);
   check(radial(n->mSRT.t)<60 && std::fabs(n->mSRT.t.y-80)<1,"source surface position");
   check(std::fabs(n->mSRT.t.x-sourceX)<1 && std::fabs(n->mSRT.t.y-sourceY)<1 && std::fabs(n->mSRT.t.z-sourceZ)<1,"source snapshot position restored");
   if(visit==3){std::puts("PASS P2_REPEAT_FINAL_SURFACE");std::fflush(nullptr);std::_Exit(0);}
   // Explicit fixture movement, not manual control acceptance.
   n->resetPosition(Vector3f(-210+visit*5,80,1160));
  }else{
   check(kind=="cave","repeat unknown kind");
   if(visit==1 && floor==1){check(count==20,"first party");crew.back()->kill(false);crew[0]->mHappa=Flower;crew[1]->mHappa=Bud;n->mHealth=C_NAVI_PARM(n,mHealth)*.625f;}
   if(visit==1 && floor==2){check(count==19,"first casualty preserved");for(int i=0;i<10;++i)pc_p2_make_purple(crew[i]);}
   if(visit==2 && floor==1)n->mHealth=C_NAVI_PARM(n,mHealth)*.5f;
   int before=pc_p2_preview_pokos();
   if(pc_p2_preview_cargo_count()){
    for(int i=0;i<pc_p2_preview_cargo_count();++i)check(pc_p2_preview_deliver(pc_p2_preview_cargo_at(i)),"native receipt hook");
   }else check(pc_p2_preview_deliver(pc_p2_preview_treasure()),"native treasure hook");
   int after=pc_p2_preview_pokos();
   if(visit==2)check(after==before,"second visit duplicated credit");
   if(pc_p2_preview_cargo_count())for(int i=0;i<pc_p2_preview_cargo_count();++i)check(pc_p2_preview_deliver(pc_p2_preview_cargo_at(i)),"repeated native receipt hook");
   check(pc_p2_preview_pokos()==after,"same-process duplicated credit");
   std::printf("P2_REPEAT_DELIVER visit=%d before=%d after=%d injected_hook=1\n",visit,before,after);
   P2CaveAnchor anchor;std::ifstream input("p2-cave-transition.txt");
   check(p2_cave_read_anchor(input,floor,anchor),"repeat anchor");
   n->resetPosition(Vector3f(anchor.x,anchor.y,anchor.z));
  }
  n->mStateMachine->transit(n,NAVISTATE_Walk);
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  SDL_Event event{};event.type=SDL_KEYDOWN;event.key.state=SDL_PRESSED;
  event.key.keysym.scancode=SDL_SCANCODE_F6;event.key.keysym.sym=SDLK_F6;
  // SDL's filter may consume the event immediately (return0); that is expected.
  check(SDL_PushEvent(&event)>=0,"F6 event injection failed");injected=true;
  std::puts("P2_REPEAT_F6_INJECTED not_physical_input");std::fflush(stdout);return result;
 }
};
int main(int argc,char**argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
 _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 check(pc_pikipelago_room_preview(),"repeat preview flag");if(!pc_window_init("P2 repeat runtime fixture",960,720))return 3;
 pc_settings_init();SDL_SetEventFilter(filterInput,nullptr);gsys->Initialise();pc_settings_p2d_init();
 nodeMgr=new NodeMgr();gsys->run(new RepeatFixtureApp());return 0;
}
