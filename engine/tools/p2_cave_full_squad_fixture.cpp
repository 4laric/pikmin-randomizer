// #1072: full-squad physical exit after ordinary water delivery.
// Staged20Blue, scripted native pad input, exit confirmation bypassed.
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

class CaveFullSquadApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool entrySeen = false, captainSeen = false, carryPicked = false;
    bool positioned = false;
    int routePhase=0, routePoint=0, phaseTick=0, settled=0, regroupPoint=0, recoveryPoint=0;
    struct Trace {Piki* actor;bool wet=false,east=false;};
    std::vector<Trace> squad;
    int crossed=0;
    float farthest(Navi* n) {
        float maximum=0;
        require(std::isfinite(n->mSRT.t.x)&&std::isfinite(n->mSRT.t.y)&&std::isfinite(n->mSRT.t.z),"nonfinite captain position");
        for(const auto& t:squad) {float dx=t.actor->mSRT.t.x-n->mSRT.t.x,dy=t.actor->mSRT.t.y-n->mSRT.t.y,dz=t.actor->mSRT.t.z-n->mSRT.t.z;maximum=std::fmax(maximum,std::sqrt(dx*dx+dy*dy+dz*dz));}
        return maximum;
    }
    bool exitHeights(Navi* n) {
        if(std::fabs(n->mSRT.t.y)>30)return false;
        for(const auto& t:squad)if(std::fabs(t.actor->mSRT.t.y)>30)return false;
        return true;
    }
    void observeSquad() {
        require(alivePikis()==20,"squad population changed");
        for(size_t i=0;i<squad.size();++i) {
            auto& t=squad[i];require(t.actor->isAlive(),"original actor lost");
            float x=t.actor->mSRT.t.x,y=t.actor->mSRT.t.y,z=t.actor->mSRT.t.z;
            require(std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z),"nonfinite original actor position");
            if(x>=350 && x<=450 && std::fabs(z)<=60 && std::fabs(y)<=30)t.wet=true;
            if(t.wet && !t.east && x>460 && std::fabs(z)<=60 && std::fabs(y)<=30) {
                t.east=true;++crossed;
                std::printf("P2_CAVE_FULL_SQUAD_CROSSED actor=%zu x=%.3f y=%.3f z=%.3f total=%d\n",i,x,y,z,crossed);std::fflush(nullptr);
            }
        }
    }
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
        pc_p2_input_script_set(1,KeyConfig::_instance->mSetCursorKey.mBind,sx,sy);
    }
    void deliveryRoute(Navi* n) {
        if(!positioned) {
            require(blues()==20,"transport fixture requires disclosed 20 Blue entry");
            positioned=true;phaseTick=observed;
            Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())squad.push_back({p});}
            require(squad.size()==20,"capture original squad");
            std::puts("P2_CAVE_ROUTE_SETUP starting_species=20_blue_staged input=scripted_controller position_writes=0 velocity_writes=0 checkpoint_confirmation=bypassed");
        }
        observeSquad();
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
            require(observed-phaseTick<1200,"ordinary whistle did not recover full squad");
            // Recall the disbanded treasure-side group first, then walk back
            // to the pod: the returned carrier is beyond whistle range here.
            if(observed-phaseTick<90) {gatherAtCursor(n);return;}
            static const float recovery[][2]={{0,-300},{0,-200},{0,-100},{100,-100},{100,0}};
            if(recoveryPoint<5) {
                if(walkTo(n,recovery[recoveryPoint][0],recovery[recoveryPoint][1]))++recoveryPoint;
                return;
            }
            if(following()!=20) {gatherAtCursor(n);return;}
            pc_p2_input_script_set(1,0);routePhase=5;routePoint=6;
            std::puts("P2_CAVE_FULL_SQUAD_RECALLED following=20");std::fflush(nullptr);
            return;
        }
        if(routePhase==1 || routePhase==5) {
            static const float outward[][2]={{100,100},{100,-100},{0,-100},{0,-200},{0,-300},{0,-400},{0,-480}};
            static const float exitRoute[][2]={{0,-400},{0,-300},{0,-200},{0,-100},{100,-100},{100,0},{200,0},{300,0},{400,0},{500,0},{600,0},{700,0},{800,0},{800,100}};
            const auto* path=routePhase==1?outward:exitRoute;const int count=routePhase==1?7:14;
            if(walkTo(n,path[routePoint][0],path[routePoint][1])) {
                // Wait for the real followers at every return waypoint. A global
                // live-actor count is not evidence of a physically arriving squad.
                if(routePhase==5 && (following()!=20 || farthest(n)>170))return;
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
            // Keep the group moving through a small diamond inside the exit.
            // Neutral formation adds a trailing offset; ordinary walking avoids
            // falsely treating that prescribed offset as a stuck squad.
            static const float regroup[][2]={{800,80},{820,100},{800,120},{780,100}};
            if(walkTo(n,regroup[regroupPoint][0],regroup[regroupPoint][1]))regroupPoint=(regroupPoint+1)%4;
            require(pc_p2_cave_items_delivered()==1,"delivery count changed");
            require(crossed==20,"not every original actor crossed the water passage");
            if(following()!=20 || farthest(n)>120 || !exitHeights(n)) {settled=0;return;}
            if(++settled<30)return;
            if(settled==30) {
                std::printf("P2_CAVE_FULL_SQUAD_ARRIVED alive=%d following=%d crossed=%d farthest=%.3f captain_x=%.3f captain_y=%.3f captain_z=%.3f\n",alivePikis(),following(),crossed,farthest(n),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);
                for(size_t i=0;i<squad.size();++i)std::printf("P2_CAVE_FULL_SQUAD_AT_EXIT actor=%zu species=%d x=%.3f y=%.3f z=%.3f mode=%d\n",i,pc_p2_species(squad[i].actor),squad[i].actor->mSRT.t.x,squad[i].actor->mSRT.t.y,squad[i].actor->mSRT.t.z,int(squad[i].actor->mMode));
                std::fflush(nullptr);
            }
            if(pc_p2_cave_checkpoint(false)) {
                std::printf("P2_CAVE_FULL_SQUAD_CHECKPOINT survivors=%d following=%d crossed=%d\n",alivePikis(),following(),crossed);std::fflush(nullptr);
                require(pc_p2_cave_exit_after_checkpoint(),"native exit unavailable");
            }
        }
    }
    const std::string scenario = std::getenv("P2_CAVE_TEST_SCENARIO") ? std::getenv("P2_CAVE_TEST_SCENARIO") : "full_squad";
    void require(bool yes, const char* why) { if (!yes) { std::printf("FAIL CAVE_PLAYABLE %s\n",why); std::fflush(nullptr); std::_Exit(1); } }
    int blues() {
        int count=0; Iterator it(pikiMgr); CI_LOOP(it) { Piki* p=static_cast<Piki*>(*it); if(p && p->isAlive() && pc_p2_species(p)==0) ++count; } return count;
    }
    void pass(const char* marker) { std::puts(marker); std::fflush(nullptr); std::_Exit(0); }
    void scenarioTick(Navi* n) {
        if(observed<60)return;
        if(scenario=="restore") {
            require(blues()==20 && alivePikis()==20,"restored full Blue squad");
            require(pc_p2_cave_items_spawned()==1,"delivered treasure not suppressed");
            pass("PASS CAVE_FULL_SQUAD_RESTORE");
        }
        require(scenario=="full_squad","unknown full-squad scenario");
        deliveryRoute(n);
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
    gsys->run(new CaveFullSquadApp());
    return 0;
}
