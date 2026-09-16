// Muse Armor15 natural death/transport/re-entry observer fixture (#165).
//
// Spliced into tools/preview_p2_room.cpp by experimental/pikmin2_muse_armor.py.
// This is a complete RoomApp class, not a standalone translation unit.
//
// Scenario: the bound Armor actor (TEKI_Chappy vehicle, generator 346001) is
// killed by REAL squad Attack orders (no mHealth write anywhere in this file).
// The fixture only observes: per-tick health decreases (read-only probe), the
// engine corpse Pellet, the ordinary FreeMode graspSituation carry, the
// generic Pod receipt, then a stage-boundary reset + real generator rebirth
// with re-bind and stale/fresh pointer proof. Sokkuri (346005) shares the
// lane-14 arena config and is parked far away, never touched.
class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0;
    int armorDropEvents=0;
    float armorMinHealth=1e9f;
    float armorLastHealth=0.0f;
    float armorStartHealth=0.0f;
    Vector3f captainOrigin;
    Teki* armor=nullptr;Teki* sokkuri=nullptr;
    Generator* armorGen=nullptr;
    Teki* freshArmor=nullptr;
    Pellet* armorCorpse=nullptr;
    bool armorDied=false;bool carried=false;bool delivered=false;bool reentered=false;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    int transportingCount(){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(v->isAlive()&&v->mMode==PikiMode::TransportMode)++n;}return n;}
    int freeAndParkAt(const Vector3f& c,float radius){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(c.x+radius*std::sin(ang),0,c.z+radius*std::cos(ang));
        pt.y=mapMgr->getMinY(pt.x,pt.z,true);v->resetPosition(pt);v->changeMode(PikiMode::FreeMode,naviMgr?naviMgr->getNavi():nullptr);++n;}return n;}
    int clumpAttack(Teki* target,const Vector3f& c){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(c.x+10.0f*std::sin(ang),0,c.z+10.0f*std::cos(ang));
        pt.y=mapMgr->getMinY(pt.x,pt.z,true);v->resetPosition(pt);
        v->mSRT.r.y=ang+3.14159265f;
        v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
        v->mActiveAction->mChildActions[PikiAction::Attack].initialise(target);v->mMode=PikiMode::AttackMode;++n;}return n;}
    int dropStrayPellets(){int n=0;Iterator i(pelletMgr);CI_LOOP(i){Pellet* p=static_cast<Pellet*>(*i);
        if(!p||!p->isAlive()||p->mPelletView||!p->mConfig)continue;
        if(p->mConfig->mModelId.mId=='pr01'){p->mIsAlive=false;++n;}}return n;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<90000,"muse armor timeout");
    if(frames%600==0){int live=0;if(pikiMgr){Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(v&&v->isAlive())++live;}}
        std::printf("P2_MUSE_ARMOR_HB frames=%d stage=%d observed=%d live=%d navimgr=%d naviobj=%d pikimgr=%d\n",frames,stage,observed,live,naviMgr?1:0,(naviMgr&&naviMgr->getNavi())?1:0,pikiMgr?1:0);std::fflush(stdout);}
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->skipScene(SCENESKIP_SkipAll);return result;}
    if(!pc_p2_preview_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    {static bool naviSustainLogged=false;int ns=n->mStateMachine->getCurrID(n);
        if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf){n->mStateMachine->transit(n,NAVISTATE_Walk);if(!naviSustainLogged){naviSustainLogged=true;std::puts("P2_MUSE_ARMOR_GUARD navi_sustain=1");}}}
    {static bool pikminGuardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!pikminGuardLogged){pikminGuardLogged=true;std::puts("P2_MUSE_ARMOR_GUARD pikmin_guard=1");}}}
    ++observed;
    if(stage==0){
        captainOrigin=n->mSRT.t;
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        n->mKontroller=new FixtureController();
        armor=byGenerator(346001);sokkuri=byGenerator(346005);
        require(armor,"bound Armor actor present");
        require(pc_p2_armor_registered(armor),"Armor registered");
        require(pc_p2_armor_count()==1,"Armor registered exactly once");
        require(!sokkuri||pc_p2_sokkuri_registered(sokkuri),"Sokkuri bystander registered if present");
        require(pc_p2_preview_goal()!=nullptr,"Pod anchor present");
        int squad=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive())++squad;}
        require(squad>=1,"live starting squad");
        armorGen=armor->mGenerator;
        require(armorGen&&armorGen->mGenType&&armorGen->mGenObject,"Armor generator present");
        armorLastHealth=armor->mHealth;armorStartHealth=armor->mHealth;
        require(armorStartHealth>0.0f,"Armor starts healthy");
        // Damage-window staging only. This host has no EB_Bittered lifecycle and
        // the arena Armor loads no collision weakpoint (mode=reject_all), so the
        // source receiver rejects every hit; pc_p2_armor_set_bittered is the
        // module's documented host input for the bittered leg. No health is
        // written: the drain below is real InteractAttack damage.
        pc_p2_armor_set_bittered(armor,true);
        std::printf("P2_MUSE_ARMOR_WINDOW bittered=1 source=armor_module_input\n");
        std::printf("P2_MUSE_ARMOR_READY squad=%d armor_gen=346001 health=%.2f\n",squad,armor->mHealth);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        if(armor->mHealth<armorLastHealth){++armorDropEvents;}
        if(armor->mHealth>0.0f&&armor->mHealth<armorMinHealth)armorMinHealth=armor->mHealth;
        armorLastHealth=armor->mHealth;
        if(observed%15==0&&!armorDied){Vector3f clump(armor->mSRT.t.x,0,armor->mSRT.t.z);clump.y=mapMgr->getMinY(clump.x,clump.z,true);clumpAttack(armor,clump);}
        if(observed%90==0){int live=0,atk=0;Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(!v->isAlive())continue;++live;if(v->mMode==PikiMode::AttackMode)++atk;}
            std::printf("P2_MUSE_ARMOR_HP health=%.2f squad=%d atk=%d events=%d tick=%d\n",armor->mHealth,live,atk,armorDropEvents,observed);std::fflush(stdout);}
        if(!armor->isAlive()||armor->mHealth<=0.0f){
            armorDied=true;
            std::printf("P2_MUSE_ARMOR_DRAIN events=%d min=%.2f start=%.2f\n",armorDropEvents,armorMinHealth,armorStartHealth);
            std::printf("P2_MUSE_ARMOR_NATURAL_DEATH armor=1 health=0.00 tick=%d\n",observed);
            std::fflush(stdout);stage=2;return result;
        }
        if(observed>=6000){std::puts("FAIL P2_MUSE_ARMOR drain_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    if(stage==2){
        if(!armorCorpse){armorCorpse=corpseOf(armor);if(armorCorpse){std::printf("P2_MUSE_ARMOR_CORPSE pellet=1 generator=346001\n");std::fflush(stdout);}}
        if(!armorCorpse){if(observed>9000){std::puts("FAIL P2_MUSE_ARMOR corpse_timeout");std::fflush(stdout);std::_Exit(1);}return result;}
        int stray=dropStrayPellets();
        int c=freeAndParkAt(armorCorpse->mSRT.t,22.0f);
        std::printf("P2_MUSE_ARMOR_FREE count=%d stray=%d pokos=%d\n",c,stray,pc_p2_preview_pokos());
        std::fflush(stdout);stage=3;return result;
    }
    if(stage==3){
        if(observed%120==0){int t=transportingCount();
            std::printf("P2_MUSE_ARMOR_CARRY state=%d alive=%d transport=%d pokos=%d\n",armorCorpse->getState(),int(armorCorpse->isAlive()),t,pc_p2_preview_pokos());std::fflush(stdout);
            if(t>0)carried=true;}
        if(!armorCorpse->isAlive()){
            delivered=true;
            std::printf("P2_MUSE_ARMOR_DELIVER pokos=%d\n",pc_p2_preview_pokos());
            std::fflush(stdout);stage=4;return result;
        }
        if(observed>20000){std::puts("FAIL P2_MUSE_ARMOR carry_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    if(stage==4){
        pc_p2_armor_forget(armor);
        require(pc_p2_armor_count()==0,"Armor registry not cleared by forget");
        std::printf("P2_MUSE_ARMOR_FORGET count=0 registered=0\n");
        pc_p2_armor_reset();
        armorGen->mGenType->init(armorGen);
        freshArmor=static_cast<Teki*>(armorGen->mLatestSpawnCreature);
        require(freshArmor,"native generator rebirth failed");
        require(freshArmor!=armor,"allocator reused the same address; stale proof inconclusive");
        pc_p2_armor_setup();
        require(pc_p2_armor_registered(freshArmor),"fresh Armor not bound");
        require(!pc_p2_armor_registered(armor),"stale Armor pointer still registered");
        require(pc_p2_armor_count()==1,"Armor registry count after re-entry");
        require(!corpseOf(freshArmor),"fresh Armor inherited a corpse");
        std::printf("P2_MUSE_ARMOR_REENTRY old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)armor,(void*)freshArmor,pc_p2_armor_count());
        std::fflush(stdout);reentered=true;stage=5;return result;
    }
    if(stage==5){
        std::printf("P2_MUSE_ARMOR_SESSION navi=1 pikis=%lu\n",(unsigned long)GameStat::allPikis);
        std::puts("PASS P2_MUSE_ARMOR death=Armor corpse=1 receipt=1 reentry=1 injected=0");
        std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return result;
}};
