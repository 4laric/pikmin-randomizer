// Included by the standalone room fixture after capture/require helpers.
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "pc_p2_purple.h"
#include "PikiHeadItem.h"
#include "PikiState.h"
#include "Pom.h"
#include "Interactions.h"

static void whiteFixture(Navi* n) {
    static int state=0,timer=0,thrown=0;
    static std::vector<Piki*> original;
    static Pom* flower=nullptr;
    ++timer;n->mNeutralTime=0;
    if(state==0 && timer>=90){
        for(int flag=0;flag<DEMOFLAG_COUNT;++flag)playerState->mDemoFlags.setFlagOnly(flag);
        Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p->isAlive())original.push_back(p);}
        Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);if(b->isAlive()&&b->mObjType==OBJTYPE_Pom){require(!flower,"White fixture has multiple Ivory buds");flower=static_cast<Pom*>(b);}}
        require(original.size()==20&&flower,"White fixture needs twenty Reds and one bound Ivory bud");
        for(Piki* p:original)require(pc_p2_species(p)==P2SpeciesRed&&pc_p2_has_red_immunity(p),"initial Reds must remain ordinary");
        n->mKontroller=new FixtureController();state=1;timer=0;capture("p2-ivory-start.ppm");std::puts("P2_WHITE_FIXTURE_READY");
    } else if(state==1){
        if(thrown<5&&timer%20==0){Piki* p=original[thrown];p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);n->throwPiki(p,flower->mSRT.t);++thrown;}
        if(thrown==5&&timer>300&&timer%30==0){for(int i=0;i<5;++i){Piki* p=original[i];if(p->isAlive()&&!p->getStickObject()&&p->getState()==PIKISTATE_Normal&&flower->isAlive()&&flower->getCurrentState()==2){p->changeMode(PikiMode::FreeMode,n);p->mFSM->transit(p,PIKISTATE_Flying);n->throwPiki(p,flower->mSRT.t);break;}}}
        int sprouts=0;Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(h->isAlive()&&h->mP2White)++sprouts;}
        if(sprouts==5){int alive=0;Iterator it(pikiMgr);CI_LOOP(it){if(static_cast<Piki*>(*it)->isAlive())++alive;}require(alive==15,"Ivory conversion must conserve bodies");capture("p2-ivory-sprouts.ppm");std::puts("P2_IVORY_FIVE_SPROUTS_PASS");state=2;timer=0;}
        require(timer<1400,"actual throws did not produce five White sprouts");
    } else if(state==2&&timer>90){
        InteractBikkuri pluck(n);Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(h->isAlive()&&h->mP2White&&h->canPullout())h->interactBikkuri(pluck);}
        int white=0,other=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;if(pc_p2_is_white(p)){++white;require(pc_p2_species(p)==P2SpeciesWhite&&!pc_p2_has_red_immunity(p),"White inherited Red identity/immunity");require(pc_throw_selection_class(p)==5,"White selection class");require(std::fabs(pc_piki_carry_power(p)-3.f)<0.001f,"White leaf carry power");}else ++other;}
        if(white==5&&other==15){capture("p2-white-squad.ppm");std::puts("PASS p2 White: real Ivory throw/conversion/pluck, conserved 20 population, distinct identity/selection, source-backed leaf carry and no Red immunity");std::fflush(stdout);std::_Exit(0);}
        require(timer<1000,"White sprouts could not be plucked");
    }
}
