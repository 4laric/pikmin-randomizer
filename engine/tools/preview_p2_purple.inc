// Included by the standalone room fixture after its capture/require helpers.
#include "pc_p2_purple.h"
#include "PikiHeadItem.h"
#include "PikiState.h"
#include "Pom.h"
#include "Interactions.h"
static void purpleFixture(Navi* n) {
    static int state=0,timer=0,thrown=0,repairs=0;
    static std::vector<Piki*> original,purples,reds;
    static std::vector<Pom*> flowers;
    static Vector3f treasureStart;
    static bool manualPluckStarted=false,manualPluckPassed=false;
    Pellet* target=pc_p2_preview_treasure();
    auto assign=[&](Piki* p){p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;p->mActiveAction->mChildActions[PikiAction::Transport].initialise(target);p->mMode=PikiMode::TransportMode;};
    ++timer;
    // Keep the captain awake while testing a long, deliberately slow heavy haul.
    n->mNeutralTime=0;
    if(timer%150==0)std::printf("P2_PURPLE_STATE phase=%d navi=%d\n",state,n->getCurrState()->getID());
    if(state==0 && timer>=90) {
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        repairs=playerState->getCurrParts();
        Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p->isAlive())original.push_back(p);}
        Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);if(b->isAlive() && b->mObjType==OBJTYPE_Pom)flowers.push_back(static_cast<Pom*>(b));}
        require(original.size()==20 && flowers.size()==2,"Purple fixture needs twenty Reds and two flowers");
        require(target->mConfig->mCarryMinPikis()==101 && target->mConfig->mCarryMaxPikis()==101,"Atlas source weights");
        require(target->stickSlot(100) && !target->isSlotFree(100),"physical slot 100 must exist");target->stickOffSlot(100);require(target->isSlotFree(100),"physical slot 100 release");
        for(Piki* p:original)require(!pc_p2_is_purple(p) && pc_piki_carry_strength(p)==1,"initial Reds must remain ordinary");
        n->mKontroller=new FixtureController();state=1;timer=0;capture("p2-violet-start.ppm");
        std::puts("P2_PURPLE_FIXTURE_READY");
    } else if(state==1) {
        if(thrown<10 && timer%20==0) {
            Piki* p=original[thrown];p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);
            n->throwPiki(p,flowers[thrown/5]->mSRT.t);++thrown;
        }
        // A real throw may miss a moving/opening petal. Retry only surviving,
        // unattached originals after the flower reopens; never create Purples directly.
        if(thrown==10 && timer>300 && timer%30==0) {
            for(int i=0;i<10;++i) {
                Piki* p=original[i];Pom* flower=flowers[i/5];
                if(p->isAlive() && !p->getStickObject() && p->getState()==PIKISTATE_Normal && flower->isAlive() && flower->getCurrentState()==2) {
                    p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);n->throwPiki(p,flower->mSRT.t);break;
                }
            }
        }
        std::vector<PikiHeadItem*> sprouts;Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(h->isAlive() && h->mP2Purple)sprouts.push_back(h);}
        if(timer%150==0)std::printf("P2_PURPLE_CONVERSION_PROGRESS thrown=%d sprouts=%d flower0=%d flower1=%d\n",thrown,int(sprouts.size()),flowers[0]->getCurrentState(),flowers[1]->getCurrentState());
        if(sprouts.size()==10) {
            int alive=0;Iterator it(pikiMgr);CI_LOOP(it){if(static_cast<Piki*>(*it)->isAlive())++alive;}
            require(alive==10,"conversion must conserve twenty bodies plus sprouts");state=2;timer=0;
            std::puts("P2_VIOLET_TEN_SPROUTS_PASS");capture("p2-violet-sprouts.ppm");
        }
        require(timer<1400,"actual throws did not produce ten Purple sprouts");
    } else if(state==2 && timer>90) {
        int purple=0,other=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()){if(pc_p2_is_purple(p))++purple;else ++other;}}
        if(manualPluckStarted && purple==1 && !manualPluckPassed){manualPluckPassed=true;std::puts("P2_PURPLE_CAPTAIN_PLUCK_PASS");}
        InteractBikkuri pluck(n);Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){
            PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(!h->isAlive() || !h->mP2Purple || !h->canPullout())continue;
            if(!manualPluckStarted){
                require(DelayPikiBirth,"fixture expects default delayed captain plucking");
                n->mSproutToPluck=h;n->mPikiToPluck=nullptr;n->mStateMachine->transit(n,NAVISTATE_NukuAdjust);manualPluckStarted=true;break;
            }
            if(manualPluckPassed)h->interactBikkuri(pluck);
        }
        if(purple==10 && other==10){state=3;timer=0;std::puts("P2_PURPLE_PLUCK_IDENTITY_PASS");}
        require(timer<1000,"Purple sprouts could not be plucked");
    } else if(state==3 && timer>120) {
        // Captain plucking leaves him on the incoming cargo route. Stage only
        // the captain out of the way; carrier and treasure positions are untouched.
        n->resetPosition(Vector3f(-260,mapMgr->getMinY(-260,240,true),240));
        Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;p->changeMode(PikiMode::FormationMode,n);if(pc_p2_is_purple(p))purples.push_back(p);else reds.push_back(p);}
        require(purples.size()==10 && reds.size()==10,"post-pluck population");
        for(Piki* p:purples){require(pc_piki_carry_strength(p)==10 && std::fabs(pc_piki_carry_power(p)-0.6f)<0.001f,"Purple power must differ from speed");require(pc_throw_selection_class(p)==4,"Purple must be a distinct held selection class");assign(p);}
        treasureStart=target->mSRT.t;state=4;timer=0;capture("p2-purple-squad.ppm");pc_p2_purple_status();
    } else if(state==4) {
        require(pc_p2_preview_pokos()==0,"insufficient squad credited Atlas");
        float dx=target->mSRT.t.x-treasureStart.x,dz=target->mSRT.t.z-treasureStart.z;
        require(dx*dx+dz*dz<4,"ten Purples moved the 101-weight Atlas");
        if(timer%150==0)std::printf("P2_PURPLE_INSUFFICIENT strength=%d\n",target->mCarrierCounter);
        if(target->mCarrierCounter==100 && timer>240){capture("p2-purple-100-of-101.ppm");assign(reds[0]);state=5;timer=0;std::puts("P2_PURPLE_100_CANNOT_LIFT_101_PASS");}
        require(timer<1400,"ten Purple carriers did not attach");
    } else if(state==5) {
        float dx=target->mSRT.t.x-treasureStart.x,dz=target->mSRT.t.z-treasureStart.z;
        if(timer%150==0)std::printf("P2_PURPLE_MIXED strength=%d distance=%.2f\n",target->mCarrierCounter,std::sqrt(dx*dx+dz*dz));
        if(dx*dx+dz*dz>100 && target->isAlive()) {capture("p2-purple-101-lift.ppm");for(size_t i=1;i<reds.size();++i)assign(reds[i]);state=6;timer=0;std::puts("P2_PURPLE_101_MIXED_LIFT_PASS");}
        require(timer<1800,"ten Purples and one Red failed to move Atlas");
    } else if(state==6) {
        if(timer%150==0)std::printf("P2_PURPLE_DELIVERY state=%d strength=%d pos=%.1f,%.1f,%.1f pokos=%d\n",target->getState(),target->mCarrierCounter,target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z,pc_p2_preview_pokos());
        if(pc_p2_preview_pokos()==200) {
            require(playerState->getCurrParts()==repairs,"Atlas changed P1 repairs");
            n->mStateMachine->transit(n,NAVISTATE_Pellet);
            require(n->mPellet && pc_p2_preview_deliver(n->mPellet),"Pod must recognize its carried captain");
            require(pc_p2_preview_pokos()==200 && playerState->getCurrParts()==repairs,"captain return must not award money or repairs");
            n->mStateMachine->transit(n,NAVISTATE_Walk);
            capture("p2-purple-final.ppm");pc_p2_purple_status();
            std::puts("PASS p2 Purple: real Violet throw/conversion/pluck, conserved 20 population, distinct identity/selection, 100 insufficient and 101 sufficient, native Atlas Pod delivery for 200 Pokos");
            std::fflush(stdout);std::_Exit(0);
        }
        require(timer<5000,"Atlas Pod delivery stalled");
    }
}
