// Real engine callback test with injected species/attachments; not controller play.
#include <SDL2/SDL.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "Boss.h"
#include "Pom.h"
#include "PlayerState.h"
#include "Demo.h"
#include "GameStat.h"
#include "Generator.h"
#include "Interactions.h"
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "C:/Users/alari/pikmin-randomizer/scripts/p2_fixture_captain_guard.h"

static void require(bool ok,const char* reason) {
    if(!ok){std::printf("P2_IVORY_BUDGET_FAIL %s\n",reason);std::fflush(nullptr);std::_Exit(1);}
}
static int population() {
    int count=0;Iterator actors(pikiMgr);CI_LOOP(actors){if(static_cast<Piki*>(*actors)->isAlive())++count;}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())++count;}
    return count;
}
static void attach(Piki* p,Pom* flower) {
    require(p->isAlive(),"input dead before capture");
    p->endStickMouth();
    require(flower->mCollInfo,"native flower collision info missing");
    CollPart* slot=flower->mCollInfo->getSphere('slot');
    require(slot&&slot->getChildAt(0),"native flower mouth missing");
    InteractSwallow swallowed(flower,slot->getChildAt(0),0);
    require(p->stimulate(swallowed),"native swallow stimulus refused");
    Vector3f submerged=flower->mSRT.t;submerged.y-=46.f;p->resetPosition(submerged);
    require(p->getStickObject()==flower&&p->isStickToMouth()&&p->getState()==PIKISTATE_Swallowed,"injected native mouth capture failed");
}
class IvoryApp:public PlugPikiApp {
    int frames=0;bool initialized=false;
public:
    int idle() override {
        int result=PlugPikiApp::idle();
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(n){initialized=true;p2_fixture_require_captain(GameStat::orimaDead,
            n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Dead,
            std::getenv("P2_IVORY_FORCE_CAPTAIN_DOWN")?0.f:n->mHealth,frames);}
        else if(initialized){std::puts("P2_FIXTURE_CAPTAIN_DOWN missing_captain outcome=BLOCKED");std::fflush(nullptr);std::_Exit(86);}
        require(++frames<5000,"frame timeout");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!pc_p2_preview_ready()||!n||!n->getCurrState()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive||frames<90)return result;
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        std::vector<Piki*> inputs;Iterator actors(pikiMgr);CI_LOOP(actors){Piki* p=static_cast<Piki*>(*actors);if(p->isAlive())inputs.push_back(p);}
        Pom* flower=nullptr;int bossCount=0;Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);++bossCount;
            std::printf("P2_IVORY_ACTOR type=%d alive=%d uid=%u ivory=%d\n",b->mObjType,int(b->isAlive()),b->mGenerator?b->mGenerator->_70:0,b->mObjType==OBJTYPE_Pom?int(pc_p2_ivory(static_cast<Pom*>(b))):0);
            if(b->isAlive()&&b->mObjType==OBJTYPE_Pom&&pc_p2_ivory(static_cast<Pom*>(b))){require(!flower,"multiple Ivory buds");flower=static_cast<Pom*>(b);}}
        std::printf("P2_IVORY_COUNTS pikis=%zu total=%d bosses=%d bound_flower=%d\n",inputs.size(),population(),bossCount,int(flower!=nullptr));
        require(inputs.size()==20&&population()==20&&flower,"requires twenty initial Pikmin and one Ivory");
        for(Piki* p:inputs)require(pc_p2_species(p)==P2SpeciesRed,"initial squad must be red");
        int w,h,x,y;SDL_Window* window=SDL_GL_GetCurrentWindow();SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
        require(w==960&&h==540,"window dimensions");
        std::printf("P2_IVORY_BASELINE squad=20 window=%dx%d position=%d,%d hp=%.3f method=injected_capture\n",w,h,x,y,n->mHealth);
        // Reserve the real sprout pool synchronously; do not initialize these
        // fixture-only reservations as living bodies. Release all before idle.
        std::vector<Creature*> reserved;
        while(Creature* head=itemMgr->birth(OBJTYPE_Pikihead)){reserved.push_back(head);require(reserved.size()<=1000,"pool unexpectedly unbounded");}
        require(!reserved.empty(),"sprout pool missing");
        attach(inputs[0],flower);
        require(pc_p2_convert_ivory(flower,3)==0,"failed allocation spent slots");
        require(inputs[0]->isAlive()&&!inputs[0]->getStickObject(),"failed allocation lost/captured input");
        require(!inputs[0]->isStickToMouth()&&inputs[0]->getState()==PIKISTATE_Flying&&inputs[0]->mSRT.t.y==flower->mSRT.t.y+50.f&&inputs[0]->mVelocity.y==500.f&&!inputs[0]->mWantToStick,"allocation refusal did not discharge existing body safely");
        for(Creature* head:reserved)itemMgr->kill(head);
        require(population()==20,"pool failure changed living population");
        std::printf("P2_IVORY_ALLOC_FAILURE_PASS reserved=%zu input_alive=1 slots=0 population=20\n",reserved.size());
        pc_p2_make_white(inputs[0]);attach(inputs[0],flower);
        require(pc_p2_convert_ivory(flower,3)==0,"White same-species charged capacity");
        require(!inputs[0]->isAlive()&&population()==20,"White replacement not one-for-one");
        std::puts("P2_IVORY_WHITE_REFUND_PASS births=1 slots=0 population=20");
        attach(inputs[1],flower);require(pc_p2_convert_ivory(flower,3)==1,"ordinary input did not spend one slot");
        require(!inputs[1]->isAlive()&&population()==20,"ordinary conversion not conserved");
        std::puts("P2_IVORY_ORDINARY_PASS births=1 slots=1 population=20");
        pc_p2_make_white(inputs[2]);pc_p2_make_white(inputs[3]);
        for(int i=2;i<=4;++i)attach(inputs[i],flower);
        require(pc_p2_convert_ivory(flower,1)==1,"mixed batch wrong charged slots");
        for(int i=2;i<=4;++i)require(!inputs[i]->isAlive(),"mixed accepted input survives");
        require(population()==20,"mixed batch not conserved");
        std::puts("P2_IVORY_MIXED_PASS births=3 slots=1 population=20");
        pc_p2_make_white(inputs[5]);attach(inputs[5],flower);attach(inputs[6],flower);
        require(pc_p2_convert_ivory(flower,0)==0,"exhausted callback spent slot");
        require(inputs[5]->isAlive()&&inputs[6]->isAlive()&&!inputs[5]->getStickObject()&&!inputs[6]->getStickObject()&&population()==20,"exhausted callback lost input");
        for(int i=5;i<=6;++i)require(!inputs[i]->isStickToMouth()&&inputs[i]->getState()==PIKISTATE_Flying&&inputs[i]->mSRT.t.y==flower->mSRT.t.y+50.f&&inputs[i]->mVelocity.y==500.f&&!inputs[i]->mWantToStick,"overcapacity refusal did not discharge existing body safely");
        require(pc_p2_convert_ivory(flower,0)==0&&population()==20,"repeated callback changed population");
        int heads=0;Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){PikiHeadItem* p=static_cast<PikiHeadItem*>(*sprouts);if(p->isAlive()){++heads;require(pc_p2_species(p)==P2SpeciesWhite,"replacement is not White");}}
        require(heads==5,"expected five genuine White sprouts");
        std::puts("P2_IVORY_EXHAUSTED_PASS births=0 slots=0 inputs_alive=2 population=20");
        std::puts("P2_IVORY_BUDGET_PASS real_callback=1 actual_pool_failure=1 bodies=20 sprouts=5 method=injected_species_and_capture");std::fflush(nullptr);std::_Exit(0);
    }
};
int main(int argc,char**argv){
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires experimental room");
    if(!pc_window_init("Ivory budget acceptance",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new IvoryApp());return 0;
}
