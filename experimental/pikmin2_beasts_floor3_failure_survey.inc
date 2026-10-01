// External fixture only. Terminal conditions are synthetic; production tick publishes/exits.
static void floorThreeFailureSurvey(Navi* n){
    static int updates=0,repairs=-1;
    ++updates;require(updates<300,"terminal native tick did not exit42");
    if(updates!=90)return;
    std::ifstream marker("p2-floor3-failure-fixture.txt");std::string version,reason,extra;
    require(bool(marker>>version>>reason) && !(marker>>extra) && marker.eof(),"invalid terminal fixture marker");
    require(version=="P2_FLOOR3_FAILURE_FIXTURE_1" && (reason=="extinction" || reason=="knockout"),"invalid terminal reason");
    std::ifstream expectedFile("p2-floor3-boundary.txt");std::string expected;require(bool(expectedFile>>expected),"missing terminal token");
    require(pc_p2_cave_floor()==3 && pc_p2_cave_is_beasts() && pc_p2_cave_boundary_token()==expected,"terminal profile/token mismatch");
    require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"active floor3 party descended");
    require(!pc_p2_cave_interact(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z),"active floor3 interaction descended");
    pc_p2_cave_request();
    require(pc_p2_preview_pokos()==0 && !pc_p2_preview_treasure(),"unexpected terminal reward/cargo");
    repairs=playerState->getCurrParts();
    std::printf("P2_FLOOR3_FAILURE_ARMED token=%s reason=%s active_descent_rejected=1\n",expected.c_str(),reason.c_str());
    beastsPartySnapshot(n);
    if(reason=="knockout")n->mHealth=0;
    else{
        std::vector<Piki*> living;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())living.push_back(p);}
        require(living.size()==20,"terminal fixture survivor count");
        Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads)require(!static_cast<PikiHeadItem*>(*heads)->isAlive(),"extinction fixture has sprouts");
        for(Piki* p:living)p->kill(false);
    }
    gameflow.mPauseAll=true;require(!pc_p2_cave_checkpoint(false),"paused terminal checkpoint accepted");gameflow.mPauseAll=false;
    require(playerState->getCurrParts()==repairs && pc_p2_preview_pokos()==0,"terminal injection changed rewards");
    std::printf("P2_FLOOR3_FAILURE_INJECTED reason=%s repairs_unchanged=1 pokos=0\n",reason.c_str());std::fflush(stdout);
}
