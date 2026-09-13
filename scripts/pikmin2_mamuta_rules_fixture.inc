class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,squad=0,buried=0,plantedBefore=0; Teki* actor=nullptr; Teki* control=nullptr;
public:
 int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<12000,"Mamuta rules startup timeout");
  // Intro-only fixture skip: never automatically skip day-end/results movies.
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(!observed)gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==221001)actor=t;if(t->mGenerator->_70==221002)control=t;}}
   require(actor&&control&&actor->mTekiType==TEKI_Miurin&&control->mTekiType==TEKI_Chappy,"Mamuta/control exact identity");
   require(pc_p2_mamuta_rules_enabled(),"P2 rules profile enabled");
   Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()){require(p->mColor==Red,"squad is red");++squad;}}
   require(squad==10,"starting squad of 10 red Pikmin");
   std::printf("P2_MAMUTA_FIXTURE_BIRTH id=221001 type=24 squad=%d color=red\n",squad);
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   n->mKontroller=new FixtureController();
   plantedBefore=GameStat::mePikis;
  }
  if(observed==30){
   InteractBury bury(actor,true,0.0f);
   Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);
    if(p&&p->isAlive()&&p->mColor==Red&&buried<3&&bury.actPiki(p)){
     ++buried; require(p->getCurrState()->getID()==PIKISTATE_Bury,"P2 bury transits to Bury");
     require(p->mHappa==Flower,"P2 buried sprout is flower-stage");
    }}
   require(buried==3,"three forced P2 buries applied");
   std::printf("P2_MAMUTA_FIXTURE_BURY forced=%d planted_before=%d\n",buried,plantedBefore);
  }
  if(observed==50){
   float before=n->mHealth;
   InteractBury nbury(actor,true,20.0f);
   require(nbury.actNavi(n),"P2 navi receiver applied");
   require(std::fabs(before-n->mHealth-5.0f)<0.001f,"captain damage exactly 5.0");
   require(n->mStateMachine->getNaviState(n)->getID()!=NAVISTATE_Bury,"captain is never buried");
   std::printf("P2_MAMUTA_FIXTURE_NAVI damage=5.0 health=%.3f\n",n->mHealth);
  }
  if(observed==70){
   int saved=GameStat::mePikis[Red];
   GameStat::mePikis.set(99,Red);
   Piki* target=nullptr; Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);
    if(p&&p->isAlive()&&p->mColor==Red&&p->getCurrState()->getID()!=PIKISTATE_Bury){target=p;break;}}
   require(target,"live squad piki available for cap probe");
   InteractBury cbury(actor,true,0.0f);
   require(!cbury.actPiki(target),"99-planted cap rejects bury");
   require(target->getCurrState()->getID()!=PIKISTATE_Bury,"cap rejection leaves piki unburied");
   GameStat::mePikis.set(saved,Red);
   std::puts("P2_MAMUTA_FIXTURE_CAP rejected_at=99");
  }
  if(observed==120){
   require(GameStat::mePikis>=plantedBefore+buried,"planted sprouts counted (mePikis)");
   std::printf("P2_MAMUTA_FIXTURE_PLANTED planted=%d expected_min=%d\n",(int)GameStat::mePikis,plantedBefore+buried);
  }
  if(observed%30==0)std::printf("P2_MAMUTA_OBSERVE tick=%d state=%d motion=%d\n",observed,actor->mStateID,actor->mTekiAnimator->getCurrentMotionIndex());
  if(observed==240)capture("mamuta-rules-live.ppm");
  if(observed==360){pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");std::puts("P2_MAMUTA_FIXTURE_RESET");}
  if(observed==363){
   require(actor->isAlive()&&control->isAlive(),"Mamuta/control died during observation");
   std::puts("PASS P2_MAMUTA_RULES_RUNTIME bury flower_stage cap99 navi_damage5 reset");
   std::fflush(nullptr);std::_Exit(0);
  }
  std::fflush(stdout);return result;
 }
};
