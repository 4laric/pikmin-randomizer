// Lane 19 (#221/#168) natural-observation fixture.
//
// Unlike the batch-4 rules fixture, this run never forces a bury or a lethal
// hit. It stages the same arena + rules marker + 10-red squad, drives the
// captain toward the bound Miurin so the squad enters its territory, and then
// records what the native P1-proxy AI does on its own: attack-state
// transitions, natural `P2_MAMUTA_PLANT` events from the rules module (natural
// flick bury), natural Pikmin damage on the actor, natural death/corpse,
// carry state, and rules reset/re-entry. Behavioural gates are classified by
// the Python validator from the emitted markers; the fixture only observes.
class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,squad=0,plantedBefore=0,buryStates=0;
 int naturalDiedTick=0; bool deathObserved=false,transported=false,goalSeen=false;
 bool approached=false; float minDistance=1.0e9f;
 unsigned statesSeen=0; int lastState=-1;
 Teki* actor=nullptr; Teki* control=nullptr; Pellet* corpse=nullptr; PelletView* actorView=nullptr;
 static const int NATURAL_TICKS=2400;
 int aliveSquad(){int c=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
public:
 int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<30000,"Mamuta natural startup timeout");
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
   require(squad==14,"starting squad of 14 red Pikmin");
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   actorView=static_cast<PelletView*>(actor);
   plantedBefore=GameStat::mePikis;
   // Natural approach: walk the captain to the Miurin so the squad follows into
   // its territory and the proxy watchdogs/attacks on its own. No AI action is
   // assigned to any Pikmin and no bury/attack interaction is forced.
   assembled=true; phase=1; ticks=0; walkGoals.clear();
   walkGoals.push_back(Vector3f(actor->mSRT.t.x,0,actor->mSRT.t.z+20)); walkPoint=0;
   n->mKontroller=new FixtureController();
   std::printf("P2_MAMUTA_NATURAL_BIRTH id=221001 type=24 squad=%d color=red\n",squad);
   std::printf("P2_MAMUTA_NATURAL_APPROACH target=%.1f,%.1f actor=%.1f,%.1f\n",walkGoals[0].x,walkGoals[0].z,actor->mSRT.t.x,actor->mSRT.t.z);
  }
  // Track natural state coverage and closest approach (either side closing in).
  if(actor->isAlive()){
   int state=actor->mStateID; if(state>=0&&state<32)statesSeen|=(1u<<state);
   float dx=actor->mSRT.t.x-n->mSRT.t.x,dz=actor->mSRT.t.z-n->mSRT.t.z;
   float distance=std::sqrt(dx*dx+dz*dz);if(distance<minDistance)minDistance=distance;
   if(distance<60.0f)approached=true;
  }
  if(observed%30==0)
   std::printf("P2_MAMUTA_NATURAL_OBSERVE tick=%d state=%d health=%.1f navi=%.1f,%.1f squad=%d min=%.1f states=%08x\n",
               observed,actor->mStateID,actor->mHealth,n->mSRT.t.x,n->mSRT.t.z,aliveSquad(),minDistance,statesSeen);
  if(!deathObserved&&!actor->isAlive()){deathObserved=true;naturalDiedTick=observed;std::printf("P2_MAMUTA_NATURAL_DIED tick=%d\n",observed);}
  if(deathObserved&&!corpse){
   Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(p->isAlive()&&p->mPelletView==actorView)corpse=p;}
   if(corpse)std::printf("P2_MAMUTA_NATURAL_CORPSE tick=%d\n",observed);
  }
  if(corpse){
   int transport=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mMode==PikiMode::TransportMode)++transport;}
   if(corpse->getState()==PELSTATE_Goal)goalSeen=true;
   if(observed%60==0)std::printf("P2_MAMUTA_NATURAL_CARRY tick=%d state=%d alive=%d transport=%d goal=%d\n",observed,corpse->getState(),int(corpse->isAlive()),transport,goalSeen?1:0);
   if(!corpse->isAlive())transported=true;
  }
  {int bury=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->getCurrState()->getID()==PIKISTATE_Bury)++bury;}
   if(bury>0){buryStates+=bury;std::printf("P2_MAMUTA_NATURAL_BURYSTATE tick=%d bury=%d\n",observed,bury);}}
  if(observed==900)capture("mamuta-natural-approach.ppm");
  if(observed==NATURAL_TICKS){
   int planted=GameStat::mePikis-plantedBefore;
   std::printf("P2_MAMUTA_NATURAL_APPROACH_RESULT approached=%d min=%.1f states=%08x\n",approached?1:0,minDistance,statesSeen);
   std::printf("P2_MAMUTA_NATURAL_PLANTED planted=%d bury_states=%d\n",planted,buryStates);
   std::printf("P2_MAMUTA_NATURAL_RESULT died=%d died_tick=%d corpse=%d carried=%d goal=%d control_alive=%d squad=%d\n",
               deathObserved?1:0,naturalDiedTick,corpse?1:0,transported?1:0,goalSeen?1:0,control->isAlive()?1:0,aliveSquad());
   capture("mamuta-natural-final.ppm");
  }
  if(observed==NATURAL_TICKS+3){
   pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();
   require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");
   std::puts("P2_MAMUTA_NATURAL_RESET");
  }
  if(observed==NATURAL_TICKS+6){
   require(control->isAlive(),"control survived natural observation");
   std::puts("PASS P2_MAMUTA_NATURAL_RUNTIME observe approach reset");
   std::fflush(nullptr);std::_Exit(0);
  }
  std::fflush(stdout);return result;
 }
};
