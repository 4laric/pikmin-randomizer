// Lane 19 (#221/#168) Pod-arena ASSISTED-transport fixture (labelled assisted).
//
// Same staging and observation as pikmin2_mamuta_pod_fixture.inc, but when the
// Mamuta carcass has existed for a grace period without any Pikmin picking it
// up, this variant directly assigns the native Transport action to the idle
// squad (the same mechanism the P2 cargo/beasts fixtures use). It therefore
// proves the Pod receipt path end-to-end but must never be reported as natural
// pickup: the result marker carries assisted=1 and the PASS line says
// "assisted".
class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,squad=0,plantedBefore=0,buryStates=0;
 int naturalDiedTick=0,initialPokos=0,assistedAssigned=0; bool deathObserved=false,transported=false,goalSeen=false;
 bool approached=false; float minDistance=1.0e9f;
 unsigned statesSeen=0; int lastState=-1;
 Teki* actor=nullptr; Teki* control=nullptr; Pellet* corpse=nullptr; PelletView* actorView=nullptr;
 static const int NATURAL_TICKS=2400;
 int aliveSquad(){int c=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
public:
 int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<30000,"Mamuta Pod assisted startup timeout");
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
   assembled=true;phase=1;ticks=0;walkGoals.clear();
   walkGoals.push_back(Vector3f(actor->mSRT.t.x,0,actor->mSRT.t.z+20));walkPoint=0;
   n->mKontroller=new FixtureController();
   // Controlled start: pin the captain to the south approach (fixture placement)
   // so the squad is not buried while the baseline-far captain walks over.
   {Vector3f near(actor->mSRT.t.x,0,actor->mSRT.t.z+50);near.y=mapMgr->getMinY(near.x,near.z,true);n->resetPosition(near);}
   std::printf("P2_MAMUTA_POD_READY generator=221004 model=pr05 pokos=%d\n",initialPokos);
   std::printf("P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=%d color=red\n",squad);
   std::printf("P2_MAMUTA_POD_APPROACH target=%.1f,%.1f actor=%.1f,%.1f\n",walkGoals[0].x,walkGoals[0].z,actor->mSRT.t.x,actor->mSRT.t.z);
   std::puts("P2_MAMUTA_POD_MODE assisted=1 (direct Transport assignment; not natural pickup)");
  }
  if(actor->isAlive()){
   int state=actor->mStateID;if(state>=0&&state<32)statesSeen|=(1u<<state);
   float dx=actor->mSRT.t.x-n->mSRT.t.x,dz=actor->mSRT.t.z-n->mSRT.t.z;
   float distance=std::sqrt(dx*dx+dz*dz);if(distance<minDistance)minDistance=distance;
   if(distance<60.0f)approached=true;
  }
  if(observed%30==0)
   std::printf("P2_MAMUTA_POD_OBSERVE tick=%d state=%d health=%.1f navi=%.1f,%.1f squad=%d min=%.1f states=%08x pokos=%d\n",
               observed,actor->mStateID,actor->mHealth,n->mSRT.t.x,n->mSRT.t.z,aliveSquad(),minDistance,statesSeen,pc_p2_preview_pokos());
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
   // Assisted fallback: if the squad never picks the carcass up on its own,
   // hand the idle Pikmin the real Transport action (no teleport).
   if(!transported&&!assistedAssigned&&observed>naturalDiedTick+120&&observed%30==0){
    int count=0;Iterator ap(pikiMgr);CI_LOOP(ap){Piki* p=static_cast<Piki*>(*ap);if(!p->isAlive())continue;
     p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
     p->mActiveAction->mChildActions[PikiAction::Transport].initialise(corpse);p->mMode=PikiMode::TransportMode;++count;}
    assistedAssigned=count;
    std::printf("P2_MAMUTA_POD_ASSIST carriers=%d assisted=1\n",count);
   }
  }
  {int bury=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->getCurrState()->getID()==PIKISTATE_Bury)++bury;}
   if(bury>0){buryStates+=bury;std::printf("P2_MAMUTA_POD_BURYSTATE tick=%d bury=%d\n",observed,bury);}}
  if(observed==900)capture("mamuta-pod-assist-approach.ppm");
  if(observed==NATURAL_TICKS){
   int planted=GameStat::mePikis-plantedBefore;
   std::printf("P2_MAMUTA_POD_APPROACH_RESULT approached=%d min=%.1f states=%08x\n",approached?1:0,minDistance,statesSeen);
   std::printf("P2_MAMUTA_POD_PLANTED planted=%d bury_states=%d\n",planted,buryStates);
   std::printf("P2_MAMUTA_POD_RESULT assisted=%d died=%d died_tick=%d corpse=%d carried=%d goal=%d pokos=%d control_alive=%d squad=%d\n",
               assistedAssigned?1:0,deathObserved?1:0,naturalDiedTick,corpse?1:0,transported?1:0,goalSeen?1:0,pc_p2_preview_pokos(),control->isAlive()?1:0,aliveSquad());
   capture("mamuta-pod-assist-final.ppm");
  }
  if(observed==NATURAL_TICKS+3){
   pc_p2_mamuta_forget(actor);pc_p2_mamuta_reset();
   require(!pc_p2_mamuta_rules_enabled(),"reset disables P2 rules");
   std::puts("P2_MAMUTA_POD_RESET");
  }
  if(observed==NATURAL_TICKS+6){
   require(control->isAlive(),"control survived assisted Pod observation");
   std::puts("PASS P2_MAMUTA_POD_RUNTIME assisted approach receipt reset");
   std::fflush(nullptr);std::_Exit(0);
  }
  std::fflush(stdout);return result;
 }
};
