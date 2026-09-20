#define DEMON_DROP_NO_MAIN
#include "p2_demon_drop_runtime.cpp"
#undef DEMON_DROP_NO_MAIN
#include "GameStat.h"
#include <cmath>

// #632 captain-guard predicate mirror (canonical
// scripts/p2_fixture_captain_guard.h sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
// Fixture-only observation guard: never changes captain health or game state.
// Prints P2_FIXTURE_CAPTAIN_DOWN and exits 86 (BLOCKED) on orimaDead,
// Navi Dead state, or nonfinite/HP<=1.

class DemonInterruptionApp final : public PlugPikiApp {
    DemonDropState drop;
    int frames=0,scenario=0,wait=0;
    bool running=false,settling=false;
    float before=0,after=0;
    unsigned oldGeneration=0;
    void stale(Navi* n) {
        const auto phase=drop.policy.phase(); const float hp=n->mHealth;
        require(!drop.policy.bounce(oldGeneration).accepted,"stale bounce");
        require(!drop.policy.animationEnd(oldGeneration,P2DemonDropPhase::Knockdown).accepted,"stale knockdown");
        require(!drop.policy.animationEnd(oldGeneration,P2DemonDropPhase::GetUp).accepted,"stale recovery");
        require(drop.policy.phase()==phase&&n->mHealth==hp,"stale changed state");
    }
public:
    int idle() override {
        int result=PlugPikiApp::idle(); require(++frames<2400,"interruption timeout");
        // #632: captain guard immediately after the engine idle step, BEFORE
        // movie/pause early returns, readiness gates, or observed ticks.
        {
            Navi* guardNavi=naviMgr?naviMgr->getNavi():nullptr;
            if(guardNavi) {
                const bool deadState=guardNavi->getCurrState()&&
                    guardNavi->getCurrState()->getID()==NAVISTATE_Dead;
                const float hp=guardNavi->mHealth;
                if(GameStat::orimaDead||deadState||!std::isfinite(hp)||hp<=1.0f) {
                    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                        frames,hp,int(GameStat::orimaDead),int(deadState));
                    std::fflush(stdout); std::_Exit(86);
                }
            }
        }
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()) return result;
        Navi* n=naviMgr->getNavi();
        if(settling) {
            require(n->mHealth==after,"late damage after cancellation");
            require(n->getCurrState()!=&drop,"old state restored");
            if(++wait<90) return result;
            settling=false; ++scenario;
        }
        if(!running) {
            if(++wait<30) return result;
            before=n->mHealth; drop.complete=false;
            n->releasePikis(); n->resetPosition(Vector3f(0,mapMgr->getMinY(0,100,true)+120,100));
            drop.begin(n); running=true; wait=0;
            if(oldGeneration) stale(n); // Stale previous generation while fresh drop is active.
            std::printf("DEMON_INTERRUPT_START scenario=%d generation=%u health=%.3f\n",scenario,drop.generation,before);
            return result;
        }
        const auto phase=drop.policy.phase();
        const bool interrupt=(scenario==0&&phase==P2DemonDropPhase::Falling)||
            (scenario==1&&phase==P2DemonDropPhase::Knockdown)||
            (scenario==2&&phase==P2DemonDropPhase::Lay)||
            (scenario==3&&phase==P2DemonDropPhase::Falling);
        if(interrupt) {
            oldGeneration=drop.generation;
            if(scenario==3) {
                // Real production reset used by GameCoreSection::initStage, not deletion.
                const int heap=gsys->setHeap(SYSHEAP_App); n->reset(); gsys->setHeap(heap);
            } else n->mStateMachine->transit(n,NAVISTATE_Walk);
            require(drop.policy.phase()==P2DemonDropPhase::Idle,"cleanup did not cancel");
            after=n->mHealth;
            require(scenario==2?after<before:after==before,"interruption damage timing");
            stale(n);
            std::printf("DEMON_INTERRUPT_CANCEL scenario=%d generation=%u health=%.3f production_reset=%d synthetic_stale_probes=1\n",scenario,oldGeneration,after,int(scenario==3));
            running=false; settling=true; wait=0;
        } else if(scenario==4 && drop.complete) {
            require(n->mHealth<before&&drop.damageEvents==2,"fresh generation final damage");
            std::puts("PASS DEMON_DROP_INTERRUPTION falling=1 knockdown=1 recovery=1 production_reset=1 fresh_generation=1 actual_destroy_rebirth=0");
            std::fflush(stdout); std::_Exit(0);
        }
        return result;
    }
};
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1); SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1"); pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"room flag");
    require(pc_window_init("Demon private interruption fixture",960,720),"window init");
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr=new NodeMgr();
    gsys->run(new DemonInterruptionApp()); return 0;
}
