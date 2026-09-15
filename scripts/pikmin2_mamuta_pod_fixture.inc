// Lane 19 (#221/#168) Pod-arena natural-observation fixture (unassisted).
//
// Stages the cargo-enabled Pod arena (pc_p2_preview_ready + single `pr05`
// treasure), then free-deploys the 10-red squad in a ring around the bound
// Miurin and PARKS the captain beyond the Miurin's 70-unit TPF_AttackableRange
// so the P2 bury (5 HP/pound) hits the Pikmin, not the captain. Without that
// park the pre-existing P1 captain-down pause froze the scene mid-fight and the
// previous observation counted ~1,900 paused ticks as natural combat. Nothing
// is forced beyond squad/captain placement: no bury, lethal hit or transport
// action is assigned. A captain going down anyway (GameStat::orimaDead /
// NAVISTATE_Dead) is reported honestly as P2_MAMUTA_POD_CAPTAIN_DOWN.
class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,squad=0,plantedBefore=0,buryStates=0;
 int naturalDiedTick=0,initialPokos=0; bool deathObserved=false,transported=false,goalSeen=false;
 bool approached=false; float minDistance=1.0e9f;
 bool captainDown=false; int captainDownFrame=0;
 unsigned statesSeen=0; int lastState=-1;
 Teki* actor=nullptr; Teki* control=nullptr; Pellet* corpse=nullptr; PelletView* actorView=nullptr;
 static const int NATURAL_TICKS=3600;
 int aliveSquad(){int c=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
 bool naviDown(Navi* n){ if(GameStat::orimaDead)return true; if(n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Dead)return true; return n->mHealth<=1.0f; }
public:
 int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<30000,"Mamuta Pod natural startup timeout");
  // Intro-only fixture skip: never automatically skip day-end/results movies.
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(!observed)gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==221001)actor=t;if(t->mGenerator->_70==221002)control=t;}}
   require(actor&&control&&actor->mTekiType==TEKI_Miurin&&control->mTekiType==TEKI_Chappy,"Mamuta/control exact identity");
   require(pc_p2_mamuta_rules_enabled(),"P2 rules profile enabled");
   require(pc_p2_preview_goal(),"Pod anchor present");
   Pellet* treasure=nullptr;Iterator pt(pelletMgr);CI_LOOP(pt){Pellet* p=static_cast<Pellet*>(*pt);if(p&&p->mConfig->mModelId.mId=='pr05'&&p->mGenerator&&p->mGenerator->_70==221004)treasure=p;}
   require(treasure,"staged pr05 Pod treasure actor");
   require(pc_p2_preview_treasure()==treasure,"Pod binds the staged pr05 treasure");
   initialPokos=pc_p2_preview_pokos();require(initialPokos==0,"Pod starts at zero Pokos");
   Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()){require(p->mColor==Red,"squad is red");++squad;}}
   require(squad==10,"starting squad of 10 red Pikmin");
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   actorView=static_cast<PelletView*>(actor);
   plantedBefore=GameStat::mePikis;
   // Park the captain far beyond the Miurin's arm reach (and its ~400-unit visible
   // range, TAI): the P2 bury pounds the Pikmin, never the captain. The
   // FixtureController holds the captain at the park point (fixture placement).
   assembled=true;phase=1;ticks=0;walkGoals.clear();
   Vector3f park(actor->mSRT.t.x,0,actor->mSRT.t.z+250);park.y=mapMgr->getMinY(park.x,park.z,true);
   n->resetPosition(park);walkGoals.push_back(park);walkPoint=0;n->mKontroller=new FixtureController();
   // Free-deploy the reds in a ring around the Mamuta (radius 22) so they engage
   // it from all sides; the bury hits a frontal arc, so a ring keeps DPS up.
   int ring=0;Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);if(!p->isAlive()||p->mColor!=Red)continue;float a=float(ring)*6.2831853f/float(squad);Vector3f pt(actor->mSRT.t.x+22.0f*std::sin(a),0,actor->mSRT.t.z+22.0f*std::cos(a));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++ring;}
   std::printf("P2_MAMUTA_POD_READY generator=221004 model=pr05 pokos=%d\n",initialPokos);
   std::printf("P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=%d color=red\n",squad);
   std::printf("P2_MAMUTA_POD_APPROACH target=%.1f,%.1f actor=%.1f,%.1f park=%.1f,%.1f ring=%d\n",walkGoals[0].x,walkGoals[0].z,actor->mSRT.t.x,actor->mSRT.t.z,park.x,park.z,ring);
  }
  // Captain-down detection: if the captain is downed anyway, report it and stop
  // counting paused/frozen ticks (previously ~1,900 ticks of a paused scene were
  // reported as natural combat).
  if(!captainDown&&naviDown(n)){captainDown=true;captainDownFrame=frames;std::printf("P2_MAMUTA_POD_CAPTAIN_DOWN tick=%d health=%.1f\n",observed,n->mHealth);}
  if(captainDown){
   if(frames==captainDownFrame+3){
    int planted=GameStat::mePikis-plantedBefore;
    std::printf("P2_MAMUTA_POD_APPROACH_RESULT approached=%d min=%.1f states=%08x\n",approached?1:0,minDistance,statesSeen);
    std::printf("P2_MAMUTA_POD_PLANTED planted=%d bury_states=%d\n",planted,buryStates);
    std::printf("P2_MAMUTA_POD_RESULT died=0 died_tick=0 corpse=0 carried=0 goal=0 pokos=%d control_alive=%d squad=%d\n",pc_p2_preview_pokos(),control->isAlive()?1:0,aliveSquad());
   }
   if(frames==captainDownFrame+5)capture("mamuta-pod-final.ppm");
   if(frames==captainDownFrame+6){pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");std::puts("P2_MAMUTA_POD_RESET");}
   if(frames==captainDownFrame+9){require(control->isAlive(),"control survived captain-down observation");std::puts("PASS P2_MAMUTA_POD_RUNTIME captain_down");std::fflush(nullptr);std::_Exit(0);}
   std::fflush(stdout);return result;
  }
  if(actor->isAlive()){
   int state=actor->mStateID;if(state>=0&&state<32)statesSeen|=(1u<<state);
   // Engagement metric: closest live red to the Mamuta (the squad, not the
   // parked captain, now does the approaching).
   float closest=1.0e9f;
   Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(!p||!p->isAlive()||p->mColor!=Red)continue;float dx=actor->mSRT.t.x-p->mSRT.t.x,dz=actor->mSRT.t.z-p->mSRT.t.z;float d=std::sqrt(dx*dx+dz*dz);if(d<closest)closest=d;}
   if(closest<minDistance)minDistance=closest;
   if(closest<60.0f)approached=true;
   // Keep the captain clear of the Miurin's arm reach while the squad fights.
   float cdx=actor->mSRT.t.x-n->mSRT.t.x,cdz=actor->mSRT.t.z-n->mSRT.t.z;
   if(std::sqrt(cdx*cdx+cdz*cdz)<150.0f){Vector3f rp(actor->mSRT.t.x,0,actor->mSRT.t.z+250);rp.y=mapMgr->getMinY(rp.x,rp.z,true);n->resetPosition(rp);walkGoals.clear();walkGoals.push_back(rp);walkPoint=0;std::printf("P2_MAMUTA_POD_REPARK tick=%d\n",observed);}
   // Sustain contact: re-deploy surviving reds around the Mamuta so the bury/AI
   // does not scatter the squad permanently.
   if(observed%120==0){int r=0;Iterator pg(pikiMgr);CI_LOOP(pg){Piki* p=static_cast<Piki*>(*pg);if(!p->isAlive()||p->mColor!=Red)continue;float a=float(r)*6.2831853f/float(squad);Vector3f pt(actor->mSRT.t.x+22.0f*std::sin(a),0,actor->mSRT.t.z+22.0f*std::cos(a));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);++r;}std::printf("P2_MAMUTA_POD_RERING tick=%d reds=%d\n",observed,r);}
  }
  if(observed%30==0)
   std::printf("P2_MAMUTA_POD_OBSERVE tick=%d state=%d health=%.1f actor=%.1f,%.1f navi=%.1f,%.1f squad=%d min=%.1f states=%08x pokos=%d\n",
               observed,actor->mStateID,actor->mHealth,actor->mSRT.t.x,actor->mSRT.t.z,n->mSRT.t.x,n->mSRT.t.z,aliveSquad(),minDistance,statesSeen,pc_p2_preview_pokos());
  if(!deathObserved&&!actor->isAlive()){deathObserved=true;naturalDiedTick=observed;std::printf("P2_MAMUTA_POD_DIED tick=%d\n",observed);}
  if(deathObserved&&!corpse){
   Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(p->isAlive()&&p->mPelletView==actorView)corpse=p;}
   if(corpse)std::printf("P2_MAMUTA_POD_CORPSE tick=%d\n",observed);
  }
  if(corpse){
   int transport=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mMode==PikiMode::TransportMode)++transport;}
   if(corpse->getState()==PELSTATE_Goal)goalSeen=true;
   if(observed%60==0)std::printf("P2_MAMUTA_POD_CARRY tick=%d state=%d alive=%d transport=%d goal=%d pokos=%d\n",observed,corpse->getState(),int(corpse->isAlive()),transport,goalSeen?1:0,pc_p2_preview_pokos());
   if(!corpse->isAlive())transported=true;
  }
  {int bury=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->getCurrState()->getID()==PIKISTATE_Bury)++bury;}
   if(bury>0){buryStates+=bury;std::printf("P2_MAMUTA_POD_BURYSTATE tick=%d bury=%d\n",observed,bury);}}
  if(observed==900)capture("mamuta-pod-approach.ppm");
  if(observed==NATURAL_TICKS){
   int planted=GameStat::mePikis-plantedBefore;
   std::printf("P2_MAMUTA_POD_APPROACH_RESULT approached=%d min=%.1f states=%08x\n",approached?1:0,minDistance,statesSeen);
   std::printf("P2_MAMUTA_POD_PLANTED planted=%d bury_states=%d\n",planted,buryStates);
   std::printf("P2_MAMUTA_POD_RESULT died=%d died_tick=%d corpse=%d carried=%d goal=%d pokos=%d control_alive=%d squad=%d\n",
               deathObserved?1:0,naturalDiedTick,corpse?1:0,transported?1:0,goalSeen?1:0,pc_p2_preview_pokos(),control->isAlive()?1:0,aliveSquad());
   capture("mamuta-pod-final.ppm");
  }
  if(observed==NATURAL_TICKS+3){
   pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();
   require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");
   std::puts("P2_MAMUTA_POD_RESET");
  }
  if(observed==NATURAL_TICKS+6){
   require(control->isAlive(),"control survived natural Pod observation");
   std::puts("PASS P2_MAMUTA_POD_RUNTIME observe approach receipt reset");
   std::fflush(nullptr);std::_Exit(0);
  }
  std::fflush(stdout);return result;
 }
};
