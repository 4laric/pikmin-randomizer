// Generated external fixture only; no production inputs or movement mutation.
static void floorThreeSurvey(Navi* n) {
    static int updates=0,point=0,repairs=-1;
    static float health=0;
    static const float goals[12][2]={{-85,-280},{-85,-390},{-85,-470},{-85,-580},{-85,-735},{-85,-1000},
        {-85,-735},{-85,-580},{-85,-470},{-85,-390},{-85,-280},{-85,-120}};
    ++updates;
    require(updates<4000,"floor3 survey timeout");
    if(updates<90)return;
    require(pc_p2_purples_enabled() && pc_p2_preview_goal(),"floor3 Purple/Pod support missing");
    require(pc_p2_preview_pokos()==0 && !pc_p2_preview_treasure(),"floor3 unexpected cargo or reward");
    if(updates==90){
        if(FILE* entry=std::fopen("p2-floor3-boundary.txt","r")){
            char expected[65],extra;
            require(std::fscanf(entry,"%64s",expected)==1 && std::fscanf(entry," %c",&extra)==EOF,"invalid floor3 expected token");std::fclose(entry);
            require(pc_p2_cave_floor()==3 && pc_p2_cave_is_beasts(),"native floor3 profile missing");
            require(pc_p2_cave_boundary_token()==expected,"native floor3 boundary differs");
            require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor4 transfer unexpectedly enabled");
            require(!pc_p2_cave_interact(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z),"floor4 interaction enabled");
            pc_p2_cave_request();
            std::printf("P2_FLOOR3_BOUNDARY_VERIFIED token=%s descent=disabled\n",expected);
        }else require(pc_p2_cave_floor()==2 && !pc_p2_cave_is_beasts(),"legacy party restore profile changed");
        repairs=playerState->getCurrParts();health=n->mHealth;
        n->mKontroller=new FixtureController();
        for(int id:{7,16,17,18,24,25,34,36,38,39,42,45,53,58,59,60,61,65,82,83,84,85,86,87,88,89,90,91,92,93})playerState->mDemoFlags.setFlagOnly(id);
        std::puts("P2_FLOOR3_SURVEY_READY");
    }
    require(playerState->getCurrParts()==repairs && std::fabs(n->mHealth-health)<0.001f,"floor3 repairs or health changed");
    const float ground=mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true);
    require(std::isfinite(ground) && std::fabs(n->mSRT.t.y-ground)<5,"floor3 captain lost grounded walk");
    combatDestination=Vector3f(goals[point][0],0,goals[point][1]);
    const float dx=n->mSRT.t.x-goals[point][0],dz=n->mSRT.t.z-goals[point][1];
    combatWalking=dx*dx+dz*dz>=15*15;
    if(!combatWalking){
        std::printf("P2_FLOOR3_POINT index=%d x=%.3f y=%.3f z=%.3f ground=%.3f\n",point,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,ground);
        ++point;
        if(point==12){
            FILE* transfer=std::fopen("p2-cave-transfer.txt","r");require(!transfer,"unexpected floor4 transfer file");
            beastsPartySnapshot(n);capture("floor3-survey.ppm");
            std::puts("PASS P2_FLOOR3_SURVEY goals=12 cargo=0 pokos=0 repairs_unchanged=1");std::fflush(stdout);std::_Exit(0);
        }
    }
    std::fflush(stdout);
}
