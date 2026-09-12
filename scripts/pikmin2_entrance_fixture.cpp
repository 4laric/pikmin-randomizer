// Standalone entrance fixture: production movement/collision against engineering walls.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "MapMgr.h"
#include "Collision.h"
#include "PlayerState.h"
#include "Demo.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <initializer_list>
#include <cstdio>
#include <cstdlib>
static void check(bool value,const char* text){if(!value){std::printf("FAIL entrance: %s\n",text);std::fflush(stdout);std::_Exit(1);}}
static float radial(Vector3f p){return std::sqrt((p.x+190)*(p.x+190)+(p.z-1160)*(p.z-1160));}
class EntranceApp:public PlugPikiApp {
 int frames=0,ready=0;
public:
 int idle() override {
  int result=PlugPikiApp::idle();check(++frames<3000,"startup timeout");
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready() || !naviMgr || !pikiMgr)return result;
  pc_p2_preview_treasure()->mConfig->mCarryMinPikis.mValue=1000; // Fixture has no hauling goal.
  Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState() || n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
  if(++ready<30)return result;
  check(std::fabs(mapMgr->getMinY(-190,1160,true)-80)<.05f,"source ground height");
  check(radial(n->mSRT.t)<=60 && std::fabs(n->mSRT.t.y-80)<5,"captain spawn outside floor");
  int count=0;Piki* first=nullptr;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()){++count;first=p;check(radial(p->mSRT.t)<60,"Pikmin spawn outside");}}
  check(count==20 && first,"twenty field Pikmin");
  Pellet* cargo=pc_p2_preview_treasure();check(cargo,"cargo specimen missing");
  int probes=0;
  for(Creature* actor:{static_cast<Creature*>(n),static_cast<Creature*>(first),static_cast<Creature*>(cargo)}) {
   for(float radius:{6.f,10.f,20.f})for(float height:{120.f,400.f,4000.f})for(int angle=0;angle<32;++angle){
    float a=angle*6.28318530718f/32.f;Vector3f dir(std::cos(a),0,std::sin(a));
    Vector3f pos(-190,height,1160);
    for(int tick=0;tick<90;++tick){
     Vector3f velocity=dir*180.f;MoveTrace trace(pos,velocity,radius,true);
     mapMgr->traceMove(actor,trace,1.f/60.f);pos=trace.mPosition;
     check(std::isfinite(pos.x)&&std::isfinite(pos.y)&&std::isfinite(pos.z),"nonfinite native trace");
     check(radial(pos)<=60.1f,"native sphere escaped boundary");
    }
    check(radial(pos)>20,"trace did not advance toward wall");++probes;
   }
  }
  // Actual mover, not just a geometry trace: launch one live Pikmin above the floor.
  Vector3f old=first->mSRT.t;first->resetPosition(Vector3f(-190,400,1160));
  for(int tick=0;tick<120;++tick){first->mVelocity.x=180;first->mVelocity.z=0;first->moveNew(1.f/60.f);check(radial(first->mSRT.t)<=60.1f,"airborne Pikmin escaped");}
  first->resetPosition(old);
  std::printf("PASS P2_ENTRANCE_BOUNDARY native_probes=%d captain_ground=80 pikmin=20 airborne_steps=120 radius=60 water_unreachable_fixture_only\n",probes);
  std::fflush(stdout);std::_Exit(0);
 }
};
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
 _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
 check(pc_pikipelago_room_preview(),"room preview flag required");
 if(!pc_window_init("P2 entrance boundary fixture",960,720))return 3;
 pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new EntranceApp());return 0;
}

