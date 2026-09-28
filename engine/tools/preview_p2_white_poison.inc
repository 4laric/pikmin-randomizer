#include "pc_p2_white_poison.h"
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "TAI/AttackActions.h"
#include "Generator.h"

static void whitePoisonFixture(Navi*) {
    static int state=0,timer=0;
    static Teki* predator=nullptr;
    static std::vector<Piki*> victims;
    ++timer;
    if(state==0 && timer>90) {
        Teki* ordinary=nullptr;
        Iterator enemies(tekiMgr);CI_LOOP(enemies){Teki* t=static_cast<Teki*>(*enemies);if(!t||!t->isAlive())continue;
            if(t->mGenerator&&t->mGenerator->_70==436207616u)predator=t;else if(t->mTekiType==TEKI_Chappy)ordinary=t;}
        Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p&&p->isAlive())victims.push_back(p);}
        require(predator&&predator->mTekiType==TEKI_Swallow,"registered adult predator");
        require(ordinary&&!pc_p2_white_poison_predator(ordinary),"unbound predator excluded");
        require(victims.size()==20,"twenty initial victims");
        victims.back()->kill(false);require(!pc_p2_white_poison_prepare(predator,victims.back()),"dead victim excluded");
        for(int i=0;i<2;++i)pc_p2_make_white(victims[i]);
        CollPart* mouth=predator->mCollInfo->getSphere('slot');require(mouth&&mouth->getChildCount()>=5,"adult mouth slots");
        for(int i=0;i<3;++i)require(victims[i]->stimulate(InteractSwallow(predator,mouth->getChildAt(i),0)),"injected mouth capture");
        predator->mHealth=2000;predator->mStoredDamage=0;predator->mDamageCount=9;
        predator->setAnimationKeyOption(BTeki::ANIMATION_KEY_OPTION_ACTION_1);
        TaiAnimationSwallowingAction swallow(-1);swallow.act(*predator);predator->clearAnimationKeyOptions();
        require(std::fabs(predator->mStoredDamage-1500.f)<0.01f,"two Whites queue additive retail poison");
        require(std::fabs(predator->mDamageCount-9.f)<0.01f,"poison does not increment flick counter");
        require(!victims[0]->isAlive()&&!victims[1]->isAlive()&&!victims[2]->isAlive(),"White and nonWhite mouth victims consumed");
        require(!pc_p2_white_poison_finish(predator,victims[0],true),"consumption callback deduplicated");
        predator->makeDamaged();require(std::fabs(predator->mHealth-500.f)<0.01f,"explicit native additive HP damage application");
        pc_p2_make_white(victims[3]);require(victims[3]->stimulate(InteractSwallow(predator,mouth->getChildAt(3),0)),"invincible mouth capture");
        predator->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);predator->setAnimationKeyOption(BTeki::ANIMATION_KEY_OPTION_ACTION_1);swallow.act(*predator);predator->clearAnimationKeyOptions();
        require(predator->mStoredDamage==0&&predator->mHealth==500,"invincible predator rejects poison");predator->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
        pc_p2_make_white(victims[4]);require(victims[4]->stimulate(InteractSwallow(predator,mouth->getChildAt(4),0)),"lethal mouth capture");
        predator->mHealth=700;predator->setAnimationKeyOption(BTeki::ANIMATION_KEY_OPTION_ACTION_1);swallow.act(*predator);predator->clearAnimationKeyOptions();
        require(std::fabs(predator->mStoredDamage-750.f)<0.01f,"lethal retail poison queued");predator->makeDamaged();require(predator->mHealth==0,"lethal poison reaches zero HP");
        std::puts("P2_WHITE_POISON_HP_PASS injected mouth attachment; real ACTION_1 consumption; two Whites=1500, red=0, invincible=0, lethal=750");state=1;timer=0;
    } else if(state==1) {
        if(!predator->isAlive()) {
            Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* corpse=static_cast<Pellet*>(*pellets);
                if(corpse->isAlive()&&corpse->mPelletView==static_cast<PelletView*>(predator)){
                    std::puts("PASS p2 White poison: registered adult consumption, additive source damage, dedup, invulnerability and normal corpse creation");std::fflush(stdout);std::_Exit(0);}}
        }
        require(timer<600,"zero-health predator did not create a normal corpse");
    }
}
