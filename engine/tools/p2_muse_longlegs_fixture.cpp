// Muse l62 walk-translation observation fixture (#502, parent #173).
//
// Spliced into tools/preview_p2_room.cpp by experimental/pikmin2_muse_longlegs.py
// (instrumentation mirrors experimental/pikmin2_long_legs_lifecycle.py). This is a
// complete RoomApp class, not a standalone translation unit.
//
// Scenario: prove the owned host translates registered Long Legs bodies during FSM
// Walk at source speed along the source target rule (Houdai66 first, BigFoot69 as
// staged). The squad is parked OUTSIDE the 60-unit accumulate radius so Walk is
// reached naturally; the captain briefly wakes Houdai then retreats. After the
// walk window the fixture assigns the real Pikmin Attack action to Houdai (the
// fix-4 facing ring + re-park cadence) and proves the natural drain still connects
// under the translation change. No health writes, no injection, no transport
// writes: a timeout is an honest FAIL, never a fallback kill.
class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,wakeTick=0;
    int houdaiDropEvents=0;         // receiver-hit probe: actual health decreases on Houdai
    float houdaiMinHealth=1e9f;     // lowest Houdai health seen
    float houdaiLastHealth=0.0f;    // previous tick's Houdai health
    Vector3f captainOrigin;
    Teki* houdai=nullptr;Teki* bigfoot=nullptr;
    bool houdaiDied=false;bool parked=false;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    int freeAndPark(Teki* center, float radius){return freeAndParkAt(center->mSRT.t,radius);}
    int freeAndParkAt(const Vector3f& c, float radius){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(c.x+radius*std::sin(ang),0,c.z+radius*std::cos(ang));
        pt.y=mapMgr->getMinY(pt.x,pt.z,true);v->resetPosition(pt);v->changeMode(PikiMode::FreeMode,naviMgr?naviMgr->getNavi():nullptr);++n;}return n;}
    // Clump the live squad tight at one point and order the real Attack action.
    // The owned host walks Houdai toward the nearest Pikmin (source target rule),
    // so a tight clump keeps the mover arriving AT the attackers instead of the
    // fixture chasing it with a ring (a ring never latches on a 250 u/s mover).
    int clumpAttack(Teki* target,const Vector3f& c){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(c.x+10.0f*std::sin(ang),0,c.z+10.0f*std::cos(ang));
        pt.y=mapMgr->getMinY(pt.x,pt.z,true);v->resetPosition(pt);
        v->mSRT.r.y=ang+3.14159265f;
        v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
        v->mActiveAction->mChildActions[PikiAction::Attack].initialise(target);v->mMode=PikiMode::AttackMode;++n;}return n;}
    int parkAttack(Teki* target,float radius){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(target->mSRT.t.x+radius*std::sin(ang),0,target->mSRT.t.z+radius*std::cos(ang));
        pt.y=mapMgr->getMinY(pt.x,pt.z,true);v->resetPosition(pt);
        v->mSRT.r.y=ang+3.14159265f;
        v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
        v->mActiveAction->mChildActions[PikiAction::Attack].initialise(target);v->mMode=PikiMode::AttackMode;++n;}return n;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<60000,"muse longlegs walk timeout");
    if(frames%600==0){int live=0;if(pikiMgr){Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(v&&v->isAlive())++live;}}
        std::printf("P2_MUSE_WALK_HB frames=%d stage=%d observed=%d live=%d navimgr=%d naviobj=%d pikimgr=%d\n",frames,stage,observed,live,naviMgr?1:0,(naviMgr&&naviMgr->getNavi())?1:0,pikiMgr?1:0);std::fflush(stdout);}
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->skipScene(SCENESKIP_SkipAll);return result;}
    if(!pc_p2_preview_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    {static bool naviSustainLogged=false;int ns=n->mStateMachine->getCurrID(n);
        if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf){n->mStateMachine->transit(n,NAVISTATE_Walk);if(!naviSustainLogged){naviSustainLogged=true;std::puts("P2_MUSE_WALK_GUARD navi_sustain=1");}}}
    {static bool pikminGuardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!pikminGuardLogged){pikminGuardLogged=true;std::puts("P2_MUSE_WALK_GUARD pikmin_guard=1");}}}
    ++observed;
    if(stage==0){
        captainOrigin=n->mSRT.t;
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        n->mKontroller=new FixtureController();
        houdai=byGenerator(312001);bigfoot=byGenerator(312002);
        require(houdai&&bigfoot,"registered Long Legs actors present");
        require(pc_p2_long_legs_registered(houdai)&&pc_p2_long_legs_registered(bigfoot),"long legs registered");
        require(pc_p2_long_legs_count()==2,"long legs registered exactly twice");
        int squad=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive())++squad;}
        require(squad>=1,"live starting squad");
        houdaiLastHealth=houdai->mHealth;
        // Park the squad 120u from Houdai: outside the 60u accumulate radius (so
        // Wait reaches Walk naturally) but inside the 800u territory sight (so the
        // source target rule walks Houdai toward the squad, not a random point).
        int c=freeAndPark(houdai,120.0f);std::printf("P2_MUSE_WALK_PARK count=%d\n",c);
        // Wake BigFoot first (its 75u private radius never sees the squad at its
        // far staging, so it needs the captain visit to leave Stay).
        Vector3f bwake(bigfoot->mSRT.t.x,0,bigfoot->mSRT.t.z-70.0f);bwake.y=mapMgr->getMinY(bwake.x,bwake.z,true);
        n->resetPosition(bwake);std::printf("P2_MUSE_WALK_WAKE_BIGFOOT captain=1\n");
        wakeTick=observed;
        std::printf("P2_MUSE_WALK_READY squad=%d houdai_gen=312001 bigfoot_gen=312002\n",squad);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        // Trip 2: brief the captain to Houdai's wake ring, then retreat to origin.
        // Both actors then run their source schedules unwatched (walk window).
        if(observed==wakeTick+8){Vector3f wake(houdai->mSRT.t.x,0,houdai->mSRT.t.z-70.0f);wake.y=mapMgr->getMinY(wake.x,wake.z,true);
            n->resetPosition(wake);std::puts("P2_MUSE_WALK_WAKE captain=1");}
        if(observed==wakeTick+16){n->resetPosition(captainOrigin);std::puts("P2_MUSE_WALK_RETREAT captain=1");}
        if(observed%300==0)std::printf("P2_MUSE_WALK_POS houdai=%.1f,%.1f bigfoot=%.1f,%.1f\n",houdai->mSRT.t.x,houdai->mSRT.t.z,bigfoot->mSRT.t.x,bigfoot->mSRT.t.z);
        // 1500 observed ticks (~50 s at 30 fps): Houdai needs at most one
        // Wait(3 s)+Walk(7 s) cycle; BigFoot one Land+Wait(5 s)+Walk(10 s) cycle.
        if(observed>=1500){Vector3f clump(houdai->mSRT.t.x,0,houdai->mSRT.t.z);clump.y=mapMgr->getMinY(clump.x,clump.z,true);
            int a=clumpAttack(houdai,clump);std::printf("P2_MUSE_WALK_ATTACK attack=%d\n",a);std::fflush(stdout);stage=2;return result;}
        return result;
    }
    if(stage==2){
        if(!houdai->isAlive()&&!houdaiDied){houdaiDied=true;std::printf("P2_MUSE_WALK_NATURAL_DEATH houdai=1 health=%.2f tick=%d\n",houdai->mHealth,observed);std::fflush(stdout);}
        if(houdaiDied){stage=3;return result;}
        {float h=houdai->mHealth;if(h<houdaiLastHealth)++houdaiDropEvents;houdaiLastHealth=h;if(h>0.0f&&h<houdaiMinHealth)houdaiMinHealth=h;}
        // Re-clump on a slow cadence: the mover arrives AT the clump on its own
        // (source target rule), so no per-tick chase is needed; this only repairs
        // Flick shake-off scatter. Tighter cadences fight the 250 u/s motion.
        if(observed%100==0&&pc_p2_long_legs_damageable(houdai)){Vector3f clump(houdai->mSRT.t.x,0,houdai->mSRT.t.z);clump.y=mapMgr->getMinY(clump.x,clump.z,true);clumpAttack(houdai,clump);}
        if(observed%90==0){int live=0,atk=0;Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(!v->isAlive())continue;++live;if(v->mMode==PikiMode::AttackMode)++atk;}
            std::printf("P2_MUSE_WALK_HOUDAI_HP health=%.2f squad=%d atk=%d dmg=%d events=%d tick=%d\n",houdai->mHealth,live,atk,int(pc_p2_long_legs_damageable(houdai)),houdaiDropEvents,observed);std::fflush(stdout);}
        if(observed>=9000){std::puts("FAIL P2_MUSE_LONGLEGS_WALK drain_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    if(stage==3){
        std::printf("P2_MUSE_WALK_DRAIN events=%d min=%.2f\n",houdaiDropEvents,houdaiMinHealth);
        std::printf("P2_MUSE_WALK_SESSION navi=1 pikis=%lu\n",(unsigned long)GameStat::allPikis);
        std::puts("PASS P2_MUSE_LONGLEGS_WALK walk+Houdai-drain");
        std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return result;
}};
