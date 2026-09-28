#include "room-prefix.inc"
#include "pc_p2_tank.h"
#include "Generator.h"
class TankActorFixture:public PlugPikiApp {
 int frames=0,ready=0,moving=0,resetFrame=0;Teki* actor=nullptr;Teki* control=nullptr;Vector3f origin;float farthest=0;bool resetDone=false,finish=false;
public:
 int idle() override {
  int result=PlugPikiApp::idle();require(++frames<3600,"Tank actor timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(ready==0)gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
  if(ready==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==186151)actor=t;if(t->mGenerator->_70==186152)control=t;}}
   require(actor&&control&&actor!=control&&actor->mTekiType==TEKI_Tank&&control->mTekiType==TEKI_Tank,"Tank proxy/control identity");
   std::printf("P2_TANK_CONTROL generator=186152 xyz=%.6f,%.6f,%.6f\n",control->mSRT.t.x,control->mSRT.t.y,control->mSRT.t.z);
   Iterator waterCheck(tekiMgr);CI_LOOP(waterCheck){Teki* t=static_cast<Teki*>(*waterCheck);require(!t||!t->mGenerator||t->mGenerator->_70!=186153,"water display allocated native actor");}
   origin=actor->mSRT.t;n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   std::printf("P2_TANK_ARENA_ACTORS proxy=%u control=%u initial=%.6f,%.6f,%.6f\n",actor->mGenerator->_70,control->mGenerator->_70,origin.x,origin.y,origin.z);
   Vector3f near=origin+Vector3f(0,0,100);near.y=mapMgr->getMinY(near.x,near.z,true);n->resetPosition(near);
  }
  require(actor->isAlive()&&control->isAlive(),"proxy/control died during movement smoke");
  float dx=actor->mSRT.t.x-origin.x,dz=actor->mSRT.t.z-origin.z;farthest=std::max(farthest,std::sqrt(dx*dx+dz*dz));
  if(actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1)++moving;
  if(ready%30==0)std::printf("P2_TANK_COUNTER state=%d motion=%d counter=%.6f frames=%d\n",actor->mStateID,actor->mTekiAnimator->getCurrentMotionIndex(),actor->mTekiAnimator->getCounter(),actor->mTekiAnimator->getFrameCount());
  if(ready==60)capture("tank-actor-start.ppm");
  if(ready%60==0){std::printf("P2_TANK_ARENA_MOVE frame=%d displacement=%.6f moving=%d xyz=%.6f,%.6f,%.6f\n",ready,farthest,moving,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);std::fflush(stdout);}
  if(!resetDone&&ready>=300&&farthest>15&&moving>=15){capture("tank-actor-moved.ppm");pc_p2_tank_reset();resetDone=true;resetFrame=ready;std::puts("P2_TANK_ARENA_RESET");}
  if(resetDone){if(ready>=resetFrame+3){capture("tank-actor-reset.ppm");finish=true;}}
  require(ready<900,"Tank autonomous movement not demonstrated");return result;
 }
 void draw(Graphics& gfx) override {
  PlugPikiApp::draw(gfx);
  if(finish){Matrix4f unused;require(!pc_p2_tank_draw(actor,gfx,unused),"reset retained actor visual mapping");require(!pc_p2_tank_draw(control,gfx,unused),"control acquired proxy visuals");std::puts("PASS P2_TANK_ACTOR_ARENA natural_P1_movement reset_declines unchanged_control");std::fflush(nullptr);std::_Exit(0);}
 }
};
int main(int argc,char** argv){SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"preview flag");if(!pc_window_init("Tank actor arena",960,720))return 3;pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TankActorFixture());return 0;}
