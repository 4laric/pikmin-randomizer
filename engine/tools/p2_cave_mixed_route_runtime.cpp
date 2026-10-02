// #930 ordinary mixed-color acquisition, water receipt and F6 boundary.
// #1125 corrected species namespace: ordinary fresh stage Red=1.
// SDL virtual controller input; production F6 and external native dialog.
// No gameplay actor position/velocity/species/mode or attachment writes.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "Generator.h"
#include "Section.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "NaviState.h"
#include "Camera.h"
#include "Controller.h"
#include "KeyConfig.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Collision.h"
#include "Creature.h"
#include "MoviePlayer.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "teki.h"
#include "pc_p2_cave.h"
#include "pc_p2_cave_bud_actor.h"
#include "pc_p2_cave_carry_engine.h"
#include "pc_p2_cave_items_engine.h"
#include "pc_p2_species.h"
#include <vector>
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "p2_fixture_captain_guard.h"
namespace {
bool sGuardSelfTest = false;
bool sForceCaptainDown = false; // env P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN=1: negative-path test only

// Engine-independent self test of the vendored guard truth table. Runs before
// any engine boot so it works without assets or a display.
int guardSelfTest() {
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.5f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {false, true, 100.0f, true},
        {true, false, 100.0f, true},
        {true, true, 0.0f, true},
    };
    for (size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        const bool down = p2_fixture_captain_down(rows[i].orima, rows[i].dead, rows[i].hp);
        if (down != rows[i].expectDown) {
            std::printf("FAIL CAVE_GUARDED_BOOT selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CAVE_GUARDED_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}


SDL_Joystick* sVirtualPad=nullptr;
void fixturePad(unsigned buttons,int sx=0,int sy=0){
    if(!sVirtualPad){std::puts("FAIL CAVE_MIXED_ROUTE virtual pad missing");std::_Exit(3);}
    for(int b=0;b<SDL_CONTROLLER_BUTTON_MAX;++b)SDL_JoystickSetVirtualButton(sVirtualPad,b,0);
    const unsigned bits[]={KBBTN_A,KBBTN_B,KBBTN_X,KBBTN_Y,KBBTN_Z,KBBTN_L,KBBTN_START,KBBTN_DPAD_RIGHT};
    const int bindings[]={SDL_CONTROLLER_BUTTON_A,SDL_CONTROLLER_BUTTON_B,SDL_CONTROLLER_BUTTON_X,SDL_CONTROLLER_BUTTON_Y,SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,SDL_CONTROLLER_BUTTON_LEFTSHOULDER,SDL_CONTROLLER_BUTTON_START,SDL_CONTROLLER_BUTTON_DPAD_RIGHT};
    for(int i=0;i<8;++i)if(buttons&bits[i])SDL_JoystickSetVirtualButton(sVirtualPad,bindings[i],1);
    SDL_JoystickSetVirtualAxis(sVirtualPad,SDL_CONTROLLER_AXIS_LEFTX,sx*256);
    SDL_JoystickSetVirtualAxis(sVirtualPad,SDL_CONTROLLER_AXIS_LEFTY,-sy*256);
    SDL_JoystickUpdate();
}
void setupVirtualPad(){
    SDL_VirtualJoystickDesc desc;SDL_zero(desc);desc.version=SDL_VIRTUAL_JOYSTICK_DESC_VERSION;
    desc.type=SDL_JOYSTICK_TYPE_GAMECONTROLLER;desc.naxes=SDL_CONTROLLER_AXIS_MAX;desc.nbuttons=SDL_CONTROLLER_BUTTON_MAX;
    desc.axis_mask=(1u<<SDL_CONTROLLER_AXIS_MAX)-1u;desc.button_mask=(1u<<SDL_CONTROLLER_BUTTON_MAX)-1u;desc.name="Cave mixed route fixture P1";
    int device=SDL_JoystickAttachVirtualEx(&desc);if(device<0){std::printf("FAIL CAVE_MIXED_ROUTE virtual attach %s\n",SDL_GetError());std::_Exit(3);}
    sVirtualPad=SDL_JoystickOpen(device);if(!sVirtualPad)std::_Exit(3);
    PADStatus pads[4]{};pc_window_poll_events(pads);
    int id=SDL_JoystickInstanceID(sVirtualPad);
    // Instance ID, not device index: a physical controller may occupy slot0.
    // These assignments/settings are process-local; never save global settings.
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,id);pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    for(int action=0;action<PC_KEY_ACT_COUNT;++action)pc_window_set_gamepad_binding(action,-1);
    pc_window_set_stick_dead_zone(15);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);
    fixturePad(0);pc_window_poll_events(pads);
    SDL_GameController* controller=pc_window_get_controller();
    bool assigned=controller&&SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(controller))==id;
    std::printf("P2_CAVE_COLOR_GAMEPAD instance=%d player=1 assigned=%d input=SDL_virtual process_local=1 navi_override=0\n",id,int(assigned));std::fflush(nullptr);
    if(!assigned)std::_Exit(3);
}

class CaveMixedRouteApp final : public PlugPikiApp {
    int frames=0, observed=0, phase=0, point=0, phaseTick=0, throwTick=0, aimed=0;
    bool entrySeen=false,captainSeen=false,started=false,picked=false;
    int separated=0,selectionQuiet=0;Piki* selectedBlue=nullptr;
    std::vector<Piki*> originalBlues,blueFlights;
    const std::string scenario=std::getenv("P2_CAVE_TEST_SCENARIO")?std::getenv("P2_CAVE_TEST_SCENARIO"):"route";
    void require(bool yes,const char* why){if(!yes){std::printf("FAIL CAVE_MIXED_ROUTE %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
    int colour(int species){int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&pc_p2_species(p)==species)++count;}return count;}
    void mixed(){require(alivePikis()==20&&colour(P2SpeciesBlue)==1&&colour(P2SpeciesYellow)==1&&colour(P2SpeciesRed)==18,"mixed squad changed");}
    int followers(int species){int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mMode==PikiMode::FormationMode&&pc_p2_species(p)==species)++count;}return count;}
    void next(int value){phase=value;point=0;phaseTick=observed;throwTick=0;aimed=0;selectionQuiet=0;selectedBlue=nullptr;if(value==3)blueFlights.clear();fixturePad(0);}
    void f6(){for(int down=1;down>=0;--down){SDL_Event event{};event.type=down?SDL_KEYDOWN:SDL_KEYUP;event.key.windowID=SDL_GetWindowID(SDL_GL_GetCurrentWindow());event.key.state=down?SDL_PRESSED:SDL_RELEASED;event.key.keysym.scancode=SDL_SCANCODE_F6;event.key.keysym.sym=SDLK_F6;require(SDL_PushEvent(&event)==1,"F6 SDL event rejected");}std::puts("P2_CAVE_MIXED_F6 path=SDL_event confirmation=external_native_dialog");std::fflush(nullptr);}
    bool blueIdle(float& x,float& z){int count=0;x=z=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&pc_p2_species(p)==P2SpeciesBlue&&p->mMode!=PikiMode::FormationMode){x+=p->mSRT.t.x;z+=p->mSRT.t.z;++count;}}if(count){x/=count;z/=count;}return count>0;}
    bool originalBlue(Piki* p){for(Piki* actor:originalBlues)if(actor==p)return true;return false;}
    void selectedBlueThrow(Navi* n,float x,float z){
        const int state=n->getCurrState()->getID();
        if(observed%30==0){auto* grab=state==NAVISTATE_ThrowWait?static_cast<NaviThrowWaitState*>(n->getCurrState()):nullptr;
            Piki* actual=grab?(grab->mHeldThrowPiki?grab->mHeldThrowPiki:grab->mPendingThrowPiki):nullptr;
            std::printf("P2_CAVE_MIXED_THROW_OBSERVE phase=%d nstate=%d step=%d preferred_class=%d expected_Blue_class=%d quiet=%d cursor=%.2f,%.2f target=%.2f,%.2f max_cursor=%.2f throw_min=%.2f throw_max=%.2f actual=%p actual_species=%d actual_state=%d held=%d selected=%p selected_state=%d flights=%d\n",phase,state,throwTick,pc_preferred_throw_color_for(n),int(Blue),selectionQuiet,n->mCursorWorldPos.x,n->mCursorWorldPos.z,x,z,C_NAVI_PARM(n,mCursorMaxRadius),C_NAVI_PARM(n,mThrowMinDistance),C_NAVI_PARM(n,mThrowMaxDistance),static_cast<void*>(actual),actual?pc_p2_species(actual):-1,actual?actual->getState():-1,grab?int(grab->mIsHoldingThrowPiki):0,static_cast<void*>(selectedBlue),selectedBlue?selectedBlue->getState():-1,int(blueFlights.size()));std::fflush(nullptr);
        }
        if(selectedBlue && selectedBlue->getState()==PIKISTATE_Flying){
            bool seen=false;for(Piki* actor:blueFlights)if(actor==selectedBlue)seen=true;
            if(!seen){blueFlights.push_back(selectedBlue);std::printf("P2_CAVE_MIXED_BLUE_FLIGHT actor=%p ordinal=%d source=ordinary_release x=%.2f z=%.2f\n",static_cast<void*>(selectedBlue),int(blueFlights.size()),selectedBlue->mSRT.t.x,selectedBlue->mSRT.t.z);std::fflush(nullptr);}
            fixturePad(0);return;
        }
        if(throwTick==2){
            fixturePad(0);bool observedFlight=false;for(Piki* actor:blueFlights)if(actor==selectedBlue)observedFlight=true;
            // Hanged exits to Normal during NaviThrow wind-up, before its
            // KEY_Action0 starts Flying. Normal alone is not a landing witness.
            if(selectedBlue && selectedBlue->getState()==PIKISTATE_Normal){
                if(observedFlight){selectedBlue=nullptr;throwTick=0;selectionQuiet=0;}
                else if(observed%10==0){std::printf("P2_CAVE_MIXED_BLUE_FLIGHT_PENDING actor=%p nstate=%d preflight_Normal=1 input=neutral\n",static_cast<void*>(selectedBlue),state);std::fflush(nullptr);}
            }
            return;
        }
        if(state==NAVISTATE_ThrowWait){
            auto* grab=static_cast<NaviThrowWaitState*>(n->getCurrState());
            Piki* actual=grab->mHeldThrowPiki?grab->mHeldThrowPiki:grab->mPendingThrowPiki;
            if(actual){require(actual->isAlive()&&originalBlue(actual)&&pc_p2_species(actual)==P2SpeciesBlue,"actual pending/held is not an original Blue");
                if(!selectedBlue)selectedBlue=actual;require(selectedBlue==actual,"actual grab identity changed");}
            if(actual && grab->mHeldThrowPiki==actual && grab->mIsHoldingThrowPiki && actual->getState()==PIKISTATE_Hanged){
                aimAt(n,x,z,0);throwTick=2;std::printf("P2_CAVE_MIXED_BLUE_RELEASE actor=%p actual_Hanged=1 preferred_class=%d\n",static_cast<void*>(actual),pc_preferred_throw_color_for(n));std::fflush(nullptr);
            }else aimAt(n,x,z,KeyConfig::_instance->mThrowKey.mBind);
            return;
        }
        if(state!=NAVISTATE_Walk){fixturePad(0);return;}
        // Production selection uses GlobalGameOptions::Blue (0), as returned
        // by pc_throw_selection_class. Keep the named enum, not a guessed ID.
        // D-pad selection happens before A. The HUD is only a preview eligibility
        // check; actual pending/held membership above governs the release.
        if(pc_preferred_throw_color_for(n)!=int(Blue)){
            selectionQuiet=0;aimAt(n,x,z,(observed-phaseTick)%30<2?KBBTN_DPAD_RIGHT:0);return;
        }
        ++selectionQuiet;Piki* preview=n->mNextThrowPiki;
        const bool eligible=preview&&originalBlue(preview)&&preview->isAlive()&&preview->mNavi==n&&preview->mMode==PikiMode::FormationMode&&preview->getState()==PIKISTATE_Normal&&preview->isThrowable();
        const bool aimedAt=aimAt(n,x,z);
        if(selectionQuiet>=10&&eligible&&aimedAt){aimAt(n,x,z,KeyConfig::_instance->mThrowKey.mBind);throwTick=1;}
    }
    void mappedThrow(Navi* n,float x,float z,bool selectBlue=false){
        if(selectBlue){selectedBlueThrow(n,x,z);return;}
        if(!throwTick){if(aimAt(n,x,z)&&++aimed>=15){throwTick=1;aimed=0;}return;}
        aimAt(n,x,z,throwTick<=20?KeyConfig::_instance->mThrowKey.mBind:0);if(++throwTick>=85)throwTick=0;
    }
    bool aimAt(Navi* n,float x,float z,unsigned buttons=0){
        const float dx=x-n->mCursorWorldPos.x,dz=z-n->mCursorWorldPos.z,d=std::sqrt(dx*dx+dz*dz);
        int sx=0,sy=0;require(n->controlCamera()!=nullptr,"aim camera missing");
        if(d>6){const Vector3f& a=n->controlCamera()->mViewXAxis;sx=int(std::lround(30*(dx*a.x+dz*a.z)/d));sy=int(std::lround(30*(dx*a.z-dz*a.x)/d));}
        // Input alignment only; the real bud still owns its 30-unit capture test.
        fixturePad(buttons,sx,sy);return d<=20;
    }
    bool walkTo(Navi* n,float x,float z) {
        float dx=x-n->mSRT.t.x,dz=z-n->mSRT.t.z;
        float distance=std::sqrt(dx*dx+dz*dz);
        if(distance<10) {fixturePad(0);return true;}
        require(n->controlCamera()!=nullptr,"navigation camera missing");
        const Vector3f& axis=n->controlCamera()->mViewXAxis;
        // Classic controls reserve small stick magnitudes for aiming only.
        // Stay above that band until the waypoint tolerance, then release.
        const float speed=65.0f;
        const int sx=int(std::lround(speed*(dx*axis.x+dz*axis.z)/distance));
        const int sy=int(std::lround(speed*(dx*axis.z-dz*axis.x)/distance));
        unsigned buttons=0;
        if(sx>32)buttons|=KBBTN_MSTICK_RIGHT;else if(sx< -32)buttons|=KBBTN_MSTICK_LEFT;
        if(sy>32)buttons|=KBBTN_MSTICK_UP;else if(sy< -32)buttons|=KBBTN_MSTICK_DOWN;
        fixturePad(buttons,sx,sy);
        return false;
    }
    int following() {
        int count=0;Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mMode==PikiMode::FormationMode)++count;}return count;
    }
    void gatherAtCursor(Navi* n) {
        const bool onlyIdle=following()<20;
        float x=0,z=0;int count=0;Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);
            if(p&&p->isAlive()&&(!onlyIdle || p->mMode!=PikiMode::FormationMode)) {x+=p->mSRT.t.x;z+=p->mSRT.t.z;++count;}}
        require(count>0,"no squad for whistle");
        float dx=x/count-n->mCursorWorldPos.x,dz=z/count-n->mCursorWorldPos.z;
        float distance=std::sqrt(dx*dx+dz*dz);int sx=0,sy=0;
        if(distance>8) {
            const Vector3f& axis=n->controlCamera()->mViewXAxis;
            // Deliberately use the classic aim-only band while holding whistle.
            sx=int(std::lround(30*(dx*axis.x+dz*axis.z)/distance));
            sy=int(std::lround(30*(dx*axis.z-dz*axis.x)/distance));
        }
        if((phase==2 || phase==10) && observed%30==0){
            std::printf("P2_CAVE_MIXED_GATHER phase=%d point=%d followers=%d target=%.2f,%.2f cursor=%.2f,%.2f aim_distance=%.2f max_cursor=%.2f\n",phase,point,following(),x/count,z/count,n->mCursorWorldPos.x,n->mCursorWorldPos.z,distance,C_NAVI_PARM(n,mCursorMaxRadius));
            Iterator idle(pikiMgr);CI_LOOP(idle){Piki* p=static_cast<Piki*>(*idle);if(p && p->isAlive() && p->mMode!=PikiMode::FormationMode)
                std::printf("P2_CAVE_MIXED_IDLE actor=%p species=%d state=%d mode=%d x=%.2f z=%.2f\n",static_cast<void*>(p),pc_p2_species(p),p->getState(),int(p->mMode),p->mSRT.t.x,p->mSRT.t.z);}
            std::fflush(nullptr);
        }
        fixturePad(KeyConfig::_instance->mSetCursorKey.mBind,sx,sy);
    }
    void drySeparationApproach(Navi* n,int base,int round){
        // Gather before and after walking, rather than aborting a dry walking
        // leg whenever a following actor temporarily leaves formation.
        if(point==base){if(following()!=20){gatherAtCursor(n);return;}fixturePad(0);++point;return;}
        if(point==base+1){if(walkTo(n,-100,-100))++point;return;}
        if(point==base+2){if(walkTo(n,-20,-100))++point;return;}
        require(point==base+3,"invalid dry separation approach stage");
        if(following()!=20){gatherAtCursor(n);return;}
        separated=round;next(3);
    }
    void scenarioTick(Navi* n){
        if(observed<60)return;
        if(scenario=="restore"){
            mixed();require(!pc_p2_cave_bud_pending(),"restore pending outputs");
            require(!pc_p2_cave_items_pellet_for("treasure_water"),"delivered water item respawned");
            require(pc_p2_cave_items_delivered()==0,"reload granted another receipt");
            std::puts("PASS CAVE_MIXED_ROUTE_RESTORE red=18 blue=1 yellow=1 water_absent=1 new_receipts=0");std::fflush(nullptr);std::_Exit(0);
        }
        require(scenario=="route","unknown scenario");
        if(!started){require(alivePikis()==20&&colour(P2SpeciesRed)==20,"requires ordinary20Red entry");started=true;phaseTick=observed;std::puts("P2_CAVE_MIXED_SETUP starting=20_red input=SDL_virtual actor_writes=0 checkpoint_bypass=0 bud_auto_pluck=production");}
        require(alivePikis()==20,"survivor population changed");
        if(observed%90==0){std::printf("P2_CAVE_MIXED_PROGRESS phase=%d point=%d red=%d blue=%d yellow=%d following_red=%d following_blue=%d conversions=%d pending=%d navi=%.1f,%.1f delivered=%d\n",phase,point,colour(P2SpeciesRed),colour(P2SpeciesBlue),colour(P2SpeciesYellow),followers(P2SpeciesRed),followers(P2SpeciesBlue),pc_p2_cave_bud_conversions(),int(pc_p2_cave_bud_pending()),n->mSRT.t.x,n->mSRT.t.z,pc_p2_cave_items_delivered());std::fflush(nullptr);}
        require(observed-phaseTick<900,"ordinary route phase timeout");
        if(phase==0){static const float path[][2]={{0,-100},{-100,-100},{-100,20}};if(walkTo(n,path[point][0],path[point][1])){if(point==2&&following()!=20){gatherAtCursor(n);return;}if(++point==3)next(1);}return;}
        if(phase==1){Vector3f bud;require(pc_p2_cave_bud_position("blue",bud),"Blue bud missing");
            if(colour(P2SpeciesBlue)==2&&!pc_p2_cave_bud_pending()){require(colour(P2SpeciesRed)==18,"Blue conversion mismatch");Iterator blues(pikiMgr);CI_LOOP(blues){Piki* p=static_cast<Piki*>(*blues);if(p&&p->isAlive()&&pc_p2_species(p)==P2SpeciesBlue)originalBlues.push_back(p);}require(originalBlues.size()==2,"original Blue identities missing");std::puts("P2_CAVE_MIXED_ACQUIRED red=18 blue=2");next(2);return;}
            require(colour(P2SpeciesBlue)<=2,"excess Blue conversion");
            if(pc_p2_cave_bud_pending()){fixturePad(0);return;}mappedThrow(n,bud.x,bud.z);return;}
        if(phase==2){drySeparationApproach(n,0,0);return;}
        // The loaded cursor radius is 100: walk within reach of target (60,-100).
        // At a dry point, ordinary Blue-only throws separate actors from Red squad.
        // Dismiss leaves Reds at the captain; whistle from the remote landing side.
        if(phase==3){int landed=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&pc_p2_species(p)==P2SpeciesBlue&&p->mMode!=PikiMode::FormationMode&&p->getState()==PIKISTATE_Normal&&p->mSRT.t.x>20)++landed;}
            if(landed==2){require(blueFlights.size()==2,"two original Blue ordinary flights not observed");next(4);return;}mappedThrow(n,60,-100,true);return;}
        if(phase==4){fixturePad(observed-phaseTick==1?KeyConfig::_instance->mDisbandKey.mBind:0);if(observed-phaseTick>30)next(5);return;}
        if(phase==5){if(walkTo(n,30,-180))next(6);return;} // Inside the water-leaf corridor walls at x=+/-50.
        if(phase==6){require(followers(P2SpeciesRed)==0,"whistle gathered Reds; refusing water traversal");
            if(followers(P2SpeciesBlue)==2){std::puts("P2_CAVE_MIXED_BLUE_ONLY followers=2 red_followers=0");next(separated?11:7);return;}
            float x,z;require(blueIdle(x,z),"missing idle Blue");aimAt(n,x,z,KeyConfig::_instance->mSetCursorKey.mBind);return;}
        if(phase==7){require(followers(P2SpeciesRed)==0,"Reds entered water route");static const float path[][2]={{0,-200},{0,-300},{0,-400},{0,-480}};if(walkTo(n,path[point][0],path[point][1])&&++point==4)next(8);return;}
        if(phase==8){Pellet* treasure=pc_p2_cave_items_pellet_for("treasure_water");
            Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(treasure&&p&&p->isAlive()&&p->getStickObject()==treasure){require(pc_p2_species(p)==P2SpeciesBlue,"nonBlue water carrier");picked=true;std::puts("P2_CAVE_MIXED_PICKUP source=ordinary_throw carrier=Blue");next(9);return;}}
            require(treasure!=nullptr,"delivery preceded observed pickup");mappedThrow(n,treasure->mSRT.t.x,treasure->mSRT.t.z);return;}
        if(phase==9){fixturePad(0);if(pc_p2_cave_items_delivered()==1){require(picked,"receipt without attachment");std::puts("P2_CAVE_MIXED_DELIVERED once=1 source=physical_Pod");next(10);}return;}
        if(phase==10){static const float path[][2]={{0,-400},{0,-300},{0,-200},{0,-100},{0,0}};
            if(point<5){if(walkTo(n,path[point][0],path[point][1]))++point;return;}
            drySeparationApproach(n,5,1);return;}
        if(phase==11){require(followers(P2SpeciesRed)==0,"Red following through Blue choke");static const float path[][2]={{100,-100},{100,0},{200,0},{300,0},{400,0},{500,0},{600,0},{700,0},{800,0},{900,20}};
            if(walkTo(n,path[point][0],path[point][1])&&++point==10){require(followers(P2SpeciesBlue)==2,"Blue followers lost at far side");std::puts("P2_CAVE_MIXED_BLUE_CHOKE physical_controller_traversal=1");next(12);}return;}
        if(phase==12){Vector3f bud;require(pc_p2_cave_bud_position("yellow",bud),"Yellow bud missing");
            if(colour(P2SpeciesYellow)==1&&!pc_p2_cave_bud_pending()){mixed();std::puts("P2_CAVE_MIXED_YELLOW red=18 blue=1 yellow=1");next(13);return;}
            require(colour(P2SpeciesYellow)<=1,"excess Yellow conversion");if(pc_p2_cave_bud_pending()){fixturePad(0);return;}mappedThrow(n,bud.x,bud.z);return;}
        if(phase==13){mixed();if(walkTo(n,800,100)){require(pc_p2_cave_items_delivered()==1,"receipt count changed");require(!pc_p2_cave_bud_pending(),"pending boundary conversion");fixturePad(0);std::puts("P2_CAVE_MIXED_BOUNDARY_READY survivors=20 red=18 blue=1 yellow=1 receipt=1");std::fflush(nullptr);f6();next(14);}return;}
        if(phase==14){fixturePad(0);return;} // production F6/OS dialog owns transfer/exit42
    }
    int alivePikis() {
        int count = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) { Creature* p = *it; if (p && p->isAlive()) ++count; }
        return count;
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        // Captain safety precedes every readiness or pause wait.
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(n && n->getCurrState()) {
            captainSeen=true;
            p2_fixture_require_captain(GameStat::orimaDead,
                n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,observed);
            if(sForceCaptainDown)p2_fixture_require_captain(true,true,0,observed);
        } else if(captainSeen || entrySeen) p2_fixture_require_captain(true,true,0,observed);
        if (++frames > 30000) {
            std::printf("FAIL CAVE_GUARDED_BOOT timeout entry_seen=%d observed=%d\n",
                        int(entrySeen), observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!n || !n->getCurrState() || !tekiMgr || !pikiMgr) return result;
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            fixturePad(KBBTN_START);
            return result;
        }
        if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        // Readiness is the engine cave entry state itself (floor applied by
        // pc_p2_cave_setup over the caller input package), not the room
        // cargo mode: non-beasts floor-1 imports run treasure-driven
        // previews where cargo-free is false by design.
        const int floor = pc_p2_cave_floor();
        if (floor <= 0 && observed % 600 == 0) {
            std::printf("P2_CAVE_GUARDED_BOOT_WAIT observed=%d floor=0\n", observed);
            std::fflush(stdout);
        }
        if (floor > 0 && !entrySeen) {
            entrySeen = true;
            std::printf("P2_CAVE_GUARDED_ENTRY_READY floor=%d observed=%d\n", floor, observed);
            std::fflush(stdout);
        }
        if (entrySeen) scenarioTick(n);
        return result;
    }
};
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") sGuardSelfTest = true;
        if (std::string(argv[i]) == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            // Engine-independent; the exit code is the assertion.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL CAVE_GUARDED_BOOT negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    if (sGuardSelfTest) return guardSelfTest();
    const char* force = std::getenv("P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == 49 && force[1] == 0) sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1",1);
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL CAVE_GUARDED_BOOT requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 Cave guarded boot fixture", 960, 540)) return 3;
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0};
        SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_CAVE_GUARDED_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    pc_window_set_control_mode(PC_CONTROL_CLASSIC);
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960,540);
    pc_window_center();
    { SDL_Window* window=SDL_GL_GetCurrentWindow();int w=0,h=0,x=0,y=0;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
      SDL_Rect bounds{};if(SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds)!=0)return 3;
      const bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;
      const bool windowed=(SDL_GetWindowFlags(window)&(SDL_WINDOW_FULLSCREEN|SDL_WINDOW_FULLSCREEN_DESKTOP))==0;
      std::printf("P2_CAVE_FINAL_WINDOW width=%d height=%d mode=%d centered=%d windowed=%d x=%d y=%d\n",w,h,pc_window_get_display_mode(),int(centered),int(windowed),x,y);std::fflush(nullptr);
      if(w!=960 || h!=540 || !centered || !windowed || pc_window_get_display_mode()!=PC_WINDOW_FULLSCREEN_WINDOWED)return 3; }
    setupVirtualPad();
    nodeMgr = new NodeMgr();
    gsys->run(new CaveMixedRouteApp());
    return 0;
}
