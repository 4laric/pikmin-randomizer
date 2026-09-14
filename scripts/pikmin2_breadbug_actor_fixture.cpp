#include "room-prefix.inc"
#include "PelletView.h"
#include "pc_window.h"
#include "pc_p2_breadbug_actor.h"
#include "Generator.h"
class BreadbugActorFixture:public PlugPikiApp {
 int frames=0,ready=0,moving=0,resetFrame=0,reentryFrame=0,killFrame=0,phase=0;
 Teki* actor=nullptr;Teki* control=nullptr;Vector3f origin;float farthest=0;
 bool resetDone=false,reentryDone=false,killed=false;
public:
 int idle() override {
  int result=PlugPikiApp::idle();require(++frames<2400,"Breadbug actor timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
  if(ready==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==186081)actor=t;if(t->mGenerator->_70==186082)control=t;}}
   require(actor&&control&&actor!=control&&actor->mTekiType==TEKI_Collec&&control->mTekiType==TEKI_Collec,"Breadbug proxy/control identity");
   origin=actor->mSRT.t;n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   std::printf("P2_BREADBUG_ARENA_ACTORS proxy=%u control=%u initial=%.6f,%.6f,%.6f\n",actor->mGenerator->_70,control->mGenerator->_70,origin.x,origin.y,origin.z);
   Vector3f near=origin+Vector3f(0,0,100);near.y=mapMgr->getMinY(near.x,near.z,true);n->resetPosition(near);
  }
  require(control->isAlive()&&(killed||actor->isAlive()),"proxy/control died before injected death");
  float dx=actor->mSRT.t.x-origin.x,dz=actor->mSRT.t.z-origin.z;farthest=std::max(farthest,std::sqrt(dx*dx+dz*dz));
  if(actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1)++moving;
  if(ready==60)capture("breadbug-actor-start.ppm");
  if(ready%60==0){std::printf("P2_BREADBUG_ARENA_MOVE frame=%d displacement=%.6f moving=%d xyz=%.6f,%.6f,%.6f\n",ready,farthest,moving,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);std::fflush(stdout);}
  if(!resetDone&&ready>=300&&farthest>15&&moving>=15){capture("breadbug-actor-moved.ppm");pc_p2_breadbug_actor_reset();resetDone=true;resetFrame=ready;std::puts("P2_BREADBUG_ARENA_RESET");std::fflush(stdout);}
  if(resetDone&&!reentryDone&&ready>=resetFrame+3){pc_p2_breadbug_actor_setup();reentryDone=true;reentryFrame=ready;std::puts("P2_BREADBUG_ACTOR_REENTRY");std::fflush(stdout);}
  if(reentryDone&&!killed&&ready>=reentryFrame+3){
   capture("breadbug-actor-reentry.ppm");
   actor->mHealth=0.0f;killed=true;killFrame=ready;
   std::puts("P2_BREADBUG_ACTOR_DEATH_INJECTED health0");std::printf("P2_BREADBUG_ACTOR_KILL frame=%d\n",killFrame);std::fflush(stdout);
  }
  if(killed&&actor->isAlive()&&ready>=killFrame+300){std::puts("P2_BREADBUG_ACTOR_DEATH_UNFIRED alive=1");std::fflush(stdout);std::_Exit(1);}
  require(ready<2000,"Breadbug autonomous movement not demonstrated");return result;
 }
 void draw(Graphics& gfx) override {
  PlugPikiApp::draw(gfx);
  if(!actor||!control)return;Matrix4f unused;
  if(phase==0&&resetDone&&!reentryDone){
   require(!pc_p2_breadbug_actor_draw(actor,gfx,unused),"reset retained actor visual mapping");
   require(!pc_p2_breadbug_actor_draw(control,gfx,unused),"control acquired proxy visuals");
   phase=1;
  }else if(phase==1&&reentryDone&&!killed){
   require(pc_p2_breadbug_actor_draw(actor,gfx,unused),"re-entry did not restore proxy mapping");
   require(!pc_p2_breadbug_actor_draw(control,gfx,unused),"control acquired proxy visuals after re-entry");
   phase=2;
  }else if(phase==2&&killed&&!actor->isAlive()){
   require(!pc_p2_breadbug_actor_draw(actor,gfx,unused),"dead actor still mapped");
   int bodies=0;Iterator p(pelletMgr);CI_LOOP(p){Pellet* body=static_cast<Pellet*>(*p);if(body->isAlive()&&body->mPelletView==static_cast<PelletView*>(actor))++bodies;}
   std::printf("P2_BREADBUG_ACTOR_DEATH corpse=%d\n",bodies);
   std::puts("PASS P2_BREADBUG_ACTOR_ARENA natural_P1_movement reset_reentry death_cleanup");std::fflush(nullptr);std::_Exit(0);
  }
 }
};
int main(int argc,char** argv){SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"preview flag");if(!pc_window_init("Breadbug actor arena",960,540))return 3;pc_settings_init();pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();std::puts("Experimental preview window set to 960x540 windowed and centered");gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new BreadbugActorFixture());return 0;}
