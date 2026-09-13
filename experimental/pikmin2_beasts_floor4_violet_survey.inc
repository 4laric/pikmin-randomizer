// External fixture: native movement, throws, Pom conversion and pluck paths.
// Action selection is scripted; this does not implement the source P2 Pom FSM.
static void floorFourViolet(Navi* n) {
    static int updates=0,state=0,timer=0,point=0,thrown=0,repairs=0;
    static float health=0;
    static Pom* flower=nullptr;
    static std::vector<Piki*> originals;
    static bool captainPluck=false,captainPassed=false;
    static const float approach[9][2]={{0,-550},{0,-640},{0,-720},{0,-830},{10,-950},{25,-1080},{170,-1190},{315,-1080},{295,-935}};
    ++updates;++timer;require(updates<6000,"floor4 Violet survey timeout");
    if(updates<90)return;
    n->mNeutralTime=0;
    require(pc_p2_purples_enabled() && pc_p2_preview_goal(),"floor4 Violet Purple/Pod missing");
    require(pc_p2_preview_pokos()==0 && !pc_p2_preview_treasure(),"floor4 Violet unexpected reward");
    int reds=0,purples=0,sprouts=0;
    Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(!p->isAlive())continue;
        if(pc_p2_is_purple(p))++purples;else{require(p->mColor==Red,"floor4 wrong species");++reds;}}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);
        if(h->isAlive()){require(h->mP2Purple,"floor4 wrong sprout");++sprouts;}}
    if(state==0){
        require(reds==20 && purples==0 && sprouts==0,"floor4 initial party differs");
        FILE* entry=std::fopen("p2-floor4-boundary.txt","r");require(entry,"floor4 token missing");
        char token[65],extra;require(std::fscanf(entry,"%64s",token)==1 && std::fscanf(entry," %c",&extra)==EOF,"floor4 token malformed");std::fclose(entry);
        require(pc_p2_cave_floor()==4 && pc_p2_cave_is_beasts() && pc_p2_cave_boundary_token()==token,"floor4 native profile differs");
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor4 completion enabled");
        int count=0;Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);if(!b->isAlive())continue;
            require(b->mObjType==OBJTYPE_Pom && b->mGenerator && b->mGenerator->_70==62002,"floor4 unexpected actor");
            flower=static_cast<Pom*>(b);require(pc_p2_violet(flower),"floor4 flower missing Violet metadata");++count;}
        require(count==1,"floor4 expected one flower");
        Iterator enemies(tekiMgr);CI_LOOP(enemies)require(!static_cast<Teki*>(*enemies)->isAlive(),"floor4 unexpected enemy");
        Iterator pellets(pelletMgr);CI_LOOP(pellets)require(!static_cast<Pellet*>(*pellets)->isAlive(),"floor4 hidden cargo");
        const Vector3f& pos=*flower->getInitPosition();
        std::printf("P2_FLOOR4_VIOLET_FLOWER generator=62002 x=%.3f y=%.3f z=%.3f live_x=%.3f live_y=%.3f live_z=%.3f ground=%.3f\n",pos.x,pos.y,pos.z,flower->mSRT.t.x,flower->mSRT.t.y,flower->mSRT.t.z,mapMgr->getMinY(pos.x,pos.z,true));
        Iterator initial(pikiMgr);CI_LOOP(initial){Piki* p=static_cast<Piki*>(*initial);if(p->isAlive())originals.push_back(p);}
        repairs=playerState->getCurrParts();health=n->mHealth;n->mKontroller=new FixtureController();
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        std::printf("P2_FLOOR4_VIOLET_BOUNDARY token=%s descent=disabled\n",token);
        std::puts("P2_BEASTS_READY reds=20 flowers=1 cargo=0");state=1;timer=0;
    }
    require(playerState->getCurrParts()==repairs && std::fabs(n->mHealth-health)<0.001f,"floor4 health or repairs changed");
    if(state==1){
        float ground=mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true);
        if(!std::isfinite(ground) || std::fabs(n->mSRT.t.y-ground)>=5)std::printf("P2_FLOOR4_VIOLET_GROUND_FAILURE x=%.3f y=%.3f z=%.3f ground=%.3f\n",n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,ground);
        require(std::isfinite(ground) && std::fabs(n->mSRT.t.y-ground)<5,"floor4 Violet approach lost ground");
        combatDestination=Vector3f(approach[point][0],0,approach[point][1]);
        float dx=n->mSRT.t.x-combatDestination.x,dz=n->mSRT.t.z-combatDestination.z;combatWalking=dx*dx+dz*dz>=15*15;
        if(!combatWalking){std::printf("P2_FLOOR4_VIOLET_POINT index=%d x=%.3f y=%.3f z=%.3f ground=%.3f\n",point,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,ground);
            if(++point==9){state=2;timer=0;}}
    }else if(state==2){
        if(n->mVelocity.x*n->mVelocity.x+n->mVelocity.z*n->mVelocity.z>=1)return;
        auto toss=[&](int i){Piki* p=originals[i];p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);
            n->throwPiki(p,flower->mSRT.t);std::printf("P2_FLOOR4_VIOLET_THROW original=%d generator=62002\n",i);};
        if(thrown<5 && timer%20==0)toss(thrown++);
        if(thrown==5 && timer%60==0)for(int i=0;i<5;++i){Piki* p=originals[i];
            if(p->isAlive() && !p->getStickObject() && p->getState()==PIKISTATE_Normal && flower->isAlive() && flower->getCurrentState()==2){toss(i);break;}}
        if(sprouts==5){require(reds==15 && purples==0,"floor4 conversion body conservation");
            for(int i=0;i<5;++i)require(!originals[i]->isAlive(),"floor4 original Red survived conversion");
            std::puts("P2_FLOOR4_VIOLET_SPROUTS reds=15 purple=0 sprouts=5");state=3;timer=0;}
        require(timer<1800,"floor4 Violet conversion stalled");
    }else if(state==3 && timer>90){
        if(captainPluck && purples==1 && !captainPassed){captainPassed=true;std::puts("P2_BEASTS_CAPTAIN_PLUCK purple=1");}
        InteractBikkuri pluck(n);Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);
            if(!h->isAlive() || !h->mP2Purple || !h->canPullout())continue;
            if(!captainPluck){require(DelayPikiBirth,"floor4 expects native captain pluck");n->mSproutToPluck=h;n->mPikiToPluck=nullptr;
                n->mStateMachine->transit(n,NAVISTATE_NukuAdjust);captainPluck=true;break;}
            if(captainPassed)h->interactBikkuri(pluck);}
        if(reds==15 && purples==5 && sprouts==0){
            require(captainPassed,"floor4 captain pluck missing");
            require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor4 post conversion descent enabled");
            Iterator final(pikiMgr);CI_LOOP(final){Piki* p=static_cast<Piki*>(*final);if(!p->isAlive())continue;
                require(pc_piki_carry_strength(p)==(pc_p2_is_purple(p)?10:1),"floor4 carry identity");
                if(pc_p2_is_purple(p))require(pc_throw_selection_class(p)==4,"floor4 Purple selection identity");}
            beastsPartySnapshot(n);capture("floor4-violet-final.ppm");
            std::puts("PASS P2_BEASTS_FLOOR4_VIOLET reds=15 purple=5 sprouts=0 cargo=0 pokos=0 repairs_unchanged=1");std::fflush(stdout);std::_Exit(0);}
        require(timer<1500,"floor4 Violet pluck stalled");
    }
    std::fflush(stdout);
}
