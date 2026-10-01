// Private normal-area acceptance fixture; never shipped as the playtest binary.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "teki.h"
#include "pc_randomizer.h"
#include "pc_p2_enemy.h"
#include "pc_p2_preview.h"
#include "pc_p2_pose_bank.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>

static void require(bool ok,const char* why){if(!ok){std::printf("FAIL snow campaign: %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
class SnowCampaignApp : public PlugPikiApp {
    unsigned frames=0,ticks=0;Teki* selected=nullptr;
public:
    int idle() override {
        int result=PlugPikiApp::idle();require(++frames<2400,"startup timeout");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!pc_randomizer_ready() || !naviMgr || !tekiMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
        Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState())return result;
        if(!selected){
            require(!pc_p2_preview_goal(),"normal area has P2 Pod");
            int dwarfs=0,other=0;Iterator it(tekiMgr);CI_LOOP(it){auto* e=static_cast<Teki*>(*it);
                if(e->mTekiType==TEKI_Chappy){require(pc_p2_enemy_name(e)!=nullptr,"unbound initial dwarf");++dwarfs;selected=e;}
                else {require(!pc_p2_enemy_name(e),"other species replaced");++other;}}
            require(dwarfs>0,"area contains no dwarfs");
            std::printf("SNOW_CAMPAIGN_INITIAL dwarfs=%d other=%d pod=0\n",dwarfs,other);
            auto* late=tekiMgr->newTeki(TEKI_Chappy);require(late && pc_p2_enemy_name(late),"late birth not bound");
            tekiMgr->kill(late);
            auto* reused=tekiMgr->newTeki(TEKI_Frog);require(reused && !pc_p2_enemy_name(reused),"slot reuse retained Snow binding");
            tekiMgr->kill(reused);std::puts("SNOW_CAMPAIGN_LATE_BIRTH_REUSE_PASS");
            Vector3f position=selected->mSRT.t+Vector3f(60,0,60);n->resetPosition(position);
        }
        if(++ticks<30)return result;
        p2pose::Pose geometry;std::string clip;float frame;bool corpse;
        if(!pc_p2_snow_geometry(selected,geometry,clip,frame,corpse)){require(ticks<240,"no actual interpolated draw");return result;}
        require(!geometry.positions.empty()&&!corpse,"invalid live geometry");
        std::printf("SNOW_CAMPAIGN_DRAW positions=%zu clip=%s frame=%f\n",geometry.positions.size(),clip.c_str(),frame);
        // Controlled native animator inputs exercise both death paths and
        // stale velocity while waiting. This is mapping coverage, not combat AI.
        const int motions[]={TekiMotion::Wait1,TekiMotion::WaitAct1,TekiMotion::Move1,TekiMotion::Dead,TekiMotion::Type1};
        const char* expected[]={"wait1","wait1","move1","dead","dead"};
        for(int i=0;i<5;++i){
            selected->startMotion(motions[i]);selected->mVelocity.set(50,0,50);
            const int count=selected->mTekiAnimator->getFrameCount();require(count>1,"motion missing frames");
            const char* name=nullptr;float first,last;
            selected->mTekiAnimator->setCounter(0);
            require(pc_p2_snow_clock(selected,name,first) && std::string(name)==expected[i],"wrong initial clip");
            selected->mTekiAnimator->setCounter(float(count-1)*.75f);
            require(pc_p2_snow_clock(selected,name,last) && std::string(name)==expected[i] && last>first,"motion did not progress");
            std::printf("SNOW_MOTION_PASS motion=%d clip=%s first=%f later=%f\n",motions[i],name,first,last);
        }
        const char* corpseName=nullptr;float corpseFrame;
        require(pc_p2_snow_clock(selected,corpseName,corpseFrame,true) && std::string(corpseName)=="dead","wrong corpse clip");
        std::printf("SNOW_CORPSE_HOLD frame=%f\n",corpseFrame);
        pc_p2_snow_reset();require(!pc_p2_enemy_name(selected),"reset retained binding");
        pc_p2_snow_campaign_setup();require(pc_p2_enemy_name(selected),"normal setup failed to rebind");
        std::puts("PASS snow campaign: initial species filter, late birth, slot reuse, live interpolated draw, reset/rebind, no Pod");
        std::fflush(nullptr);std::_Exit(0);
        return result;
    }
};
int main(int argc,char** argv){
    SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);if(!pc_window_init("Snow campaign fixture",960,640))return 3;
    pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new SnowCampaignApp());return 0;
}
