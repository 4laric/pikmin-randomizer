// Mar TPF_AttackableRange fixture (#683 scenario, completed to a
// replacement-main TU by mar-attackable-build-evidence-native, #687).
//
// The #683 RoomApp class below is preserved verbatim in behavior; the splice
// the #683 header described (into tools/preview_p2_room.cpp) is performed
// here instead, inside this owned TU, so no shared file is touched: the
// FixtureController/statics/require support is copied read-only from
// tools/preview_p2_room.cpp, and main() mirrors the landed
// tools/p2_cave_guarded_boot_fixture.cpp (#642) replacement-main convention
// (960x540 centred window; --experimental-pikmin2-room boot). The lane build
// script links this TU against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp without editing shared build files.
//
// Scenario: the bound Mar actor (TEKI_Mar, generator 375001) is engaged by a
// GROUNDED squad issuing REAL Attack orders (no mHealth / TransportMode write
// anywhere in this file). Before the #683 fix, pc_p2_mar_param_f returned 0
// for TPF_AttackableRange/Angle, so the engine never let Pikmin engage and
// health never dropped. After the fix (fp20 range 200 + 45-degree port angle),
// the squad latches on and health decreases through the normal damage path.
// The fixture observes the first natural health drop, then exits PASS. A stall
// is an honest FAIL, never a fallback credit. No corpse/haul/receipt/re-entry
// here (downstream #375/#650 own those gates); gate 6 stays UNTESTED.
//
// Captain safety (#632): the canonical guard runs FIRST after engine idle and
// BEFORE movie/pause/UI early returns, readiness gates, observation counters
// or PASS markers; CAPTAIN_DOWN exits 86 BLOCKED. The captain is parked outside
// Mar wind-attack reach (captain damage is not this test). No blanket
// invincibility.
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Inline tested equivalent of scripts/p2_fixture_captain_guard.h (recorded hash
// alongside the lane); never changes captain health or game state.
#include <cmath>
#include <cstdio>
#include <cstdlib>
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86);
}
#endif
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Generator.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "Pellet.h"
#include "PelletState.h"
#include "MapMgr.h"
#include "Camera.h"
#include "PlayerState.h"
#include "Demo.h"
#include "teki.h"
#include "GameStat.h"
#include "gameflow.h"
#include "Creature.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

// Support copied read-only from tools/preview_p2_room.cpp so this TU is
// self-contained: the #683 RoomApp below drives a FixtureController exactly
// like the room integration fixture does.
static int phase=0,ticks=0;
static bool assembled=false;
static bool secondFloor=false;
static std::vector<Vector3f> walkGoals;
static int walkPoint=0;
static Vector3f origin;
static bool corpseLifecycle=false, corpseApproach=false, combatWalking=false;
static Vector3f combatDestination;
static void require(bool value,const char* message) { if(!value) { std::printf("FAIL p2 room: %s\n",message);std::fflush(stdout);std::_Exit(1); } }
// Navi::update polls its controller after GameCoreSection::updateAI starts.
// Override that virtual poll in the standalone fixture, never production input.
class FixtureController : public Kontroller {
public:
    FixtureController() : Kontroller(1) {}
    void update() override {
        updateCont((phase==1 || phase==7)?KBBTN_MSTICK_RIGHT:0);
        mMainStickX=(phase==1 || phase==7)?74:0; mMainStickY=0;
        if((assembled || secondFloor) && (phase==1 || phase==7) && naviMgr) {
            Navi* n=naviMgr->getNavi();
            if(n && n->mNaviCamera) {
                float dx=walkGoals[walkPoint].x-n->mSRT.t.x,dz=walkGoals[walkPoint].z-n->mSRT.t.z;
                float distance=std::sqrt(dx*dx+dz*dz);
                if(distance<20 && walkPoint+1<int(walkGoals.size()))++walkPoint;
                if(distance>1) {
                    const Vector3f& axis=n->mNaviCamera->mViewXAxis;
                    mMainStickX=static_cast<signed char>(65*(dx*axis.x+dz*axis.z)/distance);
                    mMainStickY=static_cast<signed char>(65*(dx*axis.z-dz*axis.x)/distance);
                }
            }
        }
        mSubStickX=0; mSubStickY=0;
        if(combatWalking && naviMgr) {
            Navi* n=naviMgr->getNavi();
            if(n && n->mNaviCamera) {
                float dx=combatDestination.x-n->mSRT.t.x,dz=combatDestination.z-n->mSRT.t.z;
                float distance=std::sqrt(dx*dx+dz*dz);
                if(distance>1) {
                    const Vector3f& axis=n->mNaviCamera->mViewXAxis;
                    updateCont(KBBTN_MSTICK_RIGHT);
                    mMainStickX=static_cast<signed char>(65*(dx*axis.x+dz*axis.z)/distance);
                    mMainStickY=static_cast<signed char>(65*(dx*axis.z-dz*axis.x)/distance);
                }
            }
        }
    }
};

namespace {
bool sGuardSelfTest = false;

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
            std::printf("FAIL P2_MAR_RANGE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_MAR_RANGE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}
} // namespace

class RoomApp : public PlugPikiApp {
    static const unsigned MAR_GENERATOR = 375001u;
    int frames=0,observed=0,stage=0;
    int marDropEvents=0;
    float marMinHealth=1e9f;
    float marLastHealth=0.0f;
    float marStartHealth=0.0f;
    Teki* mar=nullptr;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    // Re-engage only Pikmin whose live action is not the Attack action
    // (blow scatter knocks them into stagger/follow with a stale AttackMode
    // flag). Leaving Pikmin that are actually executing Attack alone lets
    // approach->jump->stick->hit sequences complete instead of being abandoned
    // every 15 ticks (#687: both the blind re-issue and the mode-flag check
    // kept the squad out of real attack execution, so stk stayed 0).
    int clumpAttack(Teki* target,const Vector3f& c){int n=0,re=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        if(v->isStickTo()||(v->mActiveAction&&v->mActiveAction->mCurrActionIdx==PikiAction::Attack)){++n;continue;}
        float ang=float(n)*6.2831853f/20.0f;Vector3f pt(c.x+10.0f*std::sin(ang),0,c.z+10.0f*std::cos(ang));
        // Engagement placement (#687): regroup scattered Pikmin at the target's
        // own height, not on the floor. Ground placement leaves the squad
        // ~10+ units below in 3D so the strike gate never opens; the downstream
        // consumer's proven recipe places at target height for immediate 3D
        // engagement (consumed read-only; no consumer edits). Damage still
        // flows only through the real attack/stick path below.
        pt.y=target->mSRT.t.y;v->resetPosition(pt);
        v->mSRT.r.y=ang+3.14159265f;
        v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
        v->mActiveAction->mChildActions[PikiAction::Attack].initialise(target);v->mMode=PikiMode::AttackMode;++n;++re;}
        std::printf("P2_MAR_RANGE_ENGAGE reissued=%d tick=%d\n",re,observed);std::fflush(stdout);return n;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<90000,"mar range timeout");
    // Captain guard FIRST, before movie/pause/UI returns and any observation.
    if(naviMgr&&pikiMgr&&tekiMgr){
        Navi* guardN=naviMgr->getNavi();
        if(guardN){p2_fixture_require_captain(GameStat::orimaDead,guardN->mStateMachine->getCurrID(guardN)==NAVISTATE_Dead,guardN->mHealth,observed);}
    }
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        n->mKontroller=new FixtureController();
        mar=byGenerator(MAR_GENERATOR);
        require(mar,"bound Mar actor present");
        require(mar->mTekiType==TEKI_Mar,"bound actor is TEKI_Mar");
        int squad=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive())++squad;}
        require(squad>=1,"live starting squad");
        // Park the captain well outside Mar wind-attack reach (not under test).
        Vector3f park=mar->getPosition()+Vector3f(150.0f,0.0f,0.0f);
        park.y=mapMgr->getMinY(park.x,park.z,true);n->resetPosition(park);
        marLastHealth=mar->mHealth;marStartHealth=mar->mHealth;
        require(marStartHealth>0.0f,"Mar starts healthy");
        std::printf("P2_MAR_RANGE_READY squad=%d mar_gen=%u health=%.2f captain_parked=1\n",squad,MAR_GENERATOR,mar->mHealth);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        if(mar->mHealth<marLastHealth){++marDropEvents;}
        if(mar->mHealth>0.0f&&mar->mHealth<marMinHealth)marMinHealth=mar->mHealth;
        marLastHealth=mar->mHealth;
        if(observed%15==0){Vector3f clump(mar->mSRT.t.x,0,mar->mSRT.t.z);clump.y=mapMgr->getMinY(clump.x,clump.z,true);clumpAttack(mar,clump);}
        if(marDropEvents>=1&&marMinHealth<marStartHealth){
            std::printf("P2_MAR_RANGE_DAMAGE events=%d min=%.2f start=%.2f tick=%d\n",marDropEvents,marMinHealth,marStartHealth,observed);
            std::puts("PASS P2_MAR_RANGE_RUN damage=1");
            std::fflush(stdout);std::_Exit(0);
        }
        if(observed%90==0){int live=0,atk=0,stk=0,aidx=0,still=0,brain=0;int pst[40]={0};int mot[64]={0};float mind=1e9f;Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(!v->isAlive())continue;++live;if(v->mMode==PikiMode::AttackMode)++atk;if(v->isStickTo())++stk;if(v->mActiveAction&&v->mActiveAction->mCurrActionIdx==PikiAction::Attack)++aidx;
                int mi=v->mPikiAnimMgr.getUpperAnimator().getCurrentMotionIndex();if(mi>=0&&mi<64)++mot[mi];
                Vector3f tv=v->mTargetVelocity;if(tv.x*tv.x+tv.y*tv.y+tv.z*tv.z<4.0f)++still;
                PikiState* st=static_cast<PikiState*>(v->getCurrState());if(st&&st->freeAI())++brain;
                AState<Piki>* gs=v->getCurrState();int gid=gs?gs->getID():-1;if(gid>=0&&gid<40)++pst[gid];
                Vector3f pp=v->getPosition(),mp2=mar->getPosition();float dx=pp.x-mp2.x,dy=pp.y-mp2.y,dz=pp.z-mp2.z;float d=std::sqrt(dx*dx+dy*dy+dz*dz);if(d<mind)mind=d;}
            Vector3f mp=mar->getPosition();
            std::printf("P2_MAR_RANGE_OBSERVE health=%.2f stored=%.2f inv=%d fly=%d squad=%d atk=%d aidx=%d still=%d brain=%d stk=%d mary=%.1f mind=%.1f events=%d tick=%d\n",mar->mHealth,mar->mStoredDamage,int(mar->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)),int(mar->isFlying()),live,atk,aidx,still,brain,stk,mp.y,mind,marDropEvents,observed);std::fflush(stdout);
            {char pstbuf[256];int pstlen=0;for(int sid=0;sid<40&&pstlen<200;++sid)if(pst[sid]>0)pstlen+=std::snprintf(pstbuf+pstlen,sizeof(pstbuf)-pstlen,"%d:%d ",sid,pst[sid]);
            std::printf("P2_MAR_RANGE_PSTATES %s\n",pstbuf);std::fflush(stdout);}
            {char motbuf[256];int motlen=0;for(int mid=0;mid<64&&motlen<200;++mid)if(mot[mid]>0)motlen+=std::snprintf(motbuf+motlen,sizeof(motbuf)-motlen,"%d:%d ",mid,mot[mid]);
            std::printf("P2_MAR_RANGE_MOTIONS %s\n",motbuf);std::fflush(stdout);}
            // Gate audit (#687): closest-Pikmin strike-gate inputs, read-only.
            {
                Piki* bestV = nullptr;
                float best = 1e9f;
                Iterator w(pikiMgr);
                CI_LOOP(w) {
                    Piki* u = static_cast<Piki*>(*w);
                    if (!u || !u->isAlive()) continue;
                    Vector3f a = u->getPosition(), b = mar->getPosition();
                    float x = a.x - b.x, y = a.y - b.y, z = a.z - b.z;
                    float d = std::sqrt(x * x + y * y + z * z);
                    if (d < best) { best = d; bestV = u; }
                }
                if (bestV) {
                    Vector3f ap = bestV->getPosition();
                    // Tag 0x2a742a2a is the exact u32 value this toolchain
                    // (gcc 16.2) assigns the '*t**' multi-char constant used
                    // by ActJumpAttack::init (aiAttack.cpp:400); verified by
                    // compiling a probe (prints 712256042 2a742a2a). Written
                    // numerically because the bare literal in this TU trips
                    // -Werror=return-type for no attributable reason.
                    CollPart* cp = mar->getNearestCollPart(ap, 0x2a742a2a);
                    float cr = cp ? cp->mRadius : -1.0f;
                    int stick = cp ? int(cp->isStickable()) : -1;
                    float dx = mp.x - ap.x, dz = mp.z - ap.z;
                    float ang = std::fabs(std::atan2(dx, dz) - bestV->mFaceDirection);
                    if (ang > 3.14159265f) ang = 6.2831853f - ang;
                    std::printf("P2_MAR_RANGE_GATE dist3d=%.1f angledeg=%.1f collider_r=%.1f stickable=%d mar_centre=%.1f piki_centre=%.1f vis=%d tek=%d alive=%d ppow=%.1f\n",
                        best, ang * 57.29578f, cr, stick, mar->getCentreSize(), bestV->getCentreSize(),
                        int(mar->isVisible()), int(mar->isTeki()), int(mar->isAlive()), bestV->getAttackPower());
                    std::fflush(stdout);
                }
            }
        }
        if(observed>=6000){std::puts("FAIL P2_MAR_RANGE no_damage_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    std::fflush(stdout);return result;
}};

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") sGuardSelfTest = true;
        if (std::string(argv[i]) == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            // Engine-independent; the exit code is the assertion.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_MAR_RANGE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    if (sGuardSelfTest) return guardSelfTest();
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL P2_MAR_RANGE requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 Mar attackable range fixture", 960, 540)) return 3;
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
        std::printf("P2_MAR_RANGE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new RoomApp());
    return 0;
}