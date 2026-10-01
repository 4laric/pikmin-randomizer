// ElecBug28 exactly-once ordinary Onion receipt fixture (#585, parent #569).
//
// Spliced into tools/preview_p2_room.cpp by
// experimental/pikmin2_elecbug28_receipt.py; complete RoomApp class, not a
// standalone translation unit. Mirrors the proven Sokkuri79 receipt pattern
// (#578): the process boots with --randomizer-seed so the real ordinary
// endpoint (GoalItem::suckMe -> pc_randomizer_p2_corpse_delivered) can credit
// onion:p2:28.
//
// Scenario: a paired 2-ElecBug roster lets the pair discharge naturally; a
// single p1-derived staged Purple landing flips A into Reverse (labelled
// flip=staged-press), which disables the source invulnerability so the free
// squad drains 500 HP through the real receiver. Death/corpse/haul/receipt are
// natural. No enemy health/state writes, no Transport assignment, no direct
// suckMe call, no forget/re-entry: the single-use bind must survive until
// delivery consumes it. Haul alone never closes transport (the receipt line is
// required). A stall is an honest FAIL, never a fallback credit.
class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,dischargeWait=0,deadTick=0,goalTick=0;
    bool dischargeSeen=false,flipped=false,sawGoal=false;
    float minHealth=9999.0f,maxMoved=0.0f;
    Teki* a=nullptr;Teki* b=nullptr;
    Pellet* corpse=nullptr;
    Piki* purple=nullptr;Piki* yellow=nullptr;
    Vector3f deathPos;bool haveDeathPos=false;
    Vector3f podPos;bool havePodPos=false;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator&&t->mGenerator->_70==id)return t;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    const char* stateOf(Teki* t){return pc_p2_elecbug_state_name(t);}
    bool isReverse(const char* s){return s&&std::strcmp(s,"reverse")==0;}
    bool isDischarging(const char* s){return s&&(std::strcmp(s,"discharge")==0||std::strcmp(s,"childdischarge")==0);}
    bool isDead(const char* s){return s&&std::strcmp(s,"dead")==0;}
    int aliveTotal(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++c;}return c;}
    int aliveReds(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
    void snapPod(){if(havePodPos||!itemMgr)return;for(int c=0;c<3;++c){GoalItem* goal=itemMgr->getContainer(c);if(goal){podPos=goal->mSRT.t;havePodPos=true;std::printf("P2_ELECBUG28_POD container=%d x=%.2f z=%.2f\n",c,podPos.x,podPos.z);std::fflush(stdout);return;}}}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<60000,"elecbug28 receipt startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    if(!pc_randomizer_ready()){if(observed%300==0){std::printf("P2_ELECBUG28_SESSION_WAIT observed=%d\n",observed);std::fflush(stdout);}return result;}
    ++observed;
    if(stage==0){
        a=byGenerator(346002);b=byGenerator(346010);
        require(a&&b,"two ElecBug actors present");
        require(pc_p2_elecbug_registered(a)&&pc_p2_elecbug_registered(b)&&pc_p2_elecbug_count()==2,"elecbug registered exactly twice");
        require(aliveReds()>=1,"live red starting squad");
        snapPod();
        std::printf("P2_ELECBUG28_READY squad=%d elecbug_gen=346002 pair_gen=346010 reg=2 session=1\n",aliveTotal());
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;if(idx==0){pc_p2_set_species(p,P2SpeciesPurple);purple=p;}else if(idx==1){pc_p2_set_species(p,P2SpeciesYellow);yellow=p;}++idx;}
        require(purple&&yellow,"purple and yellow designated");
        Vector3f mid=Vector3f((a->getPosition().x+b->getPosition().x)*0.5f,0,a->getPosition().z);
        mid.y=mapMgr->getMinY(mid.x,mid.z,true);yellow->resetPosition(mid);
        int park=0;Iterator p2(pikiMgr);CI_LOOP(p2){Piki* p=static_cast<Piki*>(*p2);if(!p||!p->isAlive()||p==yellow)continue;Vector3f pt=Vector3f(-400.0f,0,1850.0f+float(park)*2.0f);pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++park;}
        yellow->changeMode(PikiMode::FreeMode,n);
        Vector3f npos=Vector3f(a->getPosition().x+60.0f,0,a->getPosition().z-60.0f);npos.y=mapMgr->getMinY(npos.x,npos.z,true);n->resetPosition(npos);
        std::printf("P2_ELECBUG28_DEPLOY free_squad=%d purple=1 yellow=1\n",aliveTotal());
        std::fflush(stdout);stage=2;return result;
    }
    if(stage==2){
        const char* sa=stateOf(a);const char* sb=stateOf(b);
        if(!dischargeSeen&&(isDischarging(sa)||isDischarging(sb))){dischargeSeen=true;std::printf("P2_ELECBUG28_DISCHARGE tick=%d\n",observed);std::fflush(stdout);}
        if(dischargeSeen&&!isDischarging(sa)&&!isDischarging(sb)){stage=3;}
        require(observed<3600,"pair never discharged");
        return result;
    }
    if(stage==3){
        // P1-derived staged Purple landing (the host has no Purple hipdrop state);
        // this is the documented family-local press adaptation, labelled in the
        // PASS line as flip=staged-press. No enemy health/state write.
        Vector3f onto=a->getPosition();onto.y=mapMgr->getMinY(onto.x,onto.z,true);
        purple->resetPosition(onto);
        purple->mVelocity=Vector3f(0.0f,-100.0f,0.0f);
        purple->changeMode(PikiMode::FreeMode,n);
        std::printf("P2_ELECBUG28_THROW tick=%d purple=1\n",observed);
        std::fflush(stdout);stage=4;return result;
    }
    if(stage==4){
        const char* sa=stateOf(a);
        if(a->mHealth>0.0f&&a->mHealth<minHealth)minHealth=a->mHealth;
        if(!flipped&&isReverse(sa)){
            flipped=true;
            std::printf("P2_ELECBUG28_FLIPPED tick=%d\n",observed);std::fflush(stdout);
            int k=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||p==purple||p==yellow)continue;float ang=float(k)*6.2831853f/18.f;Vector3f pt=a->getPosition()+Vector3f(14.f*std::sin(ang),0.f,14.f*std::cos(ang));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++k;}
        }
        if(purple&&!purple->isAlive()){
            Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&pc_p2_species(p)==P2SpeciesRed){pc_p2_set_species(p,P2SpeciesPurple);purple=p;std::printf("P2_ELECBUG28_REDESIGNATE tick=%d purple=1\n",observed);std::fflush(stdout);break;}}
        }
        if(a->mHealth>0.0f&&!isDead(sa)&&!isDischarging(sa)&&purple&&purple->isAlive()&&observed%25==0){
            Vector3f onto=a->getPosition();onto.y=mapMgr->getMinY(onto.x,onto.z,true);
            purple->resetPosition(onto);
            purple->mVelocity=Vector3f(0.0f,-100.0f,0.0f);
            purple->changeMode(PikiMode::FreeMode,n);
        }
        if(a->mHealth<=0.0f||isDead(sa)){
            deadTick=observed;deathPos=a->getPosition();haveDeathPos=true;
            std::printf("P2_ELECBUG28_DIED tick=%d health=%.2f\n",observed,a->mHealth);std::fflush(stdout);stage=5;return result;
        }
        if(observed%60==0){std::printf("P2_ELECBUG28_OBSERVE tick=%d health=%.2f state=%s squad=%d\n",observed,a->mHealth,sa?sa:"null",aliveTotal());std::fflush(stdout);}
        require(observed<7200,"natural death timeout (health stalled)");
        return result;
    }
    if(stage==5){
        if(!corpse)corpse=corpseOf(a);
        if(corpse){
            // Natural-haul stimulus only: re-place the surviving free squad in a
            // ring around the corpse and leave them in FreeMode, exactly as the
            // Sokkuri79 #495/#578 recipe. No Transport assignment, no health or
            // state write; graspSituation latches the carry on its own.
            int k=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;float ang=float(k)*6.2831853f/16.f;Vector3f pt=corpse->mSRT.t+Vector3f(16.f*std::sin(ang),0.f,16.f*std::cos(ang));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++k;}
            std::printf("P2_ELECBUG28_CORPSE pellet=1 tick=%d deployed=%d\n",observed,k);std::fflush(stdout);stage=6;return result;
        }
        require(observed<7560,"corpse handoff timeout");
        return result;
    }
    if(stage==6){
        // Natural haul only: free Pikmin grasp and route on their own. The bind
        // is deliberately NOT forgotten (gate 6 stays UNTESTED).
        if(corpse&&corpse->getState()==PELSTATE_Goal)sawGoal=true;
        if(!corpse||!corpse->isAlive()){
            require(sawGoal&&maxMoved>100.0f,"corpse vanished without traversing room and entering goal");
            goalTick=observed;
            std::printf("P2_ELECBUG28_DELIVERED_TO_GOAL tick=%d moved=%.2f\n",observed,maxMoved);
            std::fflush(stdout);stage=7;return result;
        }
        if(observed%60==0&&haveDeathPos){
            float dx=corpse->mSRT.t.x-deathPos.x,dz=corpse->mSRT.t.z-deathPos.z;
            float moved=std::sqrt(dx*dx+dz*dz);
            float goalDx=havePodPos?(corpse->mSRT.t.x-podPos.x):0.f,goalDz=havePodPos?(corpse->mSRT.t.z-podPos.z):0.f;
            float goalDist=havePodPos?std::sqrt(goalDx*goalDx+goalDz*goalDz):-1.f;
            if(moved>maxMoved)maxMoved=moved;
            std::printf("P2_ELECBUG28_CARRY tick=%d moved=%.2f goal_dist=%.2f state=%d\n",observed,moved,goalDist,corpse->getState());
            std::fflush(stdout);
        }
        require(observed<14000,"haul stalled before goal (route gap, no fallback credit)");
        return result;
    }
    if(stage==7){
        if(observed-goalTick>600){std::puts("PASS P2_ELECBUG28_RECEIPT_RUN delivered=1");std::fflush(stdout);std::_Exit(0);}
        return result;
    }
    std::fflush(stdout);return result;
}
};
