#include <SDL2/SDL.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "MoviePlayer.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "Interactions.h"
#include "GameCoreSection.h"
#include "Section.h"
#include "pc_p2_demon_drop_state.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
static const char* mode="positive";
static void require(bool b,const char* s) { if(!b){std::printf("FAIL DEMON_REGISTERED %s\n",s);std::fflush(stdout);std::_Exit(1);} }
static GameCoreSection* findCore(CoreNode* node,int depth=0) {
    if(!node||depth>20) return nullptr;
    if(auto* core=dynamic_cast<GameCoreSection*>(node)) return core;
    for(auto* c=node->Child();c;c=c->Next()) if(auto* core=findCore(c,depth+1)) return core;
    return nullptr;
}
static bool is(const char* s){return std::strcmp(mode,s)==0;}
class RegisteredApp final : public PlugPikiApp {
    int frames=0,ticks=0,stage=0,wait=0;
    float hp=0;
    bool sawKnockdown=false, interrupted=false;
public:
    int idle() override {
        int r=PlugPikiApp::idle(); require(++frames<2400,"timeout");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return r;}
        if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()) return r;
        auto* n=naviMgr->getNavi(); ++ticks;
        if(stage==0) {
            if(ticks<30)return r;
            static_assert(NAVISTATE_Flick==8&&NAVISTATE_IroIro==35&&NAVISTATE_DemonDrop==36&&NAVISTATE_Count==37,"registry IDs");
            hp=n->mHealth; n->releasePikis();
            std::printf("DEMON_FIXTURE_WALK_SETUP previous=%d\n",n->getCurrState()->getID());
            n->mStateMachine->transit(n,NAVISTATE_Walk); // Explicit setup from preview Starting state.
            if(is("direct")) {
                n->mStateMachine->transit(n,NAVISTATE_DemonDrop);
                require(n->getCurrState()->getID()==NAVISTATE_Walk&&pc_demon_drop_phase(n)==P2DemonDropPhase::Idle,"unadmitted state stranded");
                std::puts("PASS DEMON_REGISTERED mode=direct unadmitted_fallback=1");std::fflush(stdout);std::_Exit(0);
            }
            if(is("capacity")) {
                PaniAnimKeyListener* old=nullptr;
                unsigned count=0;
                for(unsigned g=1;g<=4100;++g) {
                    if(!pc_demon_drop_begin(n,g,10,200)) break;
                    ++count;
                    if(!old) old=n->mNaviAnimMgr.getUpperAnimator().mListener;
                    else {
                        auto phase=pc_demon_drop_phase(n); PaniAnimKeyEvent stale(KEY_Finished);
                        old->animationKeyUpdated(stale); // Synthetic obsolete issuance probe.
                        require(pc_demon_drop_phase(n)==phase&&n->mHealth==hp,"old listener after new admission");
                    }
                    pc_demon_drop_reset(n);n->mStateMachine->transit(n,NAVISTATE_Walk);
                    PaniAnimKeyEvent stale(KEY_Finished);old->animationKeyUpdated(stale);
                    require(n->getCurrState()->getID()==NAVISTATE_Walk&&n->mHealth==hp,"old listener after reset");
                }
                require(count==4094&&!pc_demon_drop_begin(n,5000,10,200),"listener capacity refusal");
                std::printf("PASS DEMON_REGISTERED mode=capacity admitted=%u synthetic_listener_probes=1\n",count);
                std::fflush(stdout);std::_Exit(0);
            }
            if(is("flick")) {
                n->mFlickIntensity=20; n->mStateMachine->transit(n,NAVISTATE_Flick);
                require(n->getCurrState()->getID()==NAVISTATE_Flick,"ordinary Flick registered");
            } else {
                n->resetPosition(Vector3f(0,mapMgr->getMinY(0,100,true)+120,100));
                std::printf("DEMON_ADMISSION state=%d alive=%d flags=%x rope=%d stick=%d limit=%d index36=%d count=%d\n",n->getCurrState()->getID(),int(n->isAlive()),n->mCreatureFlags,int(n->mRope!=nullptr),int(n->isStickTo()),n->mStateMachine->mStateLimit,n->mStateMachine->mStateIndexes[36],n->mStateMachine->mStateCount);
                require(pc_demon_drop_begin(n,1,is("fatal")?200:10,200),"admission");
                require(n->getCurrState()->getID()==36,"dedicated state");
                require(n->mVelocity.y==-400&&n->mTargetVelocity.y==-200,"entry velocities");
            }
            stage=1; return r;
        }
                auto p=pc_demon_drop_phase(n);
        if(is("stage_exit")) {
            auto* listener=n->mNaviAnimMgr.getUpperAnimator().mListener;
            auto* core=findCore(gameflow.mGameSection);require(core!=nullptr,"production core node");
            core->exitStage(); require(naviMgr==nullptr,"production manager invalidation");
            PaniAnimKeyEvent stale(KEY_Finished);listener->animationKeyUpdated(stale);
            require(n->mHealth==hp&&!pc_demon_drop_begin(n,2,10,200),"retired state re-admission");
            std::puts("PASS DEMON_REGISTERED mode=stage_exit actual_exitStage=1 synthetic_obsolete_listener=1 heap_disposal_untested=1");
            std::fflush(stdout);std::_Exit(0);
        }
        if(std::strncmp(mode,"handoff_",8)==0) {
            if(!interrupted) {
                if(is("handoff_flick")) {
                    InteractFlick flick(n,42,0,0);require(n->stimulate(flick),"incoming Flick receiver");
                    require(n->mFlickIntensity==42,"Flick intensity erased");
                } else if(is("handoff_geyzer")) {
                    InteractGeyzer geyzer(n,Vector3f(90,0,120));require(n->stimulate(geyzer),"incoming Geyzer receiver");
                    auto* state=static_cast<NaviGeyzerState*>(n->getCurrState());
                    require(state->mLaunchTargetPos.x==90&&state->mLaunchTargetPos.z==120,"Geyzer payload erased");
                } else {
                    int next=is("handoff_bury")?NAVISTATE_Bury:is("handoff_pressed")?NAVISTATE_Pressed:NAVISTATE_Walk;
                    n->mStateMachine->transit(n,next);
                }
                require(n->mVelocity.length()==0&&n->mTargetVelocity.length()==0&&n->mVolatileVelocity.length()==0,"handoff residual drop");
                require(pc_demon_drop_phase(n)==P2DemonDropPhase::Idle,"handoff pending policy");
                interrupted=true;wait=0;return r;
            }
            require(n->mHealth==hp&&n->getCurrState()->getID()!=36,"handoff late damage");
            if(++wait==1&&is("handoff_geyzer"))require(n->mTargetVelocity.y>0,"Geyzer new impulse lost");
            if(wait>=30){std::printf("PASS DEMON_REGISTERED mode=%s health=%.3f\n",mode,n->mHealth);std::fflush(stdout);std::_Exit(0);}
            return r;
        }
        if(p==P2DemonDropPhase::Knockdown||p==P2DemonDropPhase::Lay||p==P2DemonDropPhase::GetUp) {
            sawKnockdown=true;
            require(n->mVelocity.length()<.001f&&n->mTargetVelocity.length()<.001f&&n->mVolatileVelocity.length()<.001f,"postphysics residual velocity");
            require(n->mGroundTriangle!=nullptr,"ground retained");
        }
        if(!interrupted&&(((is("interrupt")||is("external"))&&p==P2DemonDropPhase::Knockdown)||(is("reset")&&p==P2DemonDropPhase::Falling))) {
            if(is("reset")) {
                const int heap=gsys->setHeap(SYSHEAP_App);n->reset();gsys->setHeap(heap);
                require(n->mVelocity.length()==0&&n->mTargetVelocity.length()==0&&n->mVolatileVelocity.length()==0,"reset velocity disposition");
                require(!n->mGroundTriangle&&!n->mPreviousTriangle&&!n->mCollPlatform,"reset contact disposition");
            } else if(is("external")) { InteractAttack attack(n,nullptr,1,false); require(n->stimulate(attack),"external receiver"); hp=n->mHealth; } else n->mStateMachine->transit(n,NAVISTATE_Walk);
            interrupted=true; wait=0;
        }
        if(is("rejected")&&p==P2DemonDropPhase::Knockdown) n->setStateDamaged(); // Explicit rejection setup; no HP/event write.
        bool done=false;
        if(is("fatal")) {
            if(n->mHealth<=1) {require(n->getCurrState()->getID()==NAVISTATE_Dead,"fatal revived");done=++wait>30;}
        } else if(is("interrupt")||is("reset")||is("external")) {
            if(interrupted){require(n->mHealth==hp&&n->getCurrState()->getID()!=36,"late damage/state");done=++wait>90;}
        } else if(n->getCurrState()->getID()==NAVISTATE_Walk) {
            require(is("flick")||sawKnockdown,"missing native bounce");
            require(n->mHealth==(is("positive")?hp-10:hp),"damage result"); done=true;
        }
        if(done){std::printf("PASS DEMON_REGISTERED mode=%s health=%.3f state=%d\n",mode,n->mHealth,n->getCurrState()->getID());std::fflush(stdout);std::_Exit(0);}
        return r;
    }
};
int main(int argc,char** argv) {
    mode=std::getenv("DEMON_FIXTURE_MODE"); if(!mode)mode="positive";
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"room flag");require(pc_window_init("Demon registered state fixture",960,720),"window");
    pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new RegisteredApp());return 0;
}
