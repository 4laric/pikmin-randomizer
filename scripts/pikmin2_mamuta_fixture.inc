class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,waitFrames=0; Teki* actor=nullptr; Teki* control=nullptr; bool finished=false,waitCaptured=false;
public:
 int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<12000,"Mamuta startup timeout");
  // Intro-only fixture skip: never automatically skip day-end/results movies.
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(!observed)gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==221001)actor=t;if(t->mGenerator->_70==221002)control=t;}}
   require(actor&&control&&actor->mTekiType==TEKI_Miurin&&control->mTekiType==TEKI_Chappy,"Mamuta/control exact identity");
   Vector3f b=actor->mPersonality->mPosition;
   require(std::fabs(b.x+150)<.02&&std::fabs(b.y-30)<.02&&std::fabs(b.z-1850)<.02,"Mamuta stored full birth XYZ");
   std::printf("P2_MAMUTA_FIXTURE_BIRTH id=221001 type=24 xyz=%.3f,%.3f,%.3f control=221002\n",b.x,b.y,b.z);
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   n->mKontroller=new FixtureController();Vector3f near(-150,0,2150);near.y=mapMgr->getMinY(near.x,near.z,true);n->resetPosition(near);
  }
  require(actor->isAlive()&&control->isAlive(),"Mamuta/control died during observation");
  if(observed%30==0)std::printf("P2_MAMUTA_OBSERVE tick=%d state=%d motion=%d counter=%.3f\n",observed,actor->mStateID,actor->mTekiAnimator->getCurrentMotionIndex(),actor->mTekiAnimator->getCounter());
  if(observed==120)capture("mamuta-live.ppm");
  if(observed==300){pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();std::puts("P2_MAMUTA_FIXTURE_RESET");}
  if(observed==303){capture("mamuta-reset.ppm");finished=true;}
  std::fflush(stdout);return result;
 }
 void draw(Graphics& gfx) override {
  PlugPikiApp::draw(gfx);
  if(actor&&actor->mTekiAnimator->getCurrentMotionIndex()==TekiMotion::Wait1)++waitFrames;else waitFrames=0;
  if(actor&&waitFrames>=10&&!waitCaptured&&observed>0&&observed<300&&actor->mTekiAnimator->getCurrentMotionIndex()==TekiMotion::Wait1){capture("mamuta-source-wait.ppm");waitCaptured=true;std::puts("P2_MAMUTA_WAIT_CAPTURE natural_motion=2");}
  Matrix4f unused;
  if(control)require(!pc_p2_mamuta_draw(control,gfx,unused),"ordinary Chappy acquired Mamuta visual");
  if(finished){require(!pc_p2_mamuta_draw(actor,gfx,unused),"forgotten Mamuta retained visual");std::puts("PASS P2_MAMUTA_RUNTIME identity control reset P1_proxy_static_anchors");std::fflush(nullptr);std::_Exit(0);}
 }
};
