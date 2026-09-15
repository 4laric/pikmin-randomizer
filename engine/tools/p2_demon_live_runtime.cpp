#include <SDL2/SDL.h>
#include "App.h"
#include "Node.h"
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
#include "GameCoreSection.h"
#include "Section.h"
#include "Creature.h"
#include "Collision.h"
#include "pc_p2_demon_bridge.h"
#include "pc_p2_demon_escape_state.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

static const char* mode="capture";
static void require(bool b,const char* s){if(!b){std::printf("FAIL DEMON_LIVE %s\n",s);std::fflush(stdout);std::_Exit(1);}}
static float zero_random(void*) { return 0.0f; }
static GameCoreSection* findCore(CoreNode* n,int d=0){if(!n||d>20)return nullptr;if(auto* c=dynamic_cast<GameCoreSection*>(n))return c;for(auto* x=n->Child();x;x=x->Next())if(auto* c=findCore(x,d+1))return c;return nullptr;}
static bool is(const char* s){return std::strcmp(mode,s)==0;}

class FixtureOwner final : public Creature {
public:
    FixtureOwner()
        : Creature(nullptr)
    {
    }

    void refresh(Graphics&) override { }
    void doKill() override { }
};
class DemonLiveApp final : public PlugPikiApp {
    int ticks=0,phase=0;
    FixtureOwner owner, replacement;
    CollPart mouth{}, replacementMouth{};
    void setupOwner(Creature& o,CollPart& p,float x) {
        o.mStickListHead=nullptr; o.mSRT.t.set(x,200,100); o.mSRT.s.set(1,1,1); o.mSRT.r.set(0,0,0);
        p.mPartType=PART_BoundSphere; p.mRadius=20; p.mCentre.set(x,200,100); p.mJointMatrix.makeIdentity();
    }
    bool capture(Navi* n,std::uint64_t token=1){return pc_demon_capture(n,&owner,&mouth,token,0);}
public:
    int idle() override {
        int r=PlugPikiApp::idle();require(++ticks<1000,"timeout");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return r;}
        if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()||ticks<30)return r;
        Navi* n=naviMgr->getNavi();
        if(phase==0){
            static_assert(NAVISTATE_DemonDrop==36&&NAVISTATE_DemonEscape==37&&NAVISTATE_Count==38,"PC state registry");
            n->mStateMachine->transit(n,NAVISTATE_Walk); n->releasePikis(); setupOwner(owner,mouth,0); setupOwner(replacement,replacementMouth,300);
            require(capture(n),"capture admission");require(n->isStickToMouth()&&n->getStickObject()==&owner&&pc_demon_bound(n),"live mouth link");
            mouth.mCentre.set(80,220,100); phase=1;return r;
        }
        if(phase==1){
            // Native Creature::updateStick follows the real CollPart, not a cached pose.
            require(n->mSRT.t.x>10,"mouth follow");
            if(is("ownerlost")){pc_demon_owner_lost(1);require(!n->isStickTo()&&!pc_demon_bound(n),"owner lost detach");std::puts("PASS DEMON_LIVE ownerlost");std::_Exit(0);}
            if(is("replacement")){n->endStickMouth();n->startStickMouth(&replacement,&replacementMouth);pc_demon_release(n);require(n->getStickObject()==&replacement&&n->isStickToMouth(),"replacement preserved");n->endStickMouth();std::puts("PASS DEMON_LIVE replacement");std::_Exit(0);}
            if(is("reset")){n->reset();require(!n->isStickTo()&&!pc_demon_bound(n),"reset detach");std::puts("PASS DEMON_LIVE reset");std::_Exit(0);}
            if(is("stageexit")){auto* c=findCore(gameflow.mGameSection);require(c,"core");c->exitStage();require(!n->isStickTo()&&!pc_demon_bound(n),"scene detach");std::puts("PASS DEMON_LIVE stageexit");std::_Exit(0);}
            if(is("forced")){require(pc_demon_forced_release(n,10,200),"forced damaging admission");require(n->getCurrState()->getID()==NAVISTATE_DemonDrop&&n->mVelocity.y==-400,"forced damage velocity");std::puts("PASS DEMON_LIVE forced");std::_Exit(0);}
            if(is("refusal")){n->mHealth=1;require(!pc_demon_forced_release(n,10,200)&&!n->isStickTo(),"forced refusal detached");std::puts("PASS DEMON_LIVE refusal");std::_Exit(0);}
            n->mVelocity.set(7,19,-3);for(int i=0;i<6;++i)pc_demon_escape_tick(n,true,zero_random,nullptr);
            require(n->getCurrState()->getID()==NAVISTATE_DemonEscape&&n->mVelocity.y==19&&!n->isStickTo(),"escape preserves velocity");require(!n->isAtari(),"escape atari off");phase=2;return r;
        }
        if(phase==2){n->bounceCallback();require(n->getCurrState()->getID()==NAVISTATE_Walk&&n->isAtari(),"escape atari restored");std::puts("PASS DEMON_LIVE capture_escape");std::_Exit(0);}
        return r;
    }
};
int main(int argc,char** argv){mode=std::getenv("DEMON_FIXTURE_MODE");if(!mode)mode="capture";SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"room");require(pc_window_init("Demon live fixture",960,720),"window");pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new DemonLiveApp());return 0;}