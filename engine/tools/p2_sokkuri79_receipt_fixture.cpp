// Sokkuri79 exactly-once ordinary Onion receipt fixture (#578, parent #569).
//
// Spliced into tools/preview_p2_room.cpp by
// experimental/pikmin2_sokkuri79_receipt.py; complete RoomApp class, not a
// standalone translation unit. Follow-on of #495 (haul proven, receipt
// missing): the arena is Pod-enabled (NOT cargo-free) and the process boots
// with --randomizer-seed so the real ordinary endpoint credits onion:p2:79.
//
// Scenario: natural FreeMode combat drains a bound Sokkuri79 to a
// combat-culminated death; free Pikmin grasp the corpse and haul it to the
// room Pod anchor (Red container); GoalItem::suckMe fires the bound-source
// receipt through pc_randomizer_p2_corpse_delivered. No health/state writes,
// no Transport assignment, no direct suckMe call, no forget/re-entry (the
// bind must survive until the single-use delivery consumes it; re-bind is
// not scene re-entry and gate 6 stays UNTESTED). A stall is an honest FAIL,
// never a fallback credit.
class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,deadTick=0,goalTick=0;
    float minHealth=9999.0f;
    Teki* sokkuri=nullptr;
    Pellet* corpse=nullptr;
    Vector3f deathPos;bool haveDeathPos=false;
    Vector3f podPos;bool havePodPos=false;
    bool sawGoal=false;float maxMoved=0.0f;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    int aliveReds(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
    bool deadClip(){const char* nm=nullptr;float ph=0;return pc_p2_sokkuri_clip(sokkuri,nm,ph)&&nm&&std::strcmp(nm,"dead1")==0;}
    void snapPod(){if(havePodPos||!itemMgr)return;for(int c=0;c<3;++c){GoalItem* goal=itemMgr->getContainer(c);if(goal){podPos=goal->mSRT.t;havePodPos=true;std::printf("P2_SOKKURI79_POD container=%d x=%.2f z=%.2f\n",c,podPos.x,podPos.z);std::fflush(stdout);return;}}}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<60000,"sokkuri79 receipt startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    if(!pc_randomizer_ready()){if(observed%300==0){std::printf("P2_SOKKURI79_SESSION_WAIT observed=%d\n",observed);std::fflush(stdout);}return result;}
    ++observed;
    if(stage==0){
        sokkuri=byGenerator(346005);
        require(sokkuri&&pc_p2_sokkuri_registered(sokkuri)&&pc_p2_sokkuri_count()==1,"sokkuri registered exactly once");
        require(aliveReds()>=1,"live red starting squad");
        snapPod();
        std::printf("P2_SOKKURI79_READY squad=%d sokkuri_gen=346005 reg=1 session=1\n",aliveReds());
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        // FreeMode deploy around the Sokkuri; real InteractAttack drains health.
        // No health is written; no AI action beyond FreeMode is assigned.
        Iterator it(pikiMgr);int count=0;CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||p->mColor!=Red)continue;float angle=float(count)*6.2831853f/20.f;Vector3f point=sokkuri->getPosition()+Vector3f(16.f*std::sin(angle),0.f,16.f*std::cos(angle));point.y=mapMgr->getMinY(point.x,point.z,true);p->resetPosition(point);p->changeMode(PikiMode::FreeMode,n);++count;}
        require(count==20,"deployed all 20 red Pikmin");
        Vector3f cap=sokkuri->getPosition()+Vector3f(40.f,0.f,0.f);cap.y=mapMgr->getMinY(cap.x,cap.z,true);n->resetPosition(cap);
        std::printf("P2_SOKKURI79_DEPLOY free_squad=%d x=%.2f z=%.2f\n",count,sokkuri->getPosition().x,sokkuri->getPosition().z);
        std::fflush(stdout);stage=2;return result;
    }
    if(stage==2){
        if(sokkuri->mHealth>0.0f && sokkuri->mHealth<minHealth)minHealth=sokkuri->mHealth;
        if(deadClip()){deadTick=observed;deathPos=sokkuri->getPosition();haveDeathPos=true;std::printf("P2_SOKKURI79_DIED tick=%d health=%.2f\n",observed,sokkuri->mHealth);std::fflush(stdout);stage=3;return result;}
        if(observed%60==0){std::printf("P2_SOKKURI79_OBSERVE tick=%d health=%.2f state=%d squad=%d\n",observed,sokkuri->mHealth,sokkuri->mStateID,aliveReds());std::fflush(stdout);}
        require(observed<5400,"natural death timeout (health stalled)");
        return result;
    }
    if(stage==3){
        if(!corpse)corpse=corpseOf(sokkuri);
        if(corpse){std::printf("P2_SOKKURI79_CORPSE pellet=1 tick=%d\n",observed);std::fflush(stdout);stage=4;return result;}
        require(observed<5760,"corpse handoff timeout");
        return result;
    }
    if(stage==4){
        // Natural haul only: carriers grasp and route on their own. The bind
        // is deliberately NOT forgotten here (gate 6 stays UNTESTED).
        if(corpse&&corpse->getState()==PELSTATE_Goal)sawGoal=true;
        if(!corpse||!corpse->isAlive()){
            require(sawGoal&&maxMoved>100.0f,"corpse vanished without traversing room and entering Pod goal");
            goalTick=observed;
            std::printf("P2_SOKKURI79_DELIVERED_TO_GOAL tick=%d moved=%.2f\n",observed,maxMoved);
            std::fflush(stdout);stage=5;return result;
        }
        if(observed%60==0&&haveDeathPos){
            float dx=corpse->mSRT.t.x-deathPos.x,dz=corpse->mSRT.t.z-deathPos.z;
            float moved=std::sqrt(dx*dx+dz*dz);
            float goalDx=havePodPos?(corpse->mSRT.t.x-podPos.x):0.f,goalDz=havePodPos?(corpse->mSRT.t.z-podPos.z):0.f;
            float goalDist=havePodPos?std::sqrt(goalDx*goalDx+goalDz*goalDz):-1.f;
            if(moved>maxMoved)maxMoved=moved;
            std::printf("P2_SOKKURI79_CARRY tick=%d moved=%.2f goal_dist=%.2f state=%d\n",observed,moved,goalDist,corpse->getState());
            std::fflush(stdout);
        }
        require(observed<14000,"haul stalled before Pod goal (route gap, no fallback credit)");
        return result;
    }
    if(stage==5){
        // Receipt flush window: suckMe already fired on goal entry; the ledger
        // write lands in the session campaign dir. Python validates new=1/0.
        if(observed-goalTick>600){std::puts("PASS P2_SOKKURI79_RECEIPT_RUN delivered=1");std::fflush(stdout);std::_Exit(0);}
        return result;
    }
    std::fflush(stdout);return result;
}
};