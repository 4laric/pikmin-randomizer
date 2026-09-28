#define main groink_unused_fixture_main
#include "p2_groink_target_runtime.cpp"
#undef main
#include "NaviState.h"
#include "Interactions.h"
#include "PaniPikiAnimator.h"
#include "../pc_port/pc_p2_demon_drop_policy.h"

// Actor-local fixture state; no registry/shared hook changes. Flick ID keeps
// normal walk AI out, but this is NOT the production Flick implementation.
class DemonDropState final : public NaviState {
public:
    P2DemonDropPolicy policy;
    unsigned generation=0, bounces=0, damageEvents=0;
    bool complete=false;
    DemonDropState():NaviState(NAVISTATE_Flick) {}
    void begin(Navi* n) {
        auto c=policy.begin(++generation,10,200); require(c.accepted,"drop admission");
        setMachine(n->mStateMachine); n->setCurrState(this);
        n->mGroundTriangle=nullptr;
        n->mVelocity.set(0,c.actualY,0); n->mTargetVelocity.set(0,c.targetY,0);
        n->mVolatileVelocity.set(0,0,0);
        n->startMotion(PaniMotionInfo(PIKIANIM_Fall,n),PaniMotionInfo(PIKIANIM_Fall));
        std::printf("DEMON_DROP_BEGIN generation=%u actual_y=%.3f target_y=%.3f health=%.3f\n",generation,n->mVelocity.y,n->mTargetVelocity.y,n->mHealth);
    }
    void cleanup(Navi*) override { policy.cancel(); }
    void exec(Navi* n) override {
        if(policy.phase()!=P2DemonDropPhase::Falling) {
            n->mVelocity.set(0,0,0); n->mTargetVelocity.set(0,0,0);
        }
        auto c=policy.tick(generation,gsys->getFrameTime());
        if(c.startGetUp) n->startMotion(PaniMotionInfo(PIKIANIM_GetUp,n),PaniMotionInfo(PIKIANIM_GetUp));
    }
    void procBounceMsg(Navi* n,MsgBounce*) override {
        auto c=policy.bounce(generation); if(!c.accepted) return;
        ++bounces;
        std::printf("DEMON_DROP_BOUNCE generation=%u y=%.3f health=%.3f\n",generation,n->mSRT.t.y,n->mHealth);
        // No P1 equivalent of P2 addDamage(0,true) is asserted here.
        if(c.startKnockdown) n->startMotion(PaniMotionInfo(PIKIANIM_JKoke,n),PaniMotionInfo(PIKIANIM_JKoke));
    }
    void procAnimMsg(Navi* n,MsgAnim* msg) override {
        if(msg->mKeyEvent->mEventType!=KEY_Finished) return;
        const auto phase=policy.phase();
        const int motion=n->mNaviAnimMgr.getLowerAnimator().getCurrentMotionIndex();
        if((phase==P2DemonDropPhase::Knockdown&&motion!=PIKIANIM_JKoke)||
           (phase==P2DemonDropPhase::GetUp&&motion!=PIKIANIM_GetUp)) return;
        auto c=policy.animationEnd(generation,phase);
        if(c.deliverDamage) {
            ++damageEvents;
            const float before=n->mHealth;
            InteractAttack attack(n,nullptr,c.damage,false);
            bool accepted=n->stimulate(attack);
            std::printf("DEMON_DROP_DAMAGE generation=%u animation_end=1 accepted=%d before=%.3f after=%.3f\n",generation,int(accepted),before,n->mHealth);
            require(accepted&&n->mHealth<before,"native damage receiver");
        }
        if(c.resume) { complete=true; n->mStateMachine->transit(n,NAVISTATE_Walk); }
    }
};
class DemonDropApp final : public PlugPikiApp {
    DemonDropState drop;
    int frames=0,stage=0,wait=0;
    float initialHealth=0,cancelHealth=0,initialY=0;
    bool descended=false;
public:
    int idle() override {
        int result=PlugPikiApp::idle(); require(++frames<1800,"drop timeout");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()) return result;
        auto* n=naviMgr->getNavi();
        if(stage==0) {
            if(++wait<30) return result;
            n->releasePikis();
            float ground=mapMgr->getMinY(0,100,true);
            n->resetPosition(Vector3f(0,ground+120,100)); initialY=n->mSRT.t.y; initialHealth=n->mHealth;
            drop.begin(n); stage=1;
        } else if(stage==1) {
            descended|=n->mSRT.t.y<initialY-5;
            if(drop.complete) {
                require(descended&&drop.bounces==1&&drop.damageEvents==1,"natural fall sequence");
                require(n->mHealth<initialHealth,"health changed after animation");
                float ground=mapMgr->getMinY(0,100,true);
                n->resetPosition(Vector3f(0,ground+120,100));
                drop.complete=false; drop.begin(n); stage=2;
            }
        } else if(stage==2 && drop.policy.phase()==P2DemonDropPhase::Knockdown) {
            cancelHealth=n->mHealth; const auto old=drop.generation;
            n->mStateMachine->transit(n,NAVISTATE_Walk); // Explicit test interruption.
            require(!drop.policy.animationEnd(old,P2DemonDropPhase::Knockdown).deliverDamage,"stale policy event after cancellation");
            wait=0; stage=3;
            std::printf("DEMON_DROP_CANCEL generation=%u health=%.3f\n",old,cancelHealth);
        } else if(stage==3 && ++wait>=90) {
            require(n->mHealth==cancelHealth&&drop.damageEvents==1,"cancel retained health");
            std::puts("PASS DEMON_DROP_NATIVE terrain=1 natural_animation=1 p1_attack_receiver=1 interrupted_drop=1 p2_receiver_fidelity=0");
            std::fflush(stdout); std::_Exit(0);
        }
        return result;
    }
};
#ifndef DEMON_DROP_NO_MAIN
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1); SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1"); pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"room flag");
    require(pc_window_init("Demon private captain drop fixture",960,720),"window init");
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr=new NodeMgr();
    gsys->run(new DemonDropApp()); return 0;
}

#endif
