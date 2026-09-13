// Opt-in, cargo-free engineering fixture. Uses native throw/conversion/pluck
// paths; scripted action selection is not manual-play or P2 Pom FSM parity.
#include "Generator.h"
#include <fstream>
static bool beastsFloor2Enabled=false;
static bool beastsRefund=false;
static bool beastsRestore=false;
static std::string beastsBoundary;
static void beastsBoundaryEnd(){if(!beastsBoundary.empty())std::printf("P2_BEASTS_BOUNDARY_END token=%s\n",beastsBoundary.c_str());}
static int beastsGlobalPurple=-1,beastsExpectedFlowers=2;
static void beastsPartySnapshot(Navi* n) {
    const float maximum=C_NAVI_PARM(n,mHealth);
    require(std::isfinite(maximum) && maximum>0 && std::isfinite(n->mHealth),"invalid snapshot captain health");
    const float health=n->mHealth/maximum;
    require(health>0 && health<=1,"snapshot captain is not a living survivor");
    std::vector<Piki*> survivors;Iterator it(pikiMgr);CI_LOOP(it) {
        Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;
        require(p->mHappa>=0 && p->mHappa<=2,"invalid survivor maturity");
        require(!p->getStickObject(),"snapshot survivor still attached");
        survivors.push_back(p);
    }
    require(survivors.size()==20,"snapshot survivor count");
    std::printf("P2_BEASTS_PARTY health=%.9g count=%zu\n",health,survivors.size());
    for(size_t i=0;i<survivors.size();++i) {
        Piki* p=survivors[i];
        const char* species=pc_p2_is_purple(p)?"purple":p->mColor==Red?"red":p->mColor==Blue?"blue":p->mColor==Yellow?"yellow":"unknown";
        std::printf("P2_BEASTS_SURVIVOR index=%zu species=%s maturity=%d\n",i,species,p->mHappa);
    }
    std::puts("P2_BEASTS_PARTY_END");
}
static void beastsFloor2Fixture(Navi* n) {
    static int state=0,timer=0,thrown=0,repairs=0;
    static std::vector<Piki*> originals;
    static Pom* flowers[2]={nullptr,nullptr};
    static bool captainPluck=false,captainPluckPassed=false;
    static int flowerIndex=0,retry=0;
    static bool approached=false;
    ++timer;n->mNeutralTime=0;
    if(state==0 && timer==1) {
        std::ifstream in("p2-beasts-boundary.txt");
        if(in) {
            std::string header,extra;
            require(bool(in>>header>>beastsBoundary) && header=="P2_BEASTS_BOUNDARY_1"
                && beastsBoundary.size()==64 && beastsBoundary.find_first_not_of("0123456789abcdef")==std::string::npos
                && !(in>>extra) && in.eof(),"invalid Beasts boundary input");
            std::printf("P2_BEASTS_BOUNDARY_BEGIN token=%s\n",beastsBoundary.c_str());
        }
    }
    if(state==0 && timer==1){std::ifstream marker("p2-beasts-refund-fixture.txt");beastsRefund=bool(marker);}
    if(state==0 && timer==1){std::ifstream marker("p2-beasts-restore-fixture.txt");beastsRestore=bool(marker);}
    const int extra=beastsRefund?1:0;
    auto target=[&](int i){return i<5+extra?0:1;};
    require(pc_p2_preview_cargo_free_ready() && !pc_p2_preview_ready() && !pc_p2_preview_treasure(),"Beasts cargo-free readiness contract");
    require(pc_p2_purples_enabled() && pc_p2_preview_goal(),"Beasts Purple and Pod initialization");
    require(pc_p2_preview_pokos()==0,"cargo-free Beasts credited a reward");
    int reds=0,purples=0,sprouts=0;
    Iterator pikis(pikiMgr);CI_LOOP(pikis) {
        Piki* p=static_cast<Piki*>(*pikis);if(!p->isAlive())continue;
        if(pc_p2_is_purple(p))++purples;else {require(p->mColor==Red,"unexpected Beasts squad color");++reds;}
    }
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads) {
        PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(!h->isAlive())continue;
        require(h->mP2Purple,"unexpected ordinary sprout");++sprouts;
    }
    if(beastsRestore) {
        require(!beastsRefund && beastsExpectedFlowers==0,"restore fixture requires suppression");
        require(reds+purples==20 && sprouts==0,"restored party population changed");
        Iterator bosses(bossMgr);CI_LOOP(bosses)require(!static_cast<Boss*>(*bosses)->isAlive(),"restore fixture spawned a flower");
        if(timer==1){repairs=playerState->getCurrParts();std::printf("P2_BEASTS_READY reds=%d flowers=0 cargo=0\n",reds);}
        if(timer>=300) {
            require(playerState->getCurrParts()==repairs,"restoration changed repairs");
            beastsPartySnapshot(n);capture("beasts-floor2-final.ppm");beastsBoundaryEnd();
            std::puts("PASS P2_BEASTS_RESTORE updates=300 cargo=0 pokos=0 repairs_unchanged=1");std::fflush(stdout);std::_Exit(0);
        }
        return;
    }
    if(timer%150==0)std::printf("P2_BEASTS_PROGRESS phase=%d red=%d purple=%d sprouts=%d thrown=%d\n",state,reds,purples,sprouts,thrown);
    if(state==0 && timer>=90) {
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        repairs=playerState->getCurrParts();
        require(reds==20 && purples==0 && sprouts==0,"Beasts initial population");
        Iterator initial(pikiMgr);CI_LOOP(initial){Piki* p=static_cast<Piki*>(*initial);if(p->isAlive())originals.push_back(p);}
        if(beastsRefund){pc_p2_make_purple(originals[0]);std::puts("P2_BEASTS_REFUND_INITIAL reds=19 purple=1");}
        int count=0;Iterator bosses(bossMgr);CI_LOOP(bosses) {
            Boss* b=static_cast<Boss*>(*bosses);if(!b->isAlive())continue;
            require(b->mObjType==OBJTYPE_Pom && b->mGenerator,"unexpected Beasts boss");
            unsigned id=b->mGenerator->_70;require(id==62000 || id==62001,"unexpected Violet generator");
            int index=int(id-62000);require(!flowers[index],"duplicate Violet generator");
            flowers[index]=static_cast<Pom*>(b);++count;
            require(pc_p2_violet(flowers[index]),"flower is not Violet proxy");
            const Vector3f& pos=*b->getInitPosition();
            std::printf("P2_BEASTS_FLOWER id=%u x=%.3f y=%.3f z=%.3f live_x=%.3f live_y=%.3f live_z=%.3f ground=%.3f\n",id,pos.x,pos.y,pos.z,b->mSRT.t.x,b->mSRT.t.y,b->mSRT.t.z,mapMgr->getMinY(pos.x,pos.z,true));
        }
        require(count==beastsExpectedFlowers,"Beasts generation flower count differs");
        Iterator enemies(tekiMgr);CI_LOOP(enemies)require(!static_cast<Teki*>(*enemies)->isAlive(),"unexpected Beasts enemy");
        Iterator pellets(pelletMgr);CI_LOOP(pellets)require(!static_cast<Pellet*>(*pellets)->isAlive(),"hidden Beasts cargo");
        n->mKontroller=new FixtureController();state=count?1:3;timer=0;
        if(beastsGlobalPurple>=0)std::printf("P2_BEASTS_GENERATION purple=%d flowers=%d\n",beastsGlobalPurple,count);
        std::printf("P2_BEASTS_READY reds=%d flowers=%d cargo=0\n",20-extra,count);capture("beasts-floor2-start.ppm");
    } else if(state==1) {
        if(flowerIndex==0 && sprouts==5+extra) {
            require(reds==15-extra && purples==0,"first Violet conversion body conservation");
            for(int i=0;i<5+extra;++i)require(!originals[i]->isAlive(),"first flower did not consume its original Reds");
            std::printf("P2_BEASTS_FLOWER_CONVERTED id=62000 count=%d\n",5+extra);flowerIndex=1;approached=false;
        }
        if(!approached) {
            combatDestination=flowers[flowerIndex]->mSRT.t;
            float dx=combatDestination.x-n->mSRT.t.x,dz=combatDestination.z-n->mSRT.t.z;
            combatWalking=dx*dx+dz*dz>80*80;
            if(!combatWalking && n->mVelocity.x*n->mVelocity.x+n->mVelocity.z*n->mVelocity.z<1) {
                approached=true;
                std::printf("P2_BEASTS_APPROACH flower=%d distance=%.3f\n",62000+flowerIndex,std::sqrt(dx*dx+dz*dz));
            }
            require(timer<1600,"Beasts controller approach stalled");
            return;
        }
        auto toss=[&](int i) {
            Piki* p=originals[i];p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);
            n->throwPiki(p,flowers[target(i)]->mSRT.t);
            std::printf("P2_BEASTS_THROW original=%d flower=%d\n",i,62000+target(i));
        };
        if(thrown<(flowerIndex+1)*5+extra && (!beastsRefund || thrown!=1 || sprouts==1) && timer%20==0)toss(thrown++);
        if((thrown==(flowerIndex+1)*5+extra || (beastsRefund && thrown==1 && sprouts==0)) && timer%60==0) {
            for(int j=0;j<(flowerIndex==0?5+extra:5);++j) {
                int i=flowerIndex==0?(retry+j)%(5+extra):5+extra+(retry+j)%5;
                if(i>=thrown)continue;
                Piki* p=originals[i];Pom* flower=flowers[target(i)];
                if(p->isAlive() && !p->getStickObject() && p->getState()==PIKISTATE_Normal && flower->isAlive() && flower->getCurrentState()==2){retry=(i%5+1)%5;toss(i);break;}
            }
        }
        if(sprouts==10+extra) {
            require(reds==10-extra && purples==0,"Beasts conversion body conservation");
            for(int i=0;i<10+extra;++i)require(!originals[i]->isAlive(),"conversion retained an original Red");
            std::puts("P2_BEASTS_FLOWER_CONVERTED id=62001 count=5");
            std::printf("P2_BEASTS_SPROUTS reds=%d purple=0 sprouts=%d\n",10-extra,10+extra);capture("beasts-floor2-sprouts.ppm");state=2;timer=0;
        }
        require(timer<1600,"Beasts real throws did not produce ten sprouts");
    } else if(state==3) {
        require(reds==20 && purples==0 && sprouts==0,"suppressed Beasts population changed");
        Iterator bosses(bossMgr);CI_LOOP(bosses)require(!static_cast<Boss*>(*bosses)->isAlive(),"suppressed flower appeared");
        Iterator pellets(pelletMgr);CI_LOOP(pellets)require(!static_cast<Pellet*>(*pellets)->isAlive(),"suppressed stage birthed cargo");
        if(timer>=300) {
            require(playerState->getCurrParts()==repairs,"suppressed Beasts changed repairs");
            capture("beasts-floor2-final.ppm");
            beastsPartySnapshot(n);
            beastsBoundaryEnd();
            std::puts("PASS P2_BEASTS_SUPPRESSED reds=20 purple=0 sprouts=0 flowers=0 cargo=0 pokos=0 repairs_unchanged=1");std::fflush(stdout);std::_Exit(0);
        }
    } else if(state==2 && timer>90) {
        if(captainPluck && purples==1 && !captainPluckPassed) {
            captainPluckPassed=true;std::puts("P2_BEASTS_CAPTAIN_PLUCK purple=1");
        }
        InteractBikkuri pluck(n);Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads) {
            PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(!h->isAlive() || !h->mP2Purple || !h->canPullout())continue;
            if(!captainPluck) {
                require(DelayPikiBirth,"Beasts expects delayed captain pluck path");
                n->mSproutToPluck=h;n->mPikiToPluck=nullptr;n->mStateMachine->transit(n,NAVISTATE_NukuAdjust);captainPluck=true;break;
            }
            if(captainPluckPassed)h->interactBikkuri(pluck);
        }
        if(reds==10-extra && purples==10+extra && sprouts==0) {
            require(captainPluckPassed,"missing captain pluck");
            Iterator final(pikiMgr);CI_LOOP(final) {
                Piki* p=static_cast<Piki*>(*final);if(!p->isAlive())continue;
                require(pc_piki_carry_strength(p)==(pc_p2_is_purple(p)?10:1),"Beasts carry identity");
                if(pc_p2_is_purple(p))require(pc_throw_selection_class(p)==4,"Beasts Purple selection identity");
            }
            require(playerState->getCurrParts()==repairs,"Beasts changed P1 repairs");
            capture("beasts-floor2-final.ppm");
            beastsPartySnapshot(n);
            beastsBoundaryEnd();
            std::printf("PASS P2_BEASTS_FLOOR2 reds=%d purple=%d sprouts=0 cargo=0 pokos=0 repairs_unchanged=1\n",10-extra,10+extra);std::fflush(stdout);std::_Exit(0);
        }
        require(timer<1200,"Beasts native plucking stalled");
    }
    std::fflush(stdout);
}
