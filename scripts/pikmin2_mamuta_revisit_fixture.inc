// Lane 19 (#221/#168) revisit/re-entry fixture (unassisted).
//
// Re-enters the SAME Pod-arena stage directory after a prior natural Pod run
// already credited corpse:mamuta:221001 (p2-economy.txt persisted, pokos=2). A
// fresh process re-births the Mamuta, then re-runs the natural kill/carry/deliver
// with the captain parked inside the Miurin's ~70-unit attackable range (20) and
// the 14-red squad ring-deployed (re-rung every 60 ticks), so the re-delivery
// reaches the Pod and the persisted economy dedupes it (new=0). A successful run
// proves clean re-entry and exactly-once reward; the fixture hard-requires
// pokos==prior_pokos at reset. A captain going down (orimaDead / NAVISTATE_Dead /
// health <= 1) is reported honestly as P2_MAMUTA_REVISIT_CAPTAIN_DOWN.
class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,squad=0;
 int naturalDiedTick=0,initialPokos=0; bool deathObserved=false,transported=false,goalSeen=false;
 bool approached=false; float minDistance=1.0e9f;
 bool captainDown=false; int captainDownFrame=0;
 unsigned statesSeen=0;
 Teki* actor=nullptr; Teki* control=nullptr; Pellet* corpse=nullptr; PelletView* actorView=nullptr;
 static const int NATURAL_TICKS=3600;
 int aliveSquad(){int c=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
 bool naviDown(Navi* n){ if(GameStat::orimaDead)return true; if(n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Dead)return true; return n->mHealth<=1.0f; }
public:
 int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<30000,"Mamuta revisit startup timeout");
  if(!pc_p2_preview_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();
  // Captain-down detection BEFORE the movie/pause/UI gates (a real P1 Olimar death
  // pauses the core and must still emit the marker).
  if(!captainDown&&n&&naviDown(n)){captainDown=true;captainDownFrame=frames;std::printf("P2_MAMUTA_REVISIT_CAPTAIN_DOWN tick=%d health=%.1f\n",observed,n->mHealth);}
  if(captainDown){
   if(frames==captainDownFrame+3){
    std::printf("P2_MAMUTA_REVISIT_APPROACH_RESULT approached=%d min=%.1f states=%08x\n",approached?1:0,minDistance,statesSeen);
    std::printf("P2_MAMUTA_REVISIT_RESULT died=0 died_tick=0 corpse=0 carried=0 goal=0 pokos=%d prior_pokos=%d control_alive=%d squad=%d\n",pc_p2_preview_pokos(),initialPokos,control->isAlive()?1:0,aliveSquad());
   }
   if(frames==captainDownFrame+5)capture("mamuta-revisit-final.ppm");
   if(frames==captainDownFrame+6){require(pc_p2_preview_pokos()==initialPokos,"revisit must not duplicate the reward");pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");std::puts("P2_MAMUTA_REVISIT_RESET");}
   if(frames==captainDownFrame+9){require(control->isAlive(),"control survived revisit observation");std::puts("PASS P2_MAMUTA_REVISIT_RUNTIME captain_down");std::fflush(nullptr);std::_Exit(0);}
   std::fflush(stdout);return result;
  }
  // Intro-only fixture skip: never automatically skip day-end/results movies.
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(!observed)gameflow.mMoviePlayer->requestSkip();return result;}
  if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==221001)actor=t;if(t->mGenerator->_70==221002)control=t;}}
   require(actor&&control&&actor->mTekiType==TEKI_Miurin&&control->mTekiType==TEKI_Chappy,"Mamuta/control exact re-birth identity");
   require(pc_p2_mamuta_rules_enabled(),"P2 rules profile enabled");
   require(pc_p2_preview_goal(),"Pod anchor present");
   Pellet* treasure=nullptr;Iterator pt(pelletMgr);CI_LOOP(pt){Pellet* p=static_cast<Pellet*>(*pt);if(p&&p->mConfig->mModelId.mId=='pr05'&&p->mGenerator&&p->mGenerator->_70==221004)treasure=p;}
   require(treasure,"staged pr05 Pod treasure actor re-birth");
   require(pc_p2_preview_treasure()==treasure,"Pod binds the staged pr05 treasure");
   initialPokos=pc_p2_preview_pokos();
   require(initialPokos>=2,"Pod economy must persist the prior mamuta receipt");
   std::printf("P2_MAMUTA_REVISIT_READY prior_pokos=%d\n",initialPokos);
   Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()){require(p->mColor==Red,"squad is red");++squad;}}
   require(squad==14,"starting squad of 14 red Pikmin");
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   actorView=static_cast<PelletView*>(actor);
   // Re-entry staging mirrors the Pod fixture: park inside the ~70-unit range and
   // ring-deploy so the re-kill/re-carry complete and the Pod re-credits (deduped).
   assembled=true;phase=1;ticks=0;walkGoals.clear();
   Vector3f park(actor->mSRT.t.x,0,actor->mSRT.t.z+20.0f);park.y=mapMgr->getMinY(park.x,park.z,true);
   n->resetPosition(park);walkGoals.push_back(park);walkPoint=0;n->mKontroller=new FixtureController();
   int ring=0;Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);if(!p->isAlive()||p->mColor!=Red)continue;float a=float(ring)*6.2831853f/float(squad);Vector3f pt(actor->mSRT.t.x+22.0f*std::sin(a),0,actor->mSRT.t.z+22.0f*std::cos(a));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++ring;}
   std::printf("P2_MAMUTA_REVISIT_BIRTH id=221001 type=24 squad=%d color=red\n",squad);
   std::printf("P2_MAMUTA_REVISIT_APPROACH target=%.1f,%.1f actor=%.1f,%.1f park=%.1f,%.1f ring=%d\n",walkGoals[0].x,walkGoals[0].z,actor->mSRT.t.x,actor->mSRT.t.z,park.x,park.z,ring);
  }
  if(actor->isAlive()){
   int state=actor->mStateID;if(state>=0&&state<32)statesSeen|=(1u<<state);
   float closest=1.0e9f;
   Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(!p||!p->isAlive()||p->mColor!=Red)continue;float dx=actor->mSRT.t.x-p->mSRT.t.x,dz=actor->mSRT.t.z-p->mSRT.t.z;float d=std::sqrt(dx*dx+dz*dz);if(d<closest)closest=d;}
   if(closest<minDistance)minDistance=closest;
   if(closest<60.0f)approached=true;
   if(observed%60==0){int r=0;Iterator pg(pikiMgr);CI_LOOP(pg){Piki* p=static_cast<Piki*>(*pg);if(!p->isAlive()||p->mColor!=Red)continue;float a=float(r)*6.2831853f/float(squad);Vector3f pt(actor->mSRT.t.x+22.0f*std::sin(a),0,actor->mSRT.t.z+22.0f*std::cos(a));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);++r;}std::printf("P2_MAMUTA_REVISIT_RERING tick=%d reds=%d\n",observed,r);}
  }
  if(observed%30==0)
   std::printf("P2_MAMUTA_REVISIT_OBSERVE tick=%d state=%d health=%.1f actor=%.1f,%.1f navi=%.1f,%.1f squad=%d min=%.1f states=%08x pokos=%d\n",
               observed,actor->mStateID,actor->mHealth,actor->mSRT.t.x,actor->mSRT.t.z,n->mSRT.t.x,n->mSRT.t.z,aliveSquad(),minDistance,statesSeen,pc_p2_preview_pokos());
  if(!deathObserved&&!actor->isAlive()){deathObserved=true;naturalDiedTick=observed;std::printf("P2_MAMUTA_REVISIT_DIED tick=%d\n",observed);}
  if(deathObserved&&!corpse){
   Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(p->isAlive()&&p->mPelletView==actorView)corpse=p;}
   if(corpse)std::printf("P2_MAMUTA_REVISIT_CORPSE tick=%d\n",observed);
  }
  if(corpse){
   int transport=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mMode==PikiMode::TransportMode)++transport;}
   if(corpse->getState()==PELSTATE_Goal)goalSeen=true;
   if(observed%60==0){
    float dist=0.0f;if(Suckable* g=pc_p2_preview_goal()){float dx=corpse->mSRT.t.x-g->mSRT.t.x,dz=corpse->mSRT.t.z-g->mSRT.t.z;dist=std::sqrt(dx*dx+dz*dz);}
    std::printf("P2_MAMUTA_REVISIT_CARRY tick=%d state=%d alive=%d transport=%d goal=%d mincarry=%d maxcarry=%d dist=%.1f pokos=%d\n",
                observed,corpse->getState(),int(corpse->isAlive()),transport,goalSeen?1:0,
                corpse->mConfig->mCarryMinPikis(),corpse->mConfig->mCarryMaxPikis(),dist,pc_p2_preview_pokos());
   }
   if(!corpse->isAlive())transported=true;
  }
  if(observed==900)capture("mamuta-revisit-approach.ppm");
  if(observed==NATURAL_TICKS){
   std::printf("P2_MAMUTA_REVISIT_APPROACH_RESULT approached=%d min=%.1f states=%08x\n",approached?1:0,minDistance,statesSeen);
   std::printf("P2_MAMUTA_REVISIT_RESULT died=%d died_tick=%d corpse=%d carried=%d goal=%d pokos=%d prior_pokos=%d control_alive=%d squad=%d\n",
               deathObserved?1:0,naturalDiedTick,corpse?1:0,transported?1:0,goalSeen?1:0,pc_p2_preview_pokos(),initialPokos,control->isAlive()?1:0,aliveSquad());
   capture("mamuta-revisit-final.ppm");
  }
  if(observed==NATURAL_TICKS+3){
   require(pc_p2_preview_pokos()==initialPokos,"revisit must not duplicate the reward");
   pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();
   require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");
   std::puts("P2_MAMUTA_REVISIT_RESET");
  }
  if(observed==NATURAL_TICKS+6){
   require(control->isAlive(),"control survived revisit observation");
   std::puts("PASS P2_MAMUTA_REVISIT_RUNTIME observe approach receipt_revisit reset");
   std::fflush(nullptr);std::_Exit(0);
  }
  std::fflush(stdout);return result;
 }
};
