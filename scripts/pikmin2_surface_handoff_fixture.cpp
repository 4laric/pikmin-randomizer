// Private source-entrance handoff fixture; reuse production restoration/checkpoint guard.
#define main previous_boundary_main
#include "pikmin2_entrance_fixture.cpp"
#undef main
#include "pc_p2_cave.h"
#include "pc_p2_purple.h"
#include <fstream>
#include <string>
#define NOMINMAX
#define HWND NativeWindowHandle
#include <windows.h>
#undef HWND

class SurfaceHandoffApp:public PlugPikiApp {
 int frames=0,ready=0;
public:
 int idle() override {
  int result=PlugPikiApp::idle();check(++frames<3000,"surface startup timeout");
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready() || !pc_p2_cave_floor() || !naviMgr || !pikiMgr)return result;
  pc_p2_preview_treasure()->mConfig->mCarryMinPikis.mValue=1000;
  Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState() || n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
  if(++ready<30)return result;
  std::ifstream input("p2-cave-entry.txt");std::string version,token;int floor,count;float health;
  check(bool(input>>version>>token>>floor>>health>>count),"surface entry framing");
  int expected[4][3]={},actual[4][3]={};for(int i=0;i<count;++i){int c,h;check(bool(input>>c>>h),"entry species");++expected[c][h];}
  Iterator it(pikiMgr);int total=0;CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()){++actual[pc_p2_is_purple(p)?3:p->mColor][p->mHappa];++total;check(radial(p->mSRT.t)<=60.1f,"restored party outside ring");}}
  check(total==count,"native restored count");for(int c=0;c<4;++c)for(int h=0;h<3;++h)check(actual[c][h]==expected[c][h],"native species/maturity mismatch");
  check(std::fabs(n->mHealth/C_NAVI_PARM(n,mHealth)-health)<.0001f,"restored captain health");
  std::ifstream settings("surface-fixture.txt");std::string mode;float x,y,z;int pokos;
  check(bool(settings>>mode>>x>>y>>z>>pokos),"surface fixture config");
  check(pc_p2_preview_pokos()==pokos,"native receipt balance");
  check(std::fabs(n->mSRT.t.x-x)<1 && std::fabs(n->mSRT.t.y-y)<1 && std::fabs(n->mSRT.t.z-z)<1,"source position changed");
  check(radial(n->mSRT.t)<60 && std::fabs(mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true)-80)<.05f,"source pocket ground");
  std::ofstream position("surface-position.txt");position.precision(9);position<<token<<'\n'<<n->mSRT.t.x<<' '<<n->mSRT.t.y<<' '<<n->mSRT.t.z<<'\n';position.close();
  if(mode=="enter"){
   gameflow.mPauseAll=true;check(!pc_p2_cave_checkpoint(false),"paused entry accepted");gameflow.mPauseAll=false;
   check(!pc_p2_cave_interact(-500,80,1160),"foreign entry actor accepted");
   check(pc_p2_cave_interact(-190,80,1160),"source entrance interaction rejected");
   check(pc_p2_cave_checkpoint(false),"source F6-equivalent checkpoint rejected");
   check(!pc_p2_cave_checkpoint(false),"duplicate source checkpoint accepted");
   std::printf("PASS P2_SURFACE_ENTER native_count=%d health=%.9g pokos=%d position=%.3f,%.3f,%.3f\n",total,health,pokos,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);std::fflush(nullptr);std::_Exit(42);
  }
  check(mode=="return","unknown surface fixture mode");
  std::printf("PASS P2_SURFACE_RETURN native_count=%d health=%.9g pokos=%d position=%.3f,%.3f,%.3f\n",total,health,pokos,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);std::fflush(nullptr);std::_Exit(0);
 }
};
static LONG CALLBACK reportCrash(EXCEPTION_POINTERS* info){
 if(info->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION){
  auto base=reinterpret_cast<uintptr_t>(GetModuleHandleA(nullptr));
  std::fprintf(stderr,"SURFACE_CRASH address=%p image_offset=%llx\n",info->ExceptionRecord->ExceptionAddress,
    static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(info->ExceptionRecord->ExceptionAddress)-base));std::fflush(stderr);
 }
 return EXCEPTION_CONTINUE_SEARCH;
}
int main(int argc,char**argv){
 AddVectoredExceptionHandler(1,reportCrash);
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 check(pc_pikipelago_room_preview(),"room preview flag required");if(!pc_window_init("P2 bounded surface handoff fixture",960,720))return 3;
 pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new SurfaceHandoffApp());return 0;
}
