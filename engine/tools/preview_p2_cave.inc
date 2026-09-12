// Lifecycle fixture only: synthetic casualty/maturity/conversion and real
// native restoration, collection hook and transfer writer. Not transport AI.
#include "pc_p2_cave.h"
#include "GoalItem.h"
#include <fstream>
static void caveFixture(Navi* n) {
    static int ticks=0;
    if(++ticks<90)return;
    for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
    std::ifstream entry("p2-cave-entry.txt");std::string version,token;int floor,count;float health;
    require(bool(entry>>version>>token>>floor>>health>>count),"cave fixture input");
    int expected[4][3]={},actual[4][3]={};
    for(int i=0;i<count;++i){int color,maturity;require(bool(entry>>color>>maturity),"cave fixture squad");++expected[color][maturity];}
    std::vector<Piki*> pikis;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;pikis.push_back(p);++actual[pc_p2_is_purple(p)?3:p->mColor][p->mHappa];}
    require(pikis.size()==size_t(count),"cave restored count");
    for(int c=0;c<4;++c)for(int h=0;h<3;++h)require(actual[c][h]==expected[c][h],"cave restored species/maturity");
    require(std::fabs(n->mHealth/C_NAVI_PARM(n,mHealth)-health)<0.001f,"cave restored captain health");
    std::puts("P2_CAVE_RESTORE_PASS species maturity health exact");
    capture("p2-cave-entry.ppm");
    if(FILE* extinct=std::fopen("p2-cave-extinction.txt","r")){
        std::fclose(extinct);for(Piki* p:pikis)p->kill(false);
        std::puts("P2_CAVE_EXTINCTION_INJECTED awaiting production tick");std::fflush(stdout);return;
    }
    if(FILE* restore=std::fopen("p2-cave-restore-only.txt","r")){
        std::fclose(restore);std::puts("PASS cave repeated restore; no checkpoint written");std::fflush(stdout);std::_Exit(0);
    }
    gameflow.mPauseAll=true;require(!pc_p2_cave_checkpoint(false),"paused cave transitioned");gameflow.mPauseAll=false;
    Suckable* pod=pc_p2_preview_goal();require(pod!=nullptr,"cave Pod missing");
    Vector3f position=n->mSRT.t;
    n->resetPosition(Vector3f(pod->mSRT.t.x+300,pod->mSRT.t.y,pod->mSRT.t.z));
    require(!pc_p2_cave_checkpoint(false),"distant cave transitioned");n->resetPosition(position);
    if(floor==1){
        require(pikis.size()==20,"first fixture squad");pikis.back()->kill(false);
        pikis[0]->mHappa=Flower;pikis[1]->mHappa=Bud;n->mHealth=C_NAVI_PARM(n,mHealth)*.625f;
    } else {
        require(pikis.size()==19,"casualty was restored for free");
        // Conversion gameplay is tested separately by preview_p2_purple.inc.
        for(size_t i=0;i<10;++i)pc_p2_make_purple(pikis[i]);
    }
    require(pc_p2_preview_deliver(pc_p2_preview_treasure()),"cave collection hook failed");
    n->resetPosition(Vector3f(pod->mSRT.t.x+50,pod->mSRT.t.y,pod->mSRT.t.z));
    n->mStateMachine->transit(n,NAVISTATE_Walk);
    require(pc_p2_cave_checkpoint(false),"cave boundary checkpoint failed");
    require(!pc_p2_cave_checkpoint(false),"duplicate cave transition accepted");
    std::puts("PASS cave: restoration, pause/distance guards, synthetic survivors, collection hook, single transfer");
    std::fflush(nullptr);std::_Exit(42);
}
