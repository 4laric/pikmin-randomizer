#include "room-prefix.inc"
#include "Generator.h"
class BreadbugCargoFixture:public PlugPikiApp {
 int frames=0,tick=0,heldFrames=0;Teki* actor=nullptr;Pellet* cargo=nullptr;Vector3f origin,nest;bool grabbed=false;float farthest=0,initialDistance=0,bestDistance=0;
public:
 int idle() override {
  int result=PlugPikiApp::idle();require(++frames<3600,"Breadbug cargo startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  Navi* n=naviMgr->getNavi();if(!n)return result;++tick;
  if(tick==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator&&t->mGenerator->_70==186081)actor=t;}
   require(actor&&actor->mTekiType==TEKI_Collec,"Cargo proxy identity");
   n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   Vector3f forward;actor->outputDirectionVector(forward);origin=actor->mSRT.t+forward*100.0f;origin.y=mapMgr->getMinY(origin.x,origin.z,true)+5.0f;
   cargo=pelletMgr->newNumberPellet(PELCOLOR_Red,0);require(cargo,"Native 1-pellet allocation");cargo->init(origin);cargo->startAI(0);
   require(!cargo->isUfoParts()&&cargo->mConfig->mCarryMinPikis()<=2,"Source carry eligibility");
   nest=actor->getNestPosition();float dx=origin.x-nest.x,dz=origin.z-nest.z;initialDistance=bestDistance=std::sqrt(dx*dx+dz*dz);
   Vector3f view=origin+Vector3f(0,0,100);view.y=mapMgr->getMinY(view.x,view.z,true);n->resetPosition(view);
   std::printf("P2_BREADBUG_CARGO_BIRTH xyz=%.3f,%.3f,%.3f nest=%.3f,%.3f,%.3f distance=%.3f min=%d\n",origin.x,origin.y,origin.z,nest.x,nest.y,nest.z,initialDistance,cargo->mConfig->mCarryMinPikis());
  }
  bool held=actor->getCreaturePointer(2)==cargo;grabbed|=held;if(held)++heldFrames;
  float dx=cargo->mSRT.t.x-origin.x,dz=cargo->mSRT.t.z-origin.z;farthest=std::max(farthest,std::sqrt(dx*dx+dz*dz));
  dx=cargo->mSRT.t.x-nest.x;dz=cargo->mSRT.t.z-nest.z;float distance=std::sqrt(dx*dx+dz*dz);if(held)bestDistance=std::min(bestDistance,distance);
  if(tick%30==0){std::printf("P2_BREADBUG_CARGO_TICK tick=%d held=%d state=%d alive=%d distance=%.3f displacement=%.3f held_frames=%d\n",tick,int(held),actor->mStateID,int(cargo->isAlive()),distance,farthest,heldFrames);std::fflush(stdout);}
  if(heldFrames==1)capture("breadbug-cargo-grab.ppm");
  bool released=grabbed&&!held;
  if((released&&heldFrames>15)||tick>=1800){
   capture("breadbug-cargo-final.ppm");std::printf("P2_BREADBUG_CARGO_RESULT grabbed=%d held_frames=%d moved=%.3f progress=%.3f released=%d alive=%d\n",int(grabbed),heldFrames,farthest,initialDistance-bestDistance,int(released),int(cargo->isAlive()));std::fflush(nullptr);std::_Exit(0);
  }
  return result;
 }
};
int main(int argc,char** argv){SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"preview flag");if(!pc_window_init("Breadbug cargo observation",960,720))return 3;pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new BreadbugCargoFixture());return 0;}
