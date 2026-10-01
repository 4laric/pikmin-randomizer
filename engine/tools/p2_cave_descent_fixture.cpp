// #1127: actual native source boundary and independent floor2 actor observation.
// Red=1 uses named native species constants. No staged-alone descent proof.
// SDL virtual controller input; exit confirmation bypassed.
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
#include <fstream>
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474);
// observation-only, equivalent tested guard. The canonical header is consumed
// read-only; this vendored copy exists because a replacement-main TU cannot
// include a Python-tree script header at native build time.
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}

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
    if(!sVirtualPad){std::puts("FAIL CAVE_DESCENT virtual pad missing");std::_Exit(3);}
    for(int b=0;b<SDL_CONTROLLER_BUTTON_MAX;++b)SDL_JoystickSetVirtualButton(sVirtualPad,b,0);
    const unsigned bits[]={KBBTN_A,KBBTN_B,KBBTN_X,KBBTN_Y,KBBTN_Z,KBBTN_L,KBBTN_START};
    const int bindings[]={SDL_CONTROLLER_BUTTON_A,SDL_CONTROLLER_BUTTON_B,SDL_CONTROLLER_BUTTON_X,SDL_CONTROLLER_BUTTON_Y,SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,SDL_CONTROLLER_BUTTON_LEFTSHOULDER,SDL_CONTROLLER_BUTTON_START};
    for(int i=0;i<7;++i)if(buttons&bits[i])SDL_JoystickSetVirtualButton(sVirtualPad,bindings[i],1);
    SDL_JoystickSetVirtualAxis(sVirtualPad,SDL_CONTROLLER_AXIS_LEFTX,sx*256);
    SDL_JoystickSetVirtualAxis(sVirtualPad,SDL_CONTROLLER_AXIS_LEFTY,-sy*256);
    SDL_JoystickUpdate();
}
void setupVirtualPad(){
    SDL_VirtualJoystickDesc desc;SDL_zero(desc);desc.version=SDL_VIRTUAL_JOYSTICK_DESC_VERSION;
    desc.type=SDL_JOYSTICK_TYPE_GAMECONTROLLER;desc.naxes=SDL_CONTROLLER_AXIS_MAX;desc.nbuttons=SDL_CONTROLLER_BUTTON_MAX;
    desc.axis_mask=(1u<<SDL_CONTROLLER_AXIS_MAX)-1u;desc.button_mask=(1u<<SDL_CONTROLLER_BUTTON_MAX)-1u;desc.name="Cave color supply fixture P1";
    int device=SDL_JoystickAttachVirtualEx(&desc);if(device<0){std::printf("FAIL CAVE_DESCENT virtual attach %s\n",SDL_GetError());std::_Exit(3);}
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
    std::printf("P2_CAVE_DESCENT_GAMEPAD instance=%d player=1 assigned=%d input=SDL_virtual process_local=1 navi_override=0\n",id,int(assigned));std::fflush(nullptr);
    if(!assigned)std::_Exit(3);
}

class CaveDescentApp final : public PlugPikiApp {
    int frames=0, observed=0, phase=0, point=0, phaseTick=0, throwTick=0, aimed=0;
    bool entrySeen=false,captainSeen=false,started=false;
    void require(bool yes,const char* why){if(!yes){std::printf("FAIL CAVE_DESCENT %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
    int colour(int species){int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&pc_p2_species(p)==species)++count;}return count;}
    void mixed(){require(alivePikis()==20&&colour(P2SpeciesBlue)==5&&colour(P2SpeciesRed)==15,"mixed squad changed");}
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
        fixturePad(KeyConfig::_instance->mSetCursorKey.mBind,sx,sy);
    }
    void scenarioTick(Navi* n){
        if(observed<60)return;
        if(pc_p2_cave_floor()==2){
            mixed();require(!pc_p2_cave_bud_pending(),"floor2 pending outputs");
            std::ifstream in("p2-cave-entry.txt");std::string version,token,extra;int floor,count;float health;
            require(bool(in>>version>>token>>floor>>health>>count)&&floor==2&&count==20,"incoming floor2 header");
            int expected[3][3]{};for(int i=0;i<count;++i){int species,maturity;require(bool(in>>species>>maturity)&&species>=0&&species<=2&&maturity>=0&&maturity<=2,"incoming Pikmin");++expected[species][maturity];}
            require(!(in>>extra)&&in.eof(),"trailing incoming entry");
            int actual[3][3]{};Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()){int species=pc_p2_species(p);require(species>=0&&species<=2&&p->mHappa<=2,"observed species/maturity");++actual[species][p->mHappa];}}
            for(int species=0;species<3;++species)for(int maturity=0;maturity<3;++maturity)require(expected[species][maturity]==actual[species][maturity],"incoming actor identity/maturity changed");
            require(pc_p2_cave_boundary_token()==token,"actual engine floor token");
            float normalized=n->mHealth/C_NAVI_PARM(n,mHealth);require(std::fabs(normalized-health)<0.000001f,"incoming captain health changed");
            require(pc_p2_cave_bud_save("fixture-floor2-observed-buds.txt"),"observed floor2 bud snapshot");
            std::printf("PASS CAVE_DESCENT_FLOOR2 floor=%d red=%d blue=%d yellow=%d count=%d health=%.9g maturity_exact=1 token=%s observed_native_actors=1\n",pc_p2_cave_floor(),colour(P2SpeciesRed),colour(P2SpeciesBlue),colour(P2SpeciesYellow),alivePikis(),normalized,token.c_str());
            std::fflush(nullptr);std::_Exit(0);
        }
        require(pc_p2_cave_floor()==1,"unsupported source floor");
        if(!started){require(alivePikis()==20&&colour(P2SpeciesRed)==20&&colour(P2SpeciesBlue)==0&&colour(P2SpeciesYellow)==0,"requires ordinary20Red and noYellow entry");started=true;phaseTick=observed;
            std::printf("P2_CAVE_DESCENT_SPECIES red_id=%d yellow_id=%d blue_id=%d red_count=%d yellow_count=%d blue_count=%d\n",P2SpeciesRed,P2SpeciesYellow,P2SpeciesBlue,colour(P2SpeciesRed),colour(P2SpeciesYellow),colour(P2SpeciesBlue));
            std::puts("P2_CAVE_DESCENT_SETUP starting=20_red_ordinary_entry input=SDL_virtual_gamepad position_writes=0 velocity_writes=0 species_writes=0 state_writes=0 bud_auto_pluck=production confirmation=bypassed");}
        Vector3f bud;require(pc_p2_cave_bud_position("blue",bud),"blue bud missing");
        if(observed%120==0){std::printf("P2_CAVE_DESCENT_PROGRESS phase=%d point=%d red=%d blue=%d alive=%d following=%d conversions=%d pending=%d navi=%.2f,%.2f cursor=%.2f,%.2f\n",phase,point,colour(P2SpeciesRed),colour(P2SpeciesBlue),alivePikis(),following(),pc_p2_cave_bud_conversions(),int(pc_p2_cave_bud_pending()),n->mSRT.t.x,n->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.z);std::fflush(nullptr);}
        if(phase==0){static const float path[][2]={{0,-100},{-100,-100},{-100,20}};
            if(walkTo(n,path[point][0],path[point][1])){if(point==2&&following()!=20){gatherAtCursor(n);return;}if(++point==3){phase=1;phaseTick=observed;point=0;}}return;}
        if(phase==1){
            if(colour(P2SpeciesBlue)==5&&pc_p2_cave_bud_conversions()==5&&!pc_p2_cave_bud_pending()){
                mixed();fixturePad(0);phase=2;phaseTick=observed;std::puts("P2_CAVE_DESCENT_ACQUIRED red=15 blue=5 conversions=5 source=ordinary_controller_throw");std::fflush(nullptr);return;}
            require(observed-phaseTick<720,"controller conversion timeout");
            // Aim in the classic low-stick band, then press/release the mapped
            // throw key. All Flying/grab/throw transitions belong to the engine.
            if(throwTick==0){if(aimAt(n,bud.x,bud.z)){if(++aimed>=15){throwTick=1;aimed=0;}}else aimed=0;return;}
            aimAt(n,bud.x,bud.z,throwTick<=20?KeyConfig::_instance->mThrowKey.mBind:0);
            if(throwTick==1){std::puts("P2_CAVE_DESCENT_THROW input=mapped_button");std::fflush(nullptr);}
            if(++throwTick>=75)throwTick=0;
            return;
        }
        mixed();
        if(phase==2){require(observed-phaseTick<240,"mixed whistle timeout");if(following()!=20||observed-phaseTick<45){gatherAtCursor(n);return;}phase=3;point=0;fixturePad(0);std::puts("P2_CAVE_DESCENT_RECALLED following=20 red=15 blue=5");return;}
        if(phase==3){static const float path[][2]={{-100,-100},{100,-100},{100,100}};
            if(walkTo(n,path[point][0],path[point][1])){
                if(following()!=20)return;
                float far=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()){float dx=p->mSRT.t.x-n->mSRT.t.x,dy=p->mSRT.t.y-n->mSRT.t.y,dz=p->mSRT.t.z-n->mSRT.t.z;require(std::isfinite(dx)&&std::isfinite(dy)&&std::isfinite(dz),"nonfinite position");far=std::fmax(far,std::sqrt(dx*dx+dy*dy+dz*dz));}}
                if(far>170)return;
                if(++point==3){phase=4;phaseTick=observed;std::printf("P2_CAVE_DESCENT_MIXED_MOVEMENT red=15 blue=5 following=20 farthest=%.3f x=%.3f z=%.3f\n",far,n->mSRT.t.x,n->mSRT.t.z);std::fflush(nullptr);}
            }return;
        }
        if(phase==4){fixturePad(observed-phaseTick==1?KeyConfig::_instance->mDisbandKey.mBind:0);if(observed-phaseTick<40)return;require(following()==0,"mixed squad not safely disbanded");phase=5;point=0;std::puts("P2_CAVE_DESCENT_EXIT captain_only=1 squad_left_west=1 full_squad_traversal=0");return;}
        if(phase==5){static const float path[][2]={{100,0},{200,0},{300,0},{400,0},{500,0},{600,0},{700,0},{800,0},{800,100}};
            if(walkTo(n,path[point][0],path[point][1])&&++point==9)phase=6;return;}
        if(phase==6){fixturePad(0);require(!pc_p2_cave_bud_pending(),"checkpoint pending conversions");if(pc_p2_cave_checkpoint(false)){std::puts("P2_CAVE_DESCENT_CHECKPOINT red=15 blue=5 survivors=20 conversions=5");std::fflush(nullptr);require(pc_p2_cave_exit_after_checkpoint(),"native exit unavailable");}}
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
            gameflow.mMoviePlayer->requestSkip();
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
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
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
    { SDL_Window* window=SDL_GL_GetCurrentWindow();int w=0,h=0;SDL_GetWindowSize(window,&w,&h);
      std::printf("P2_CAVE_FINAL_WINDOW width=%d height=%d mode=%d\n",w,h,pc_window_get_display_mode());std::fflush(nullptr);
      if(w!=960 || h!=540 || pc_window_get_display_mode()!=PC_WINDOW_FULLSCREEN_WINDOWED)return 3; }
    setupVirtualPad();
    nodeMgr = new NodeMgr();
    gsys->run(new CaveDescentApp());
    return 0;
}
