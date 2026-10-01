// #930 guarded engine regression. Scripted positioning/throw inputs are disclosed.
// PASS markers are scenario-specific, never complete player-route acceptance.
// Shared replacement-main cave boot fixture (lane cave-guarded-runtime-fixture, #642).
//
// Private prerequisite for blocked forest1 P1 (#154) and yakushima4 P1 (#161):
// boots the REAL game-linked engine over a caller-supplied input package
// (p2-cave-entry.txt + p2-cave-generate.txt + p2-cave-runtime-inputs.json,
// built by experimental/pikmin2_cave_runtime_inputs.py), lets the integrated
// cave entry path (pc_p2_preview.cpp -> pc_p2_cave_setup, #129 landing) apply
// the entry and run the opt-in generator sidecar, and reports guarded boot
// readiness. No new generator/save semantics anywhere: this file never parses
// manifests and never writes checkpoints; the engine owns both.
//
// Ordering contract (#632): the canonical captain guard runs on EVERY idle
// tick immediately after the base engine idle and BEFORE any readiness
// observation or PASS. CAPTAIN_DOWN exits BLOCKED (86) with no PASS. The
// guard never changes game state.
//
// Replacement-main convention: mirrors tools/p2_kurage_runtime.cpp (scenario
// main instead of pc_main.cpp; 960x540 centred window; --experimental-pikmin2-room
// boot). Promotion to a first-class CMake target is a documented shared-owner
// follow-up (see docs/PIKMIN2_CAVE_GUARDED_BOOT_FIXTURE.md); the lane build
// script links this TU against the private pikmin_pc graph without editing
// shared build files.
//
// Markers: P2_CAVE_GUARDED_BOOT_* only, plus the engine's own P2_CAVE_READY /
// P2_CAVE_GENERATE_* markers. Successful boot ends with
// "PASS CAVE_GUARDED_BOOT" and exit 0. Anything else is FAIL (1), BLOCKED
// (86), or timeout (2). No PASS is ever emitted without observed evidence.
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
#include "pc_p2_input_script.h"
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

class CaveGuardedBootApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool entrySeen = false, captainSeen = false, carryPicked = false;
    int throws = 0, lastThrow = -1000, initialBlocked = 0;
    bool positioned = false, exitPositioned = false;
    int routePhase=0, routePoint=0, phaseTick=0;
    bool walkTo(Navi* n,float x,float z) {
        float dx=x-n->mSRT.t.x,dz=z-n->mSRT.t.z;
        float distance=std::sqrt(dx*dx+dz*dz);
        if(distance<10) {pc_p2_input_script_set(1,0);return true;}
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
        pc_p2_input_script_set(1,buttons,sx,sy);
        return false;
    }
    int following() {
        int count=0;Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mMode==PikiMode::FormationMode)++count;}return count;
    }
    void gatherAtCursor(Navi* n) {
        float x=0,z=0;int count=0;Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);
            if(p&&p->isAlive()) {x+=p->mSRT.t.x;z+=p->mSRT.t.z;++count;}}
        require(count>0,"no squad for whistle");
        float dx=x/count-n->mCursorWorldPos.x,dz=z/count-n->mCursorWorldPos.z;
        float distance=std::sqrt(dx*dx+dz*dz);int sx=0,sy=0;
        if(distance>8) {
            const Vector3f& axis=n->controlCamera()->mViewXAxis;
            // Deliberately use the classic aim-only band while holding whistle.
            sx=int(std::lround(30*(dx*axis.x+dz*axis.z)/distance));
            sy=int(std::lround(30*(dx*axis.z-dz*axis.x)/distance));
        }
        pc_p2_input_script_set(1,KeyConfig::_instance->mSetCursorKey.mBind,sx,sy);
    }
    void deliveryRoute(Navi* n) {
        if(!positioned) {
            require(blues()==20,"transport fixture requires disclosed 20 Blue entry");
            positioned=true;phaseTick=observed;
            std::puts("P2_CAVE_ROUTE_SETUP starting_species=20_blue_staged input=scripted_controller position_writes=0 velocity_writes=0 checkpoint_confirmation=bypassed");
        }
        if(routePhase>=2 && !carryPicked) {
            Pellet* treasure=pc_p2_cave_items_pellet_for("treasure_water");
            Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);
                if(treasure&&p&&p->isAlive()&&p->getStickObject()==treasure) {
                    carryPicked=true;std::puts("P2_CAVE_ROUTE_PICKUP item=treasure_water attachment=ordinary");std::fflush(nullptr);break;
                }
            }
        }
        if(observed%120==0) {
            Pellet* p=pc_p2_cave_items_pellet_for("treasure_water");
            std::printf("P2_CAVE_ROUTE_PROGRESS phase=%d point=%d navi=%.2f,%.2f alive=%d following=%d delivered=%d treasure=%.2f,%.2f cursor=%.2f,%.2f\n",
                routePhase,routePoint,n->mSRT.t.x,n->mSRT.t.z,alivePikis(),following(),pc_p2_cave_items_delivered(),p?p->mSRT.t.x:0,p?p->mSRT.t.z:0,n->mCursorWorldPos.x,n->mCursorWorldPos.z);
            Iterator it(pikiMgr);int i=0;CI_LOOP(it) {Piki* actor=static_cast<Piki*>(*it);if(actor&&actor->isAlive())std::printf("P2_CAVE_ROUTE_SQUAD i=%d x=%.2f z=%.2f mode=%d state=%d\n",i++,actor->mSRT.t.x,actor->mSRT.t.z,int(actor->mMode),actor->getState());}
            std::fflush(nullptr);
        }
        if(routePhase==0) {
            static const float gatherRoute[][2]={{0,-100},{100,-100},{100,100},{0,100}};
            if(routePoint<4) {
                if(walkTo(n,gatherRoute[routePoint][0],gatherRoute[routePoint][1])) {++routePoint;phaseTick=observed;}
                return;
            }
            if(observed-phaseTick<90) {gatherAtCursor(n);return;}
            pc_p2_input_script_set(1,0);
            if(observed-phaseTick>=105) {require(following()>0,"scripted whistle gathered no followers");routePhase=1;routePoint=0;}
            return;
        }
        if(routePhase==4) {
            pc_p2_input_script_set(1,0);routePhase=5;routePoint=0;
            return;
        }
        if(routePhase==1 || routePhase==5) {
            static const float outward[][2]={{100,100},{100,-100},{0,-100},{0,-200},{0,-300},{0,-400},{0,-480}};
            static const float exitRoute[][2]={{0,-400},{0,-300},{0,-200},{0,-100},{100,-100},{100,0},{200,0},{300,0},{400,0},{500,0},{600,0},{700,0},{800,0},{800,100}};
            const auto* path=routePhase==1?outward:exitRoute;const int count=routePhase==1?7:14;
            if(walkTo(n,path[routePoint][0],path[routePoint][1])) {
                std::printf("P2_CAVE_ROUTE_WAYPOINT phase=%d point=%d x=%.2f z=%.2f\n",routePhase,routePoint,n->mSRT.t.x,n->mSRT.t.z);std::fflush(nullptr);
                if(++routePoint==count) {++routePhase;phaseTick=observed;}
            }
            return;
        }
        if(routePhase==2) {
            const int elapsed=observed-phaseTick;
            pc_p2_input_script_set(1,elapsed==241?KeyConfig::_instance->mDisbandKey.mBind:0);
            int sx=0,sy=0;
            if(elapsed>=60 && elapsed<240) {
                Pellet* treasure=pc_p2_cave_items_pellet_for("treasure_water");
                if(treasure&&!carryPicked) {
                    const float dx=treasure->mSRT.t.x-n->mSRT.t.x,dz=treasure->mSRT.t.z-n->mSRT.t.z;
                    const float distance=std::sqrt(dx*dx+dz*dz);
                    const Vector3f& axis=n->controlCamera()->mViewXAxis;
                    if(distance>1) {sx=int(std::lround(65*(dx*axis.x+dz*axis.z)/distance));sy=int(std::lround(65*(dx*axis.z-dz*axis.x)/distance));}
                }
            }
            pc_p2_input_script_set_sub(1,sx,sy);
            if(elapsed>=270) {routePhase=3;phaseTick=observed;}
            return;
        }
        if(routePhase==3) {
            pc_p2_input_script_set(1,0);
            Pellet* treasure=pc_p2_cave_items_pellet_for("treasure_water");
            Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);
                if(treasure&&p&&p->isAlive()&&p->getStickObject()==treasure&&!carryPicked) {
                    carryPicked=true;std::puts("P2_CAVE_ROUTE_PICKUP item=treasure_water attachment=ordinary");std::fflush(nullptr);
                }
            }
            if(pc_p2_cave_items_delivered()==1) {
                require(carryPicked,"delivery without observed pickup");
                std::puts("P2_CAVE_ROUTE_DELIVERED count=1 source=native_pod");std::fflush(nullptr);
                routePhase=4;phaseTick=observed;
            }
            return;
        }
        if(routePhase==6) {
            pc_p2_input_script_set(1,0);
            require(pc_p2_cave_items_delivered()==1,"delivery count changed");
            if(pc_p2_cave_checkpoint(false)) {
                std::printf("P2_CAVE_ROUTE_CHECKPOINT survivors=%d controller_traversal=1\n",alivePikis());std::fflush(nullptr);
                require(pc_p2_cave_exit_after_checkpoint(),"native exit unavailable");
            }
        }
    }
    const std::string scenario = std::getenv("P2_CAVE_TEST_SCENARIO") ? std::getenv("P2_CAVE_TEST_SCENARIO") : "boot";
    void require(bool yes, const char* why) { if (!yes) { std::printf("FAIL CAVE_PLAYABLE %s\n",why); std::fflush(nullptr); std::_Exit(1); } }
    int blues() {
        int count=0; Iterator it(pikiMgr); CI_LOOP(it) { Piki* p=static_cast<Piki*>(*it); if(p && p->isAlive() && pc_p2_species(p)==0) ++count; } return count;
    }
    void pass(const char* marker) { std::puts(marker); std::fflush(nullptr); std::_Exit(0); }
    void scenarioTick(Navi* n) {
        if (observed < 60) return;
        if (!positioned && scenario != "restore") require(alivePikis()==20,"fresh starting squad is not20");
        if(scenario=="delivery_route") {deliveryRoute(n);return;}
        if (scenario=="boot") { require(pc_p2_cave_bud_count()==2,"two buds missing"); require(pc_p2_cave_items_spawned()==2,"two treasure actors missing"); pass("PASS CAVE_PLAYABLE_BOOT"); }
        if (scenario=="restore") { require(blues()>0,"blue squad not restored"); require(alivePikis()==20,"restored squad count"); pass("PASS CAVE_PLAYABLE_RESTORE"); }
        if (scenario=="carry_denial") {
            Pellet* treasure=pc_p2_cave_items_pellet_for("treasure_elec");require(treasure!=nullptr,"electric treasure missing");
            if(!positioned) {
                Vector3f anchor=treasure->getPosition();Vector3f captain(anchor.x+20,anchor.y,anchor.z-20);
                n->resetPosition(captain);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
                int i=0;Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
                    Vector3f pos(anchor.x-20+8*i,anchor.y,anchor.z+10);p->resetPosition(pos);p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);
                    p->changeMode(PikiMode::FreeMode,n);if(++i==6)break;
                }
                require(i==6,"six free actors unavailable");positioned=true;initialBlocked=pc_p2_cave_carry_carriers_dropped();
                std::puts("P2_CAVE_SCRIPTED_CARRY_SETUP actors=6 intervention=position_and_free_mode attachments=ordinary_search");std::fflush(nullptr);
            }
            Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->getStickObject()==treasure) {
                if(!carryPicked) {carryPicked=true;std::puts("P2_CAVE_ORDINARY_PICKUP_OBSERVED item=treasure_elec");std::fflush(nullptr);}break;
            }}
            if(carryPicked && pc_p2_cave_carry_carriers_dropped()>initialBlocked) {
                require(pc_p2_cave_items_delivered()==0,"blocked treasure was credited");pass("PASS CAVE_PLAYABLE_CARRY_DENIAL");
            }
            return;
        }
        if (scenario=="barrier") {
            if(!positioned) {
                const auto* plan=pc_p2_cave_carry_plan();require(plan!=nullptr,"carry plan missing");
                float x=0,z=0; bool found=false;
                for(const auto& door:plan->doors) if(door.carry_block=="elec" && pc_p2_cave_carry_door_pos(door.id.c_str(),&x,&z)) {found=true;break;}
                require(found,"electric door missing");
                initialBlocked=pc_p2_cave_carry_blocked(); int i=0;
                Iterator it(pikiMgr); CI_LOOP(it) { Piki* p=static_cast<Piki*>(*it); if(!p||!p->isAlive())continue;
                    Vector3f pos(x-45.0f+18.0f*i,0,z);p->resetPosition(pos);p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);
                    if(++i==6)break;
                }
                require(i==6,"six actors unavailable");positioned=true;
                std::puts("P2_CAVE_SCRIPTED_BARRIER_SETUP actors=6 width=90 intervention=position_only");std::fflush(nullptr);
            } else if(pc_p2_cave_carry_blocked()-initialBlocked>=6) pass("PASS CAVE_PLAYABLE_BARRIER_REACTIONS");
            return;
        }
        require(scenario=="blue_checkpoint","unknown scenario");
        if(!positioned) {
            Vector3f bud;require(pc_p2_cave_bud_position("blue",bud),"blue bud missing");
            Vector3f pos(bud.x+65,bud.y,bud.z-65);n->resetPosition(pos);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
            positioned=true;std::puts("P2_CAVE_SCRIPTED_THROW_SETUP intervention=captain_position_and_throw_events species_writes=0");
        }
        if(blues()>0 && pc_p2_cave_bud_conversions()>0 && !pc_p2_cave_bud_pending()) {
            if(!exitPositioned) {
                Vector3f pos(800,0,100);n->resetPosition(pos);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);exitPositioned=true;
                std::printf("P2_CAVE_SCRIPTED_EXIT_SETUP blue=%d intervention=captain_position natural_traversal=0\n",blues());
            }
            if(pc_p2_cave_checkpoint(false)) {require(alivePikis()==20,"conversion lost squad");pass("PASS CAVE_PLAYABLE_BLUE_CHECKPOINT");}
            return;
        }
        if(throws<5 && observed-lastThrow>=90) {
            n->findNextThrowPiki();Piki* p=n->mNextThrowPiki;
            if(p && p->isAlive() && p->getState()==PIKISTATE_Normal && p->isThrowable()) {
                Vector3f aim;require(pc_p2_cave_bud_position("blue",aim),"blue bud unavailable");
                p->mFSM->transit(p,PIKISTATE_Flying);n->throwPiki(p,aim);++throws;lastThrow=observed;
                std::printf("P2_CAVE_SCRIPTED_THROW ordinal=%d\n",throws);std::fflush(nullptr);
            }
        }
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
    nodeMgr = new NodeMgr();
    gsys->run(new CaveGuardedBootApp());
    return 0;
}
