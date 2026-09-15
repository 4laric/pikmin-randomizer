// Included by the standalone room fixture. Exercises production throw,
// collision, Teki strategy damage and corpse paths in an isolated run.
#include "pc_p2_purple_impact.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_kochappy_stun.h"
#include "pc_p2_purple.h"
#include "Interactions.h"
#include "TAI/Chappy.h"

static void purpleImpactFixture(Navi* n)
{
    static int state=0,timer=0,attempts=0,activeFrames=0;
    static Piki* source=nullptr;
    static Teki* target=nullptr;
    static float startingHealth=0.0f;
    static float healthBefore=0.0f;
    static bool sourceParked=false;
    ++timer;

    auto throwAtTarget=[&]() {
        require(source && source->isAlive() && target && target->isAlive(),"impact actors unavailable");
        if(source->isStickTo())source->endStickObject();
        source->changeMode(PikiMode::FreeMode,n);
        Vector3f enemyPos=target->mSRT.t;
        // Land beside the dwarf, within the 60-unit quake radius. A center hit
        // can enter the vanilla press path before the quake receiver runs.
        Vector3f landingPos(enemyPos.x,enemyPos.y,enemyPos.z+45.0f);
        Vector3f captainPos(enemyPos.x-80.0f,mapMgr->getMinY(enemyPos.x-80.0f,enemyPos.z,true),enemyPos.z+45.0f);
        n->resetPosition(captainPos);
        source->mFSM->transit(source,PIKISTATE_Flying);
        n->throwPiki(source,landingPos);
        ++attempts;timer=0;activeFrames=0;sourceParked=false;
        std::printf("P2_PURPLE_IMPACT_FIXTURE_THROW attempt=%d target_health=%.1f\n",attempts,target->mHealth);
    };

    if(state==0 && timer>=90) {
        require(pc_p2_purple_impact_enabled(),"impact profile opt-in missing");
        Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(!source && p->isAlive())source=p;}
        Iterator enemies(tekiMgr);CI_LOOP(enemies){Teki* e=static_cast<Teki*>(*enemies);if(pc_p2_kochappy_registered(e)){require(!target,"multiple registered Red dwarfs");target=e;}}
        require(source && target,"fixture needs a Piki and registered Red dwarf");
        startingHealth=target->mHealth;
        Iterator parked(pikiMgr);CI_LOOP(parked){Piki* p=static_cast<Piki*>(*parked);if(p!=source)p->resetPosition(Vector3f(-220.0f,mapMgr->getMinY(-220.0f,-180.0f,true),-180.0f));}
        pc_p2_make_purple(source);
        require(pc_p2_is_purple(source),"source did not become Purple");
        throwAtTarget();state=1;
        std::puts("P2_PURPLE_IMPACT_FIXTURE_READY actual Navi throw and registered Red target");
    } else if(state==1) {
        if(pc_p2_kochappy_stun_active(target) && !sourceParked) {
            if(source->isStickTo())source->endStickObject();
            source->changeMode(PikiMode::FreeMode,n);
            source->resetPosition(Vector3f(-220.0f,mapMgr->getMinY(-220.0f,-180.0f,true),-180.0f));
            sourceParked=true;
        }
        const bool settled=target->mGroundTriangle;
        if(timer%30==0)std::printf("P2_PURPLE_IMPACT_TRACE attempt=%d state=%d ground=%d vy=%.2f active=%d health=%.1f damage=%.1f parked=%d\n",attempts,target->mStateID,target->mGroundTriangle?1:0,target->mVelocity.y,pc_p2_kochappy_stun_active(target)?1:0,target->mHealth,target->mDamageCount,sourceParked?1:0);
        if(pc_p2_kochappy_stun_active(target) && settled)++activeFrames;
        else activeFrames=0;
        // Bounce-only/missed rolls do not remain settled. Ninety continuous
        // grounded frames proves the ten-second Fit branch was reached naturally;
        // Bounce makes its decision on the fourth grounded update.
        if(activeFrames>=90) {
            require(target->mStateID==CHAPPYSTATE_P2PurpleImpact,"active target left impact state");
            healthBefore=target->mHealth;
            InteractAttack hit(source,nullptr,5.0f,false);
            require(target->stimulate(hit),"nonlethal attack callback rejected during Fit");
            state=2;timer=0;
            std::printf("P2_PURPLE_IMPACT_FIT_PASS attempts=%d health=%.1f\n",attempts,healthBefore);
        } else if(timer>=180 && !pc_p2_kochappy_stun_active(target)) {
            require(attempts<24,"natural 30 percent Fit roll not observed");
            // Landing damage is production behavior. Refill the one fixture
            // receiver between failed random branches so it can sample Fit.
            target->mHealth=startingHealth;
            throwAtTarget();
        }
    } else if(state==2 && timer>=2) {
        require(target->mHealth<=healthBefore-4.9f && target->isAlive(),"nonlethal native damage did not apply during Fit");
        std::printf("P2_PURPLE_IMPACT_DAMAGE_PASS before=%.1f after=%.1f\n",healthBefore,target->mHealth);
        InteractAttack lethal(source,nullptr,target->mHealth+1.0f,false);
        require(target->stimulate(lethal),"lethal attack callback rejected during Fit");
        state=3;timer=0;
    } else if(state==3) {
        if(target->mDeadState || !target->isAlive()) {
            state=4;timer=0;
            std::puts("P2_PURPLE_IMPACT_LETHAL_PASS normal target death entered");
        }
        require(timer<300,"lethal damage did not enter native death path");
    } else if(state==4) {
        Iterator pellets(pelletMgr);CI_LOOP(pellets){
            Pellet* corpse=static_cast<Pellet*>(*pellets);
            if(corpse->isAlive() && corpse->mPelletView==static_cast<PelletView*>(target)) {
                std::puts("PASS p2 Purple impact: actual throw emitted one registered Red earthquake, natural bounce/Fit persisted, nonlethal damage applied, lethal callback produced normal corpse");
                std::fflush(stdout);std::_Exit(0);
            }
        }
        require(timer<600,"normal corpse did not appear after stunned death");
    }
}
