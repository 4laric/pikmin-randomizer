#include "pc_p2_cave.h"
#include "pc_p2_preview.h"
#include "pc_p2_purple.h"
#include "pc_bbft.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "MoviePlayer.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include <SDL2/SDL.h>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <fstream>
#include <sstream>
#include <vector>

namespace {
int floorId=0;
std::string token;
bool requested=false;
bool completed=false;
float titleTimer=0;
struct Survivor {int color,maturity;};
void invalid(const char* reason){std::fprintf(stderr,"Invalid P2 cave entry: %s\n",reason);std::abort();}
bool active(){return floorId && !completed && pc_p2_preview_ready() && naviMgr && naviMgr->getNavi() && naviMgr->getNavi()->getCurrState();}
bool safeTime(){return active() && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
    && (!gameflow.mMoviePlayer || !gameflow.mMoviePlayer->mIsActive) && !playerState->mInDayEnd;}
void notice(const char* text){SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION,"Emergence Cave",text,SDL_GL_GetCurrentWindow());}
}
int pc_p2_cave_floor(){return floorId;}
std::string pc_p2_cave_receipt_prefix(){return floorId?"floor"+std::to_string(floorId)+":":"";}
void pc_p2_cave_setup(){
    floorId=0;token.clear();requested=false;completed=false;
    if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-cave-entry.txt");if(!in)return;
    std::string version,extra;int floor,count;float health;
    if(!(in>>version>>token>>floor>>health>>count) || version!="P2_CAVE_ENTRY_1"
        || token.size()!=32 || token.find_first_not_of("0123456789abcdef")!=std::string::npos
        || (floor!=1 && floor!=2) || !std::isfinite(health) || health<=0 || health>1 || count<1 || count>100)
        invalid("header");
    std::vector<Survivor> squad;
    for(int i=0;i<count;++i){Survivor s;if(!(in>>s.color>>s.maturity) || s.color<0 || s.color>3 || s.maturity<0 || s.maturity>2)invalid("Pikmin");squad.push_back(s);}
    if(in>>extra || !in.eof())invalid("trailing data");
    std::vector<Piki*> spawned;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())spawned.push_back(p);}
    if(spawned.size()!=squad.size())invalid("spawn count differs from checkpoint");
    for(size_t i=0;i<squad.size();++i){
        Piki* p=spawned[i];p->setColor(squad[i].color==3?Red:squad[i].color);p->mHappa=squad[i].maturity;
        if(squad[i].color==3){if(!pc_p2_purples_enabled())invalid("Purple assets unavailable");pc_p2_make_purple(p);}
        std::printf("P2_CAVE_RESTORE species=%d maturity=%d\n",squad[i].color,squad[i].maturity);
    }
    Navi* n=naviMgr->getNavi();if(!n || C_NAVI_PARM(n,mHealth)<=0)invalid("captain unavailable");
    n->mHealth=C_NAVI_PARM(n,mHealth)*health;
    floorId=floor;
    std::printf("P2_CAVE_READY floor=%d survivors=%d health=%.9g\n",floor,count,health);std::fflush(stdout);
}
void pc_p2_cave_request(){if(active())requested=true;}
bool pc_p2_cave_checkpoint(bool confirm){
    if(!safeTime())return false;
    Navi* n=naviMgr->getNavi();std::vector<Survivor> squad;
    bool busy=false;
    Iterator it(pikiMgr);CI_LOOP(it){
        Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;
        const int state=p->getState();
        if(state==PIKISTATE_Dying || state==PIKISTATE_Dead) {busy=true;continue;}
        // Do not preserve an actor half-swallowed, converting or becoming a sprout.
        if(state==PIKISTATE_Swallowed || state==PIKISTATE_Bury || state==PIKISTATE_Grow
            || (p->getStickObject() && p->getStickObject()->mObjType!=OBJTYPE_Pellet))busy=true;
        squad.push_back({pc_p2_is_purple(p)?3:p->mColor,p->mHappa});
    }
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())busy=true;}
    if(busy && n->mHealth>1){if(confirm)notice("Pluck all sprouts and whistle Pikmin out of flowers or combat before leaving.");return false;}
    float health=C_NAVI_PARM(n,mHealth)>0?n->mHealth/C_NAVI_PARM(n,mHealth):0;
    health=std::fmax(0.f,std::fmin(1.f,health));
    if(n->mHealth<=1){health=0;squad.clear();}
    const bool failed=squad.empty();
    Suckable* pod=pc_p2_preview_goal();
    if(!pod)return false;
    float dx=n->mSRT.t.x-pod->mSRT.t.x,dz=n->mSRT.t.z-pod->mSRT.t.z;
    if(!failed && (dx*dx+dz*dz>150.f*150.f || n->getCurrState()->getID()!=NAVISTATE_Walk)){
        if(confirm)notice("Return to the Research Pod to descend or leave the cave.");return false;
    }
    if(confirm && !failed){
        const char* action=floorId==1?"Descend":"Leave cave";
        std::string message=std::string(action)+" with all "+std::to_string(squad.size())+" surviving Pikmin?\n"
            "Uncollected treasure stays behind. Your squad and delivered treasure will be saved together.";
        const SDL_MessageBoxButtonData buttons[]={{SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT,0,"Stay"},{SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT,1,action}};
        SDL_MessageBoxData data={SDL_MESSAGEBOX_INFORMATION,SDL_GL_GetCurrentWindow(),"Emergence Cave",message.c_str(),2,buttons,nullptr};int choice=0;
        if(SDL_ShowMessageBox(&data,&choice)!=0 || choice!=1)return false;
    }
    std::ostringstream out;out.precision(9);
    out<<"P2_CAVE_TRANSFER_1\n"<<token<<'\n'<<floorId<<' '<<health<<' '<<squad.size()<<'\n';
    for(const auto& s:squad)out<<s.color<<' '<<s.maturity<<'\n';
    std::string text=out.str();FILE* file=std::fopen("p2-cave-transfer.tmp","wb");
    if(!file)return false;
    bool ok=std::fwrite(text.data(),1,text.size(),file)==text.size() && std::fflush(file)==0;
    if(std::fclose(file)!=0)ok=false;
    if(!ok || std::rename("p2-cave-transfer.tmp","p2-cave-transfer.txt")!=0){if(confirm)notice("Could not prepare the checkpoint. Stay on this floor and retry.");return false;}
    completed=true;
    std::printf("P2_CAVE_TRANSFER floor=%d survivors=%zu health=%.9g failed=%d\n",floorId,squad.size(),health,int(failed));std::fflush(stdout);
    return true;
}
void pc_p2_cave_tick(){
    if(!safeTime()){requested=false;return;}
    gameflow.mWorldClock.setTime(gameflow.mParameters->mStartHour());
    bool attempt=requested;requested=false;
    // Extinction/knockout must not silently restore a fresh squad on the next launch.
    bool any=false;Iterator it(pikiMgr);CI_LOOP(it){if(static_cast<Piki*>(*it)->isAlive()){any=true;break;}}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive()){any=true;break;}}
    if(!any || naviMgr->getNavi()->mHealth<=1)attempt=true;
    // The supervisor owns the next process and the atomic campaign commit.
    // Exit after closing the transfer file; do not run P1 day-end/save teardown.
    if(attempt && pc_p2_cave_checkpoint(true)){std::fflush(nullptr);std::_Exit(42);}
    titleTimer+=gsys->getFrameTime();
    if(titleTimer>=1.f){
        titleTimer=0;
        int count=0,purples=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(p->isAlive()){++count;if(pc_p2_is_purple(p))++purples;}}
        std::string title="Pikipelago - Emergence Cave | Floor "+std::to_string(floorId)+" | "+std::to_string(count)+" Pikmin ("+std::to_string(purples)+" Purple) | "+std::to_string(pc_p2_preview_pokos())
            +" Pokos | F6 at Pod: "+(floorId==1?"descend":"leave cave")+" | Saves at floor boundaries";
        if(SDL_Window* w=SDL_GL_GetCurrentWindow())SDL_SetWindowTitle(w,title.c_str());
    }
}
