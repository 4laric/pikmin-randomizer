// Private fault injection; production pc_p2_cave_tick owns terminal checkpoint/exit.
#include "manual-app.inc"
#include "teki.h"
#include <vector>
class TerminalFixtureApp:public ManualEntranceApp {
 int frames=0,ready=0;bool injected=false;
public:
 int idle() override {
  int result=ManualEntranceApp::idle();check(++frames<1800,"native terminal fixture timeout");
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready() || !pc_p2_cave_floor() || !naviMgr || !pikiMgr)return result;
  if(!ready && tekiMgr){Iterator enemies(tekiMgr);CI_LOOP(enemies){Teki* e=static_cast<Teki*>(*enemies);if(e && e->isAlive())e->kill(false);}}
  Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState() || n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
  if(++ready<30 || injected)return result;
  std::ifstream entry("p2-cave-entry.txt");std::string version,token;int floor,count;float health;
  check(bool(entry>>version>>token>>floor>>health>>count),"terminal fixture entry");
  std::vector<Piki*> crew;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())crew.push_back(p);}
  check(crew.size()==size_t(count),"terminal restored population");
  check(std::fabs(n->mHealth/C_NAVI_PARM(n,mHealth)-health)<.0001f,"terminal restored health");
  std::ifstream cfg("terminal-fixture.txt");std::string fault;int pokos;
  check(bool(cfg>>fault>>pokos) && (fault=="extinction" || fault=="knockout"),"terminal fixture config");
  check(pc_p2_preview_pokos()==pokos,"terminal restored receipts");
  std::printf("P2_TERMINAL_RESTORED count=%d health=%.9g pokos=%d\n",count,health,pokos);
  if(fault=="extinction")for(Piki* p:crew)p->kill(false);
  else n->mHealth=0;
  injected=true;
  std::printf("P2_TERMINAL_INJECTED kind=%s awaiting_production_tick=1\n",fault.c_str());std::fflush(stdout);
  return result;
 }
};
int main(int argc,char**argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
 _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 check(pc_pikipelago_room_preview(),"terminal preview flag");if(!pc_window_init("P2 native terminal fixture",960,720))return 3;
 pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
 gsys->run(new TerminalFixtureApp());return 0;
}
