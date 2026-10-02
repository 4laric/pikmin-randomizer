// #1154: ordinary surface/floor captain movement and production F6 dialogs.
// The supervisor owns OS-dialog confirmation and a <=60 second child deadline.
// No actor writes, direct cave requests, checkpoint calls or transfer writes.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "Generator.h"
#include "MapMgr.h"
#include "Collision.h"
#include "Shape.h"
#include "PlayerState.h"
#include "GameStat.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_cave.h"
#include "pc_p2_cave_route_policy.h"
#include "pc_p2_species.h"
// The fixture builder supplies the canonical root scripts include directory.
// An explicit header override also supports isolated Linux source packages.
#ifdef P2_FIXTURE_CAPTAIN_GUARD_HEADER
#include P2_FIXTURE_CAPTAIN_GUARD_HEADER
#else
#include "p2_fixture_captain_guard.h"
#endif
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <set>
#include <thread>
#include <utility>

namespace {
SDL_Joystick* pad=nullptr;
P2CaveSurfaceRoute route;
bool roomRoute=false;
bool fullParty=false,wfg=false,acquire=false;
struct BodyTarget { unsigned uid;int species;float x,y,z; };
std::vector<BodyTarget> bodies;
std::vector<std::pair<float,float>> floorPath;
void require(bool value,const char* why) {
    if(!value){std::printf("FAIL P2_CAVE_ROUTE_RUNTIME %s\n",why);std::fflush(nullptr);std::_Exit(1);}
}
bool transferExists() {
    std::error_code error;
    bool exists=std::filesystem::exists(roomRoute?"p2-cave-transfer.txt":"p2-cave-surface-transfer.txt",error);
    require(!error,"transfer existence query failed");return exists;
}
void controls(int x=0,int y=0,bool whistle=false,bool dismiss=false,bool action=false) {
    require(SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,x*256)==0,"left X input");
    require(SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,-y*256)==0,"left Y input");
    require(SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,whistle?1:0)==0,"whistle input");
    require(SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_X,dismiss?1:0)==0,"dismiss input");
    require(SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,action?1:0)==0,"throw/pluck input");
    SDL_JoystickUpdate();
}
void f6(const char* kind) {
    for(int down=1;down>=0;--down){
        SDL_Event event{};event.type=down?SDL_KEYDOWN:SDL_KEYUP;
        event.key.windowID=SDL_GetWindowID(SDL_GL_GetCurrentWindow());
        event.key.state=down?SDL_PRESSED:SDL_RELEASED;
        event.key.keysym.scancode=SDL_SCANCODE_F6;event.key.keysym.sym=SDLK_F6;
        require(SDL_PushEvent(&event)==1,"F6 SDL event rejected");
    }
    std::printf("P2_CAVE_ROUTE_F6 where=%s path=SDL_event confirmation=external_native_dialog\n",kind);std::fflush(nullptr);
}
void snapshot(Navi* n,const char* label) {
    int total=0,red=0;Iterator it(pikiMgr);
    CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
        require(std::isfinite(p->mSRT.t.x)&&std::isfinite(p->mSRT.t.y)&&std::isfinite(p->mSRT.t.z),"nonfinite squad position");
        int species=pc_p2_species(p);if(species==P2SpeciesRed)++red;
        require(species>=0&&species<=(fullParty?P2SpeciesWhite:P2SpeciesRed)&&int(p->mHappa)>=0&&int(p->mHappa)<=2,"snapshot species/maturity invalid");
        std::printf("P2_CAVE_ROUTE_LIVE label=%s actor=%d species=%d maturity=%d mode=%d state=%d x=%.6f y=%.6f z=%.6f\n",label,total++,species,int(p->mHappa),int(p->mMode),p->getState(),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);
    }
    require(total>0&&total<=100&&(fullParty||red==total),"live survivors invalid");
    if(fullParty)require(total==int(route.party.squad.size()),"full living party changed at durable snapshot");
    require(C_NAVI_PARM(n,mHealth)>0,"captain health denominator");
    std::printf("P2_CAVE_ROUTE_SNAPSHOT label=%s survivors=%d red=%d hp=%.9g health=%.9g x=%.6f y=%.6f z=%.6f\n",label,total,red,n->mHealth,n->mHealth/C_NAVI_PARM(n,mHealth),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);std::fflush(nullptr);
}
void verifyIncoming(Navi* n,bool floor=true) {
    if(floor){require(pc_p2_cave_floor()==route.party.floor,"native floor differs from entry");
        require(pc_p2_cave_boundary_token()==route.party.token,"native token differs from entry");}
    require(C_NAVI_PARM(n,mHealth)>0,"captain health denominator");
    const float health=n->mHealth/C_NAVI_PARM(n,mHealth);
    require(std::isfinite(health)&&std::fabs(health-route.party.health)<=0.00001f,"restored captain health differs from entry");
    std::map<std::pair<int,int>,int> expected,actual;
    for(const auto& p:route.party.squad)++expected[{p.species,p.maturity}];
    Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++actual[{pc_p2_species(p),int(p->mHappa)}];}
    require(actual==expected,"restored live roster differs from actual entry");
    if(fullParty){
        size_t index=0;Iterator ordered(pikiMgr);CI_LOOP(ordered){auto* p=static_cast<Piki*>(*ordered);if(!p||!p->isAlive())continue;
            require(index<route.party.squad.size()&&pc_p2_species(p)==route.party.squad[index].species&&int(p->mHappa)==route.party.squad[index].maturity,"incoming actor order differs from checkpoint");++index;}
        require(index==route.party.squad.size(),"incoming ordered party count");
    }
}
class CaveRouteApp final:public PlugPikiApp {
    bool captainSeen=false;int ticks=0,ready=0,phase=0,wait=0;Vector3f origin;
    size_t floorPoint=0;
    size_t bodyPoint=0;
    int acquisitionPhase=0,acquisitionTicks=0;
    bool sawFlying=false,sawHeld=false,sawHead=false,sawPluckA=false,sawNuku=false;
    std::set<const Piki*> flyingActors;
    void followers(Navi* n,const char* label,bool exit=false) {
        if(!fullParty)return;
        const float captainDistance=std::hypot(n->mSRT.t.x-origin.x,n->mSRT.t.z-origin.z);
        int count=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
            const float distance=std::hypot(p->mSRT.t.x-n->mSRT.t.x,p->mSRT.t.z-n->mSRT.t.z);
            const float progress=std::hypot(p->mSRT.t.x-origin.x,p->mSRT.t.z-origin.z);
            std::printf("P2_CAVE_ROUTE_FOLLOWER label=%s actor=%d species=%d mode=%d state=%d distance=%.6f progress=%.6f captain_progress=%.6f\n",label,count++,pc_p2_species(p),int(p->mMode),p->getState(),distance,progress,captainDistance);
            require(std::isfinite(distance)&&std::isfinite(progress)&&std::isfinite(p->mSRT.t.y),"nonfinite physical follower position");
            if(exit){require(distance<=180&&std::fabs(p->mSRT.t.y-n->mSRT.t.y)<=100,"full party stranded outside physical captain reach");require(p->mMode==PikiMode::FormationMode,"exit follower is not in ordinary formation");require(progress>=std::fmax(60.f,captainDistance*.5f),"living follower did not make physical route progress");}
        }
        require(count==int(route.party.squad.size()),"full follower count differs from incoming party");std::fflush(nullptr);
    }
    bool moveTo(Navi* n,float x,float z,int speed=65) {
        float dx=x-n->mSRT.t.x,dz=z-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);
        if(d<10){controls();return true;}
        require(n->controlCamera()!=nullptr,"acquisition camera missing");
        const auto& a=n->controlCamera()->mViewXAxis;
        controls(int(std::lround(speed*(dx*a.x+dz*a.z)/d)),int(std::lround(speed*(dx*a.z-dz*a.x)/d)));
        return false;
    }
    bool acquisitionTick(Navi* n) {
        if(bodyPoint==bodies.size())return false;
        const auto& body=bodies[bodyPoint];
        int living=0,total=0;Iterator pikis(pikiMgr);
        CI_LOOP(pikis){auto* p=static_cast<Piki*>(*pikis);if(!p||!p->isAlive())continue;
            ++total;if(pc_p2_species(p)==body.species)++living;
            if(p->getState()==PIKISTATE_Flying && flyingActors.insert(p).second){sawFlying=true;std::printf("P2_WFG_WITNESS species=%d stage=flying actor=%p tick=%d\n",body.species,(void*)p,ticks);}
            Creature* stuck=p->getStickObject();
            const bool held=stuck&&stuck->mObjType==OBJTYPE_Pom&&stuck->mGenerator&&stuck->mGenerator->_70==body.uid;
            if(held&&!sawHeld){require(flyingActors.count(p)!=0,"actual Pom input was not the observed flying actor");sawHeld=true;std::printf("P2_WFG_WITNESS species=%d stage=held actor=%p uid=%u tick=%d\n",body.species,(void*)p,body.uid,ticks);}
            if(!held&&p->getState()!=PIKISTATE_Flying)flyingActors.erase(p);
        }
        PikiHeadItem* head=nullptr;Iterator heads(itemMgr->getPikiHeadMgr());
        CI_LOOP(heads){auto* h=static_cast<PikiHeadItem*>(*heads);if(h&&h->isAlive()&&pc_p2_species(h)==body.species){head=h;break;}}
        if(head && !sawHead){require(sawFlying&&sawHeld,"typed output without observed throw/contact");sawHead=true;std::printf("P2_WFG_WITNESS species=%d stage=typed_sprout actor=%p x=%.6f y=%.6f z=%.6f tick=%d\n",body.species,(void*)head,head->mSRT.t.x,head->mSRT.t.y,head->mSRT.t.z,ticks);}
        if(sawHead&&sawPluckA&&n->getCurrState()->getID()==NAVISTATE_Nuku&&!sawNuku){sawNuku=true;std::printf("P2_WFG_WITNESS species=%d stage=native_Navi_Nuku tick=%d\n",body.species,ticks);}
        if(living>0 && sawHead && !head){
            require(sawPluckA&&sawNuku,"living typed replacement without observed ordinary SDL A and native Navi Nuku");
            require(total==20,"natural acquisition changed living party total");
            snapshot(n,body.species==3?"natural_purple_plucked":"natural_white_plucked");
            std::printf("P2_WFG_WITNESS species=%d stage=living_after_SDL_A ordinary_pluck=1 tick=%d\n",body.species,ticks);std::fflush(nullptr);
            ++bodyPoint;acquisitionPhase=0;acquisitionTicks=0;sawFlying=sawHeld=sawHead=sawPluckA=sawNuku=false;flyingActors.clear();return true;
        }
        ++acquisitionTicks;require(acquisitionTicks<900,"ordinary throw/contact/pluck did not complete");
        if(sawHead){
            require(head!=nullptr,"typed output disappeared without living replacement");
            if(moveTo(n,head->mSRT.t.x,head->mSRT.t.z,40)){
                const bool action=acquisitionTicks%12<4;
                if(action)sawPluckA=true;
                controls(0,0,false,false,action);
            }
        }else if(acquisitionPhase==0){
            // Approach from the south. Final ordinary movement faces the bud;
            // camera-relative stick conversion never writes the captain angle.
            if(moveTo(n,body.x,body.z-130)){acquisitionPhase=1;acquisitionTicks=0;}
        }else if(acquisitionPhase==1){
            // A separate northward SDL step supplies the final throw heading.
            if(moveTo(n,body.x,body.z-100,35)){acquisitionPhase=2;acquisitionTicks=0;}
        }else{
            // Release A between attempts so production Navi grab/throw sees
            // genuine button edges. No direct callback or actor state changes.
            controls(0,0,acquisitionTicks<24,false,acquisitionTicks>=24&&acquisitionTicks%30<5);
        }
        if(ticks%30==0){std::printf("P2_WFG_FRAME tick=%d species=%d phase=%d flying=%d held=%d head=%d living=%d total=%d\n",ticks,body.species,acquisitionPhase,int(sawFlying),int(sawHeld),int(sawHead),living,total);std::fflush(nullptr);}
        return true;
    }
    void floorTick(Navi* n) {
        if(phase==0){
            if(pc_p2_cave_floor()==0||++ready<30)return;
            verifyIncoming(n);require(!transferExists(),"stale floor transfer exists");
            require(!route.entrance.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z),"captain starts inside floor exit");
            origin=n->mSRT.t;snapshot(n,"floor_entry");followers(n,"floor_entry");controls();
            std::printf("P2_CAVE_ROUTE_FLOOR_READY floor=%d token=%s anchor=%.3f,%.3f,%.3f captain_only=%d full_squad_requested=%d carry_route=0 treasure_completion=0 confirmation=external_native_dialog\n",route.party.floor,route.party.token.c_str(),route.entrance.x,route.entrance.y,route.entrance.z,int(!fullParty),int(fullParty));
            // Ordinary disband keeps the restored followers west of the water
            // while this explicitly captain-only route tests the boundary.
            if(fullParty){phase=8;wait=0;}else{controls(0,0,false,true);std::puts("P2_CAVE_ROUTE_DISBAND path=SDL_button_X");phase=7;}
            std::fflush(nullptr);return;
        }
        require(pc_p2_cave_floor()==route.party.floor&&pc_p2_cave_boundary_token()==route.party.token,"floor identity changed");
        if(phase==7){controls();phase=1;return;}
        if(phase==8){
            if(acquire&&acquisitionTick(n))return;
            controls(0,0,true);if(++wait>=30){controls();phase=1;wait=0;}return;
        }
        if(phase==1){
            const auto& target=floorPath[floorPoint];
            const float dx=target.first-n->mSRT.t.x,dz=target.second-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);
            if(d<10){
                controls();std::printf("P2_CAVE_ROUTE_FLOOR_WAYPOINT floor=%d point=%zu x=%.6f y=%.6f z=%.6f\n",route.party.floor,floorPoint,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);std::fflush(nullptr);
                if(++floorPoint==floorPath.size()){phase=3;wait=0;}
            }else{
                require(n->controlCamera()!=nullptr,"floor movement camera missing");const Vector3f& a=n->controlCamera()->mViewXAxis;
                controls(int(std::lround(65*(dx*a.x+dz*a.z)/d)),int(std::lround(65*(dx*a.z-dz*a.x)/d)));
            }
        }else if(phase==3){
            ++wait;if(wait<30){controls(0,0,fullParty);return;}
            controls();if(fullParty&&(wait<40||n->getCurrState()->getID()!=NAVISTATE_Walk))return;
            require(route.entrance.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z),"captain outside floor exit");
            require(!transferExists(),"floor transfer preceded F6");snapshot(n,"floor_before_F6");
            if(fullParty){
                int total=0,purple=0,white=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive()){++total;purple+=pc_p2_species(p)==3;white+=pc_p2_species(p)==4;}}
                require(total==int(route.party.squad.size()),"full party lost on traversal");
                if(wfg)require(purple>0&&white>0,"natural acquisition did not retain living P/W");
                followers(n,"floor_exit",true);
                std::printf("P2_CAVE_ROUTE_FULL_PARTY survivors=%d purple=%d white=%d disband=0 acquisition=%d\n",total,purple,white,int(acquire));
            }
            const float dx=n->mSRT.t.x-origin.x,dz=n->mSRT.t.z-origin.z;
            require(dx*dx+dz*dz>120*120,"insufficient ordinary floor movement");
            std::printf("P2_CAVE_ROUTE_DIALOG_READY floor=%d distance=%.6f captain_only=%d full_squad_requested=%d carry_route=0 treasure_completion=0 actor_writes=0 direct_checkpoint=0\n",route.party.floor,std::sqrt(dx*dx+dz*dz),int(!fullParty),int(fullParty));std::fflush(nullptr);
            f6("floor_exit");phase=5;wait=0;
        }else if(phase==5){controls();require(++wait<120,"floor F6 cancelled or refused");}
        if(ticks%60==0){std::printf("P2_CAVE_ROUTE_FLOOR_FRAME floor=%d tick=%d phase=%d point=%zu x=%.3f y=%.3f z=%.3f hp=%.3f\n",route.party.floor,ticks,phase,floorPoint,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mHealth);std::fflush(nullptr);}
    }
public:
    int idle() override {
        int result=PlugPikiApp::idle();
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        bool initialized=n&&n->getCurrState();
        if(initialized)captainSeen=true;
        bool forced=std::getenv("P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN")!=nullptr;
        if(captainSeen&&!initialized)p2_fixture_require_captain(true,true,0,ticks);
        if(initialized){
            p2_fixture_require_captain(GameStat::orimaDead,
                naviMgr->isNaviDead(n)||n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,ticks);
            if(forced){
                std::printf("P2_CAVE_ROUTE_NEGATIVE_INITIALIZED tick=%d state=%d actual_hp=%.9g after_engine_idle=1 actor_writes=0\n",ticks,n->getCurrState()->getID(),n->mHealth);std::fflush(nullptr);
                p2_fixture_require_captain(true,true,0,ticks);
            }
        }
        ++ticks;
        // No demo-flag writes and no automatic movie skip: original lifecycle.
        if(!initialized||!pikiMgr||!mapMgr||!playerState)return result;
        if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive||(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive))return result;
        require(!pc_settings_get_debug_keys(),"debug keys must remain disabled");
        // A held whistle enters a non-Walk captain state. Keep advancing that
        // input phase so its release happens through SDL instead of deadlocking.
        if(n->getCurrState()->getID()!=NAVISTATE_Walk && (roomRoute?(phase!=7&&phase!=8&&!(fullParty&&phase==3)):(phase!=2&&!(fullParty&&phase==4)))){
            if(ticks%60==0){std::printf("P2_CAVE_ROUTE_WAIT tick=%d phase=%d captain_state=%d\n",ticks,phase,n->getCurrState()->getID());std::fflush(nullptr);}
            return result;
        }
        require(std::isfinite(n->mSRT.t.x)&&std::isfinite(n->mSRT.t.y)&&std::isfinite(n->mSRT.t.z),"nonfinite captain position");
        if(roomRoute){floorTick(n);return result;}
        if(phase==0){
            if(!pc_p2_cave_surface_route_active()||++ready<30)return result;
            if(fullParty){verifyIncoming(n,false);origin=n->mSRT.t;followers(n,"surface_entry");}
            require(flowCont.mCurrentStage&&!std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"wrong surface stage");
            require(!gameflow.mIsChallengeMode&&!pc_pikipelago_room_preview(),"wrong lifecycle");
            require(mapMgr->mMapModel&&mapMgr->mMapModel->mTriCount==5332,"imported face count changed");
            require(mapMgr->mMapModel->mTriList[673].mMapCode!=mapMgr->mMapModel->mTriList[4914].mMapCode,"duplicate slip overlay collapsed");
            if(route.entrance.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z)){
                require(!transferExists(),"stale reentry transfer exists");snapshot(n,"surface_return");
                controls();phase=6;return result;
            }
            require(!transferExists(),"stale transfer exists");origin=n->mSRT.t;snapshot(n,"outside");controls();f6("outside");phase=1;wait=0;
        }else if(phase==6){
            // A returned checkpoint starts at the entrance. Walk out through
            // ordinary SDL input before repeating the distant refusal/reentry.
            const float dx=route.entrance.x-n->mSRT.t.x,dz=1350-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);
            if(d<10){
                require(!route.entrance.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z),"reentry approach still inside entrance");
                controls();origin=n->mSRT.t;snapshot(n,"outside_reentry");f6("outside_reentry");phase=1;wait=0;
            }else{
                require(n->controlCamera()!=nullptr,"reentry movement camera missing");const Vector3f& a=n->controlCamera()->mViewXAxis;
                controls(int(std::lround(65*(dx*a.x+dz*a.z)/d)),int(std::lround(65*(dx*a.z-dz*a.x)/d)));
            }
        }else if(phase==1){
            require(!transferExists(),"distant F6 wrote transfer");
            if(++wait>=30){std::puts("P2_CAVE_ROUTE_DISTANT_REFUSED observed_ticks=30 transfer=absent");phase=2;wait=0;}
        }else if(phase==2){
            controls(0,0,true);if(++wait>=60){controls();phase=3;}
        }else if(phase==3){
            const float dx=route.entrance.x-n->mSRT.t.x,dz=route.entrance.z-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);
            if(d<10&&route.entrance.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z)){
                controls();phase=4;wait=0;
            }else{
                require(n->controlCamera()!=nullptr,"movement camera missing");const Vector3f& a=n->controlCamera()->mViewXAxis;
                require(d>0,"entrance height unreachable");controls(int(std::lround(65*(dx*a.x+dz*a.z)/d)),int(std::lround(65*(dx*a.z-dz*a.x)/d)));
            }
        }else if(phase==4){
            ++wait;if(wait<30){controls(0,0,fullParty);return result;}
            controls();if(fullParty&&(wait<40||n->getCurrState()->getID()!=NAVISTATE_Walk))return result;
            require(route.entrance.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z),"captain drifted outside entrance");
            float dx=n->mSRT.t.x-origin.x,dz=n->mSRT.t.z-origin.z;
            require(dx*dx+dz*dz>120*120,"insufficient ordinary movement");
            require(!transferExists(),"transfer preceded inside F6");snapshot(n,"inside_before_F6");
            followers(n,"surface_inside_before_F6",true);
            std::printf("P2_CAVE_ROUTE_DIALOG_READY distance=%.6f faces=5332 actor_writes=0 direct_checkpoint=0\n",std::sqrt(dx*dx+dz*dz));std::fflush(nullptr);
            f6("inside");phase=5;wait=0;
        }else if(phase==5){
            // Production normally exits42 from the actual modal confirmation.
            // A cancelled/refused dialog is never retried or treated as success.
            controls();require(++wait<120,"inside F6 cancelled or refused");
        }
        if(ticks%60==0){std::printf("P2_CAVE_ROUTE_FRAME tick=%d phase=%d x=%.3f y=%.3f z=%.3f hp=%.3f\n",ticks,phase,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mHealth);std::fflush(nullptr);}
        return result;
    }
};
}
int main(int argc,char** argv){
    // Backstop remains live while SDL_ShowMessageBox blocks the engine thread.
    // The external supervisor still owns child-only termination and run records.
    std::thread([]{std::this_thread::sleep_for(std::chrono::seconds(60));std::puts("FAIL P2_CAVE_ROUTE_RUNTIME wall_timeout60");std::fflush(nullptr);std::_Exit(2);}).detach();
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("PIKMIN_DEBUG_KEYS","0",1);pc_bbft_init(argc,argv);
    if(const char* option=std::getenv("P2_CAVE_ROUTE_FULL_PARTY")){
        require(std::strcmp(option,"1")==0,"invalid full party opt-in");fullParty=true;
    }
    if(const char* option=std::getenv("P2_CAVE_ROUTE_ACQUIRE")){
        require(std::strcmp(option,"1")==0&&fullParty,"fresh acquisition requires explicit full party opt-in");acquire=true;
    }
    roomRoute=pc_pikipelago_room_preview();
    if(roomRoute){
        std::ifstream input("p2-cave-entry.txt");require(bool(input),"floor entry unreadable");std::ostringstream text;text<<input.rdbuf();require(!input.bad(),"floor entry read failed");std::string error;
        require(p2_cave_parse(text.str(),"P2_CAVE_ENTRY",route.party,error),"floor entry invalid");
        std::error_code bodyError;wfg=fullParty&&std::filesystem::exists("p2-cave-route-pom.txt",bodyError);require(!bodyError,"Pom profile existence query");
        if(wfg){
            std::ifstream profile("p2-cave-route-pom.txt");std::string magic,key,value,cave,token,extra;unsigned long long seed;int floor,count;
            require(bool(profile>>magic>>key>>value)&&magic=="P2_CAVE_ROUTE_POM_1"&&key=="profile"&&value=="wfg-pw-acquisition-v1","WFG fixture profile");
            require(bool(profile>>key>>seed)&&key=="seed","WFG seed");
            require(bool(profile>>key>>cave)&&key=="cave"&&cave=="forest_2","WFG cave");
            require(bool(profile>>key>>floor)&&key=="floor"&&floor==1,"WFG floor");
            require(bool(profile>>key>>token)&&key=="token"&&token==route.party.token&&route.party.floor==1&&route.party.schema==2,"WFG ENTRY2 token");
            require(bool(profile>>key>>count)&&key=="buds"&&count==2,"WFG body count");
            for(int i=0;i<2;++i){BodyTarget b;unsigned long long uid;std::string slot;int budget;
                require(bool(profile>>slot>>uid>>b.species>>b.x>>b.y>>b.z>>budget)&&slot=="forest_2:f1:bud:"+std::to_string(i)&&uid<=0xffffffffULL&&b.species==3+i&&budget==5&&std::isfinite(b.x)&&std::isfinite(b.y)&&std::isfinite(b.z),"WFG fixture body binding");b.uid=static_cast<unsigned>(uid);bodies.push_back(b);}
            require(bodies[0].uid!=bodies[1].uid&&!(profile>>extra)&&profile.eof(),"WFG fixture trailing or duplicate body");
            if(acquire){require(route.party.squad.size()==20&&route.party.health==1,"WFG actual initial baseline count/health");
                for(const auto& p:route.party.squad)require(p.species==1&&p.maturity==0,"WFG actual initial20 Red leaf baseline");}
        }
        std::ifstream transition("p2-cave-transition.txt");require(bool(transition)&&p2_cave_read_anchor(transition,route.party.floor,route.entrance),"floor transition invalid");
        // Engineered floor centerline, with length/exit obtained from the real
        // sidecar (floor2 salt1 is longer than floor1). No terrain changes.
        require(route.entrance.x>=0,"floor centerline expects east exit");
        // Avoid the real Pod at the origin without moving it or its geometry.
        floorPath.push_back({0,-100});floorPath.push_back({100,-100});floorPath.push_back({100,0});
        for(float x=200;x<route.entrance.x;x+=100)floorPath.push_back({x,0});
        floorPath.push_back({route.entrance.x,0});floorPath.push_back({route.entrance.x,route.entrance.z});
    }else{
        require(pc_pikipelago_surface_course()!=nullptr,"ordinary surface or room option required");
        std::ifstream input("p2-cave-route-surface.txt");require(bool(input)&&p2_cave_surface_route_read(input,route),"surface route sidecar invalid");
    }
    require(!acquire||(roomRoute&&wfg),"fresh acquisition requires matching WFG body profile");
    require(!transferExists(),"stale transfer at startup");
    require(!route.party.squad.empty()&&route.party.squad.size()<=100,"incoming Pikmin count invalid");for(const auto& p:route.party.squad)require(fullParty?(p.species>=0&&p.species<=4):p.species==P2SpeciesRed,"incoming species outside selected fixture profile");
    require(pc_window_init("P2 Cave route runtime",960,540),"window init");pc_settings_init();
    // Settings has no process-local debug-key setter. Refuse unsafe saved config;
    // the runner must stage debugKeys=0 in its private settings file.
    require(!pc_settings_get_debug_keys(),"stage private settings debugKeys=0");
    pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();pc_window_set_control_mode(PC_CONTROL_CLASSIC);
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    require(w==960&&h==540&&std::abs(x-(bounds.x+(bounds.w-w)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-h)/2))<=2,"window baseline");
    std::puts("P2_CAVE_ROUTE_WINDOW width=960 height=540 centered=1 after_settings=1");
    SDL_VirtualJoystickDesc desc{};desc.version=SDL_VIRTUAL_JOYSTICK_DESC_VERSION;desc.type=SDL_JOYSTICK_TYPE_GAMECONTROLLER;desc.naxes=SDL_CONTROLLER_AXIS_MAX;desc.nbuttons=SDL_CONTROLLER_BUTTON_MAX;desc.axis_mask=(1u<<SDL_CONTROLLER_AXIS_MAX)-1;desc.button_mask=(1u<<SDL_CONTROLLER_BUTTON_MAX)-1;desc.name="Cave route fixture P1";
    int device=SDL_JoystickAttachVirtualEx(&desc);require(device>=0,"virtual attach");pad=SDL_JoystickOpen(device);require(pad!=nullptr,"virtual open");
    PADStatus statuses[4]{};pc_window_poll_events(statuses);int id=SDL_JoystickInstanceID(pad);pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,id);pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    for(int a=0;a<PC_KEY_ACT_COUNT;++a)pc_window_set_gamepad_binding(a,-1);
    pc_window_set_stick_dead_zone(15);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);controls();pc_window_poll_events(statuses);
    SDL_GameController* resolved=pc_window_get_controller();require(resolved&&SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(resolved))==id,"virtual P1 assignment");
    std::printf("P2_CAVE_ROUTE_GAMEPAD instance=%d player=1 assigned=1 input=SDL_virtual\n",id);std::fflush(nullptr);
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CaveRouteApp());return 0;
}
