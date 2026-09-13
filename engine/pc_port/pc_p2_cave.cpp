#include "pc_p2_cave.h"
#include "pc_p2_cave_nav_diagnostics.h"
#include "pc_p2_cave_anchor.h"
#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
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
bool beasts=false;
std::string token;
bool requested=false;
bool completed=false;
float titleTimer=0;
P2CaveAnchor anchor;
Shape* transitionShape=nullptr;
P2CaveNavRate navRate;
unsigned navDrawCalls=0;
bool navMarkerLogged=false;
struct Survivor {int color,maturity;};
void invalid(const char* reason){std::fprintf(stderr,"Invalid P2 cave entry: %s\n",reason);std::abort();}
bool active(){return floorId && !completed && (beasts?pc_p2_preview_cargo_free_ready():pc_p2_preview_ready()) && naviMgr && naviMgr->getNavi() && naviMgr->getNavi()->getCurrState();}
bool safeTime(){return active() && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
    && (!gameflow.mMoviePlayer || !gameflow.mMoviePlayer->mIsActive) && !playerState->mInDayEnd;}

void navigationDiagnostic(){
    if(!floorId || !navRate.due(SDL_GetTicks()))return;
    Navi* n=naviMgr?naviMgr->getNavi():nullptr;
    const int state=n && n->getCurrState()?n->getCurrState()->getID():-1;
    const float x=n?n->mSRT.t.x:0,y=n?n->mSRT.t.y:0,z=n?n->mSRT.t.z:0;
    const float dx=anchor.x-x,dz=anchor.z-z;
    const bool inside=n && anchor.contains(x,y,z),safe=safeTime();
    const bool movie=gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive;
    const char* path=!anchor.enabled?"none":transitionShape?"model":"fallback_ring";
    std::printf("P2_CAVE_NAV seq=%u floor=%d captain=%d x=%.3f y=%.3f z=%.3f heading_rad=%.4f anchor_x=%.3f anchor_y=%.3f anchor_z=%.3f dx=%.3f dz=%.3f horizontal=%.3f vertical=%.3f radius=%.3f inside=%d state=%d walk=%d safe=%d pause=%d ui=%d movie=%d day_end=%d completed=%d pod=%d interaction_eligible=%d marker=%s draws=%u\n",
        navRate.count,floorId,int(n!=nullptr),x,y,z,n?n->mFaceDirection:0,anchor.x,anchor.y,anchor.z,dx,dz,std::hypot(dx,dz),std::fabs(y-anchor.y),anchor.radius,int(inside),state,int(state==NAVISTATE_Walk),int(safe),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(movie),int(playerState && playerState->mInDayEnd),int(completed),int(pc_p2_preview_goal()!=nullptr),int(safe && inside && state==NAVISTATE_Walk),path,navDrawCalls);
    std::fflush(stdout);
}

const char* caveName(){return beasts?"Beasts Cave":"Emergence Cave";}
void notice(const char* text){SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION,caveName(),text,SDL_GL_GetCurrentWindow());}
}
int pc_p2_cave_floor(){return floorId;}
std::string pc_p2_cave_receipt_prefix(){return floorId?"floor"+std::to_string(floorId)+":":"";}
void pc_p2_cave_setup(){
    const char* opt=std::getenv("PIKMIN_CAVE_NAV_DIAGNOSTICS");
    navRate.reset(opt && opt[0]==49 && opt[1]==0);navDrawCalls=0;navMarkerLogged=false;
    floorId=0;beasts=false;token.clear();requested=false;completed=false;titleTimer=0;anchor=P2CaveAnchor{};transitionShape=nullptr;
    if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-cave-entry.txt");if(!in)return;
    std::string version,extra;int floor,count;float health;
    if(!(in>>version>>token>>floor>>health>>count))invalid("header");
    beasts=version=="P2_BEASTS_ENTRY_1";
    if((!beasts && version!="P2_CAVE_ENTRY_1")
        || token.size()!=(beasts?64:32) || token.find_first_not_of("0123456789abcdef")!=std::string::npos
        || (beasts?floor!=2:(floor!=1 && floor!=2)) || !std::isfinite(health) || health<=0 || health>1 || count<1 || count>100)
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
    std::ifstream location("p2-cave-transition.txt");
    if(beasts && !location)invalid("Beasts requires a hole anchor");
    // Reuse the hole geometry validator; this does not change source floorId.
    if(location && !p2_cave_read_anchor(location,beasts?1:floor,anchor))invalid("transition anchor");
    if(anchor.enabled)std::printf("P2_CAVE_ANCHOR kind=%s x=%.3f y=%.3f z=%.3f radius=%.3f\n",anchor.kind.c_str(),anchor.x,anchor.y,anchor.z,anchor.radius);
    std::ifstream visual("p2-cave-visual.txt");
    if(visual){
        std::string header,kind,trailing;
        if(!(visual>>header>>kind) || header!="P2_CAVE_VISUAL_1" || !anchor.enabled
                || kind!=anchor.kind || (visual>>trailing) || !visual.eof())invalid("transition visual");
        const std::string path="courses/pikmin2room/cave_"+kind+".mod";
        transitionShape=gameflow.loadShape(path.c_str(),true);
        if(!transitionShape)invalid("missing transition model");
        for(int i=0;i<transitionShape->mTexAttrCount;++i)
            if(transitionShape->mTexAttrList[i].mTexture)transitionShape->mTexAttrList[i].mTexture->attach();
        std::printf("P2_CAVE_VISUAL_READY kind=%s vertices=%d\n",kind.c_str(),transitionShape->mVertexCount);
    }
    std::printf("P2_CAVE_READY floor=%d survivors=%d health=%.9g\n",floor,count,health);std::fflush(stdout);
}
void pc_p2_cave_request(){if(active())requested=true;}
bool pc_p2_cave_interact(float x,float y,float z){
    if(!safeTime() || !anchor.contains(x,y,z))return false;
    Navi* n=naviMgr->getNavi();
    if(!anchor.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z)
        || n->getCurrState()->getID()!=NAVISTATE_Walk)return false;
    requested=true;return true;
}
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
    const bool nearExit=anchor.enabled?anchor.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z):dx*dx+dz*dz<=150.f*150.f;
    if(!failed && (!nearExit || n->getCurrState()->getID()!=NAVISTATE_Walk)){
        if(confirm)notice(anchor.enabled?"Stand at the hole/geyser to descend or leave the cave.":"Return to the Research Pod to descend or leave the cave.");return false;
    }
    if(confirm && !failed){
        const char* action=(beasts || floorId==1)?"Descend":"Leave cave";
        std::string message=std::string(action)+" with all "+std::to_string(squad.size())+" surviving Pikmin?\n"
            "Uncollected treasure stays behind. Your squad and delivered treasure will be saved together.";
        const SDL_MessageBoxButtonData buttons[]={{SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT,0,"Stay"},{SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT,1,action}};
        SDL_MessageBoxData data={SDL_MESSAGEBOX_INFORMATION,SDL_GL_GetCurrentWindow(),caveName(),message.c_str(),2,buttons,nullptr};int choice=0;
        if(SDL_ShowMessageBox(&data,&choice)!=0 || choice!=1)return false;
    }
    std::ostringstream out;out.precision(9);
    if(beasts)out<<"P2_BEASTS_TRANSFER_1\n"<<token<<"\n2 3 "<<health<<' '<<squad.size()<<'\n';
    else out<<"P2_CAVE_TRANSFER_1\n"<<token<<'\n'<<floorId<<' '<<health<<' '<<squad.size()<<'\n';
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
bool pc_p2_cave_exit_after_checkpoint(){
    if(!completed)return false;
    std::fflush(nullptr);std::_Exit(42);
}
void pc_p2_cave_tick(){
    navigationDiagnostic();
    if(!safeTime()){requested=false;return;}
    gameflow.mWorldClock.setTime(gameflow.mParameters->mStartHour());
    bool attempt=requested;requested=false;
    // Extinction/knockout must not silently restore a fresh squad on the next launch.
    bool any=false;Iterator it(pikiMgr);CI_LOOP(it){if(static_cast<Piki*>(*it)->isAlive()){any=true;break;}}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive()){any=true;break;}}
    if(!any || naviMgr->getNavi()->mHealth<=1)attempt=true;
    // The supervisor owns the next process and the atomic campaign commit.
    // Exit after closing the transfer file; do not run P1 day-end/save teardown.
    if(attempt && pc_p2_cave_checkpoint(true))pc_p2_cave_exit_after_checkpoint();
    titleTimer+=gsys->getFrameTime();
    if(titleTimer>=1.f){
        titleTimer=0;
        int count=0,purples=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(p->isAlive()){++count;if(pc_p2_is_purple(p))++purples;}}
        std::string title=std::string("Pikipelago - ")+caveName()+" | Floor "+std::to_string(floorId)+" | "+std::to_string(count)+" Pikmin ("+std::to_string(purples)+" Purple) | "+std::to_string(pc_p2_preview_pokos())
            +" Pokos | F6 at "+(anchor.enabled?anchor.kind:std::string("Pod"))+": "+((beasts || floorId==1)?"descend":"leave cave")+" | Saves at floor boundaries";
        if(SDL_Window* w=SDL_GL_GetCurrentWindow())SDL_SetWindowTitle(w,title.c_str());
    }
}

void pc_p2_cave_draw_transition(Graphics& gfx){
    if(!active() || !anchor.enabled || !gfx.mCamera)return;
    if(navRate.enabled)++navDrawCalls;
    if(!navMarkerLogged){std::puts("P2_CAVE_MARKER_DRAW");navMarkerLogged=true;}
    // Map post-effects may leave an orthographic projection/material active.
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    if(transitionShape){
        Matrix4f world,view;
        world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),Vector3f(anchor.x,anchor.y,anchor.z));
        gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
        transitionShape->updateAnim(gfx,view,nullptr,nullptr);
        transitionShape->drawshape(gfx,*gfx.mCamera,nullptr);
        return;
    }
    // Honest engineering marker, not an imported P2 actor. Ring + down/up arrow.
    // The caller is a world-overlay boundary and resets the matrix for subsequent UI.
    const Colour oldColour=gfx.mPrimaryColour;
    const Colour oldAux=gfx.mAuxiliaryColour;
    const int oldBlend=gfx.setCBlending(BLEND_Alpha);
    Texture* oldTexture=gfx.mActiveTexture[0];
    const bool oldLight=gfx.setLighting(false,nullptr);
    const float oldWidth=gfx.setLineWidth(3.f);
    gfx.useTexture(nullptr,0);gfx.useMatrix(gfx.mCamera->mLookAtMtx,0);
    gfx.setColour(anchor.kind=="hole"?Colour(255,185,65,255):Colour(75,235,255,255),true);
    const float y=anchor.y+4.f;
    for(int i=0;i<32;++i){
        const float a=i*6.28318530718f/32.f,b=(i+1)*6.28318530718f/32.f;
        gfx.drawLine(Vector3f(anchor.x+std::cos(a)*anchor.radius,y,anchor.z+std::sin(a)*anchor.radius),
                     Vector3f(anchor.x+std::cos(b)*anchor.radius,y,anchor.z+std::sin(b)*anchor.radius));
    }
    const float tip=anchor.kind=="hole"?y+8.f:y+75.f;
    const float tail=anchor.kind=="hole"?y+75.f:y+8.f;
    const float wing=anchor.kind=="hole"?tip+20.f:tip-20.f;
    gfx.drawLine(Vector3f(anchor.x,tail,anchor.z),Vector3f(anchor.x,tip,anchor.z));
    gfx.drawLine(Vector3f(anchor.x-18.f,wing,anchor.z),Vector3f(anchor.x,tip,anchor.z));
    gfx.drawLine(Vector3f(anchor.x+18.f,wing,anchor.z),Vector3f(anchor.x,tip,anchor.z));
    gfx.setLineWidth(oldWidth);gfx.setColour(oldColour,true);gfx.mAuxiliaryColour=oldAux;
    gfx.setCBlending(oldBlend);gfx.useTexture(oldTexture,0);gfx.setLighting(oldLight,nullptr);
}
