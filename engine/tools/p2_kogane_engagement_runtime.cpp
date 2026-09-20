// rd-p2-kogane-engagement (#835): guarded natural-engagement runtime fixture.
//
// Kogane is a finite flip/drop/escape species, not a kill/corpse enemy.
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp. It boots the staged Kogane arena (generators 219001
// kogane / 219002 wealthy / 219003 fart / 219004 P1 control, plus the
// p2-kogane-native.txt sidecar and the kogane_*.mod visual bank), stages the
// captain ONCE beside the 219001 beetle, and then drives contact ONLY through
// genuine engine throw-release event pairs -- Piki transit to PIKISTATE_Flying
// plus Navi::throwPiki toward the beetle's live position, identical to the
// KEY_Action0 release sequence in NaviThrowState::procAnimMsg (the lane-54
// #494 technique). After release each Pikmin flies ballistically under its own
// physics, lands, and its own attack AI engages the beetle on contact; the
// stick attack arrives as InteractAttack and flips the beetle through the
// native pc_p2_kogane_attacked receiver (tekiinteraction.cpp:46).
//
// It deliberately does NOT issue attack directives, reposition any Pikmin,
// pin or hold anything per frame, stimulate InteractPress/InteractAttack,
// write health/state, or touch generic Piki AI, central receipts, P2 pool
// membership or the user's game. The expected natural markers, in order:
//   P2_KOGANE_BIND generator=219001 source_id=9 ...
//   P2_KOGANE_FLIP generator=219001 source_id=9 flip=1..3 (each with a
//     P2_KOGANE_NATURAL_ATTACK line proving the InteractAttack path)
//   P2_KOGANE_DROP generator=219001 source_id=9 flip=1..3 ...
//   P2_KOGANE_ONION_RECEIPT generator=219001 flip=1..3 granted=1 ...
//   P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3 (no corpse)
// and the in-process PASS below. A driver validates the full ordering; the
// exit-0 PASS additionally requires the P1 control alive, a live squad, and
// at least one recorded throw.
//
// Captain safety #632 is adopted first-after-engine-idle for every tick:
// `p2_fixture_require_captain(GameStat::orimaDead, !navi->isAlive(),
// navi->mHealth, frames)` (canonical guard sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474),
// BEFORE movie/pause/UI early returns, readiness gates, observation counters
// or PASS markers. Policy is unprotected: the captain is staged beside the
// beetle because throws originate from him, and Kogane deals no captain damage
// (attack params zeroed, pc_p2_kogane_param_f); no health refill, revive,
// invincibility or production change is added. CAPTAIN_DOWN exits BLOCKED
// (86) with no PASS.
//
// Window baseline: 960x540 centred, verified in main like the shared fixture
// contract (P2_KOGANE_ENGAGEMENT_WINDOW). A real-GL run needs the staged arena
// in the process working directory (kogane-positions.txt + sidecar + bank);
// when the beetle is missing or unregistered (setup skipped on an unstaged
// arena) the fixture exits BLOCKED (2), never PASS.
//
// Compile-checked as ${p2_kogane_engagement_runtime_compile}; the
// replacement-main executable is produced by scripts/build_pikmin2_fixture.py
// against a completed pikmin_pc build, then launched bounded with
// scripts/run_pikmin2_fixture.py --pass-marker
// "PASS P2_KOGANE_ENGAGEMENT flips3 escape1 control_alive".
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "GameStat.h"
#include "Section.h"
#include "Generator.h"
#include "MapMgr.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "PlayerState.h"
#include "Demo.h"
#include "TekiPersonality.h"
#include "Collision.h"
#include "MoviePlayer.h"
#include "teki.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "pc_p2_kogane.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>

#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Vendored tested equivalent of scripts/p2_fixture_captain_guard.h
// (canonical sha256 d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp)
{
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick)
{
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86);
}
#endif

namespace {

void require(bool ok, const char* message)
{
    if (ok) return;
    std::printf("FAIL KOGANE_ENGAGEMENT %s\n", message);
    std::fflush(stdout);
    std::_Exit(1);
}

void blocked(const char* reason)
{
    std::printf("P2_KOGANE_ENGAGEMENT_BLOCKED reason=%s\n", reason);
    std::fflush(stdout);
    std::_Exit(2);
}

int alivePikis()
{
    int count = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it)
    {
        Creature* p = *it;
        if (p && p->isAlive()) ++count;
    }
    return count;
}

class KoganeEngagementApp final : public PlugPikiApp {
    int frames = 0, observed = 0, throws = 0, lastThrow = -10000;
    bool staged = false, escaped = false;
    Teki* beetle = nullptr;
    Teki* control = nullptr;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 15000, "engagement timeout");

        // #632 captain safety: immediately after the engine idle step, before
        // movie/pause/UI early returns, readiness gates, counters or markers.
        // The captain counts as initialized once naviMgr hands us a Navi.
        Navi* early = (naviMgr != nullptr) ? naviMgr->getNavi() : nullptr;
        if (early != nullptr) {
            p2_fixture_require_captain(GameStat::orimaDead, !early->isAlive(),
                                       early->mHealth, frames);
        }

        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr || !pikiMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;

        if (observed == 1) {
            for (int i = 0; i < DEMOFLAG_COUNT; ++i) playerState->mDemoFlags.setFlagOnly(i);
            std::ifstream input("kogane-positions.txt");
            unsigned id;
            float x, y, z;
            int count = 0;
            while (input >> id >> x >> y >> z) {
                Teki* actor = nullptr;
                int matches = 0;
                Iterator iter(tekiMgr);
                CI_LOOP(iter)
                {
                    Teki* a = static_cast<Teki*>(*iter);
                    if (a->mGenerator && a->mGenerator->_70 == id) {
                        actor = a;
                        ++matches;
                    }
                }
                require(matches == 1, "beetle roster identity");
                Vector3f birth = actor->mPersonality->mPosition;
                require(std::fabs(birth.x - x) < .02 && std::fabs(birth.y - y) < .02
                            && std::fabs(birth.z - z) < .02,
                        "beetle birth XYZ");
                std::printf("P2_KOGANE_ENGAGEMENT_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",
                            id, actor->mTekiType, birth.x, birth.y, birth.z);
                if (id == 219001) beetle = actor;
                if (id == 219004) control = actor;
                ++count;
            }
            require(count == 4, "beetle roster missing");
            require(beetle && control && beetle != control, "beetle/control identity");
            // The arena must have registered the target through production
            // setup; an unstaged arena (setup skipped) is BLOCKED, never PASS.
            if (pc_p2_kogane_source_id(static_cast<PelletView*>(beetle)) != 9) {
                blocked("target_unregistered");
            }
            // Single staged captain position beside the target birth anchor.
            // The only repositioning in the run, before any throw. Kogane
            // deals no captain damage, so this staging is unprotected
            // observation setup, not damage protection.
            Vector3f b = beetle->getPosition();
            Vector3f stagedPos(b.x - 150.0f, b.y, b.z);
            n->resetPosition(stagedPos);
            n->mVelocity.set(0, 0, 0);
            n->mTargetVelocity.set(0, 0, 0);
            staged = true;
            std::printf("P2_KOGANE_ENGAGEMENT_STAGED nx=%.3f ny=%.3f nz=%.3f "
                        "bx=%.3f by=%.3f bz=%.3f\n",
                        stagedPos.x, stagedPos.y, stagedPos.z, b.x, b.y, b.z);
            std::fflush(stdout);
        }
        if (observed == 60) {
            std::printf("P2_KOGANE_ENGAGEMENT_SQUAD pikis=%d\n", alivePikis());
            std::fflush(stdout);
            require(alivePikis() >= 1, "starting squad missing");
        }
        // Throw loop: one genuine throw-release event pair per cooldown window
        // at the beetle's live position. The engine selector picks the Pikmin;
        // ballistic flight, landing and engagement are the Pikmin's own.
        if (beetle && beetle->isAlive() && staged && !escaped && throws < 30
            && observed - lastThrow >= 180) {
            n->findNextThrowPiki();
            Piki* p = n->mNextThrowPiki;
            if (p && p->isAlive() && p->getState() == PIKISTATE_Normal && p->isThrowable()) {
                Vector3f aim = beetle->getPosition();
                p->mFSM->transit(p, PIKISTATE_Flying);
                n->throwPiki(p, aim);
                ++throws;
                lastThrow = observed;
                Vector3f d = aim;
                d.sub(n->mSRT.t);
                std::printf("P2_KOGANE_ENGAGEMENT_THROW n=%d generator=219001 dist=%.1f\n",
                            throws, d.length());
                std::fflush(stdout);
            } else {
                std::printf("P2_KOGANE_ENGAGEMENT_THROW_SKIP tick=%d\n", observed);
                std::fflush(stdout);
                lastThrow = observed - 120;
            }
        }
        if (beetle && !beetle->isAlive() && !escaped) {
            escaped = true;
            std::printf("P2_KOGANE_ENGAGEMENT_ESCAPED tick=%d throws=%d beetle_alive=0\n",
                        observed, throws);
            std::fflush(stdout);
        }
        if (throws >= 30 && !escaped && beetle && beetle->isAlive()) {
            blocked("throw_budget_exhausted_without_escape");
        }
        if (escaped) {
            require(control && control->isAlive(), "P1 control disturbed");
            require(alivePikis() >= 1, "squad extinct");
            require(throws >= 1, "no throws recorded");
            std::puts("PASS P2_KOGANE_ENGAGEMENT flips3 escape1 control_alive");
            std::fflush(stdout);
            std::_Exit(0);
        }
        std::fflush(stdout);
        return result;
    }
};

} // namespace

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    if (!pc_window_init("P2 Kogane source-9 natural-engagement fixture", 960, 540)) return 3;
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
        std::printf("P2_KOGANE_ENGAGEMENT_WINDOW size=%dx%d pos=%d,%d centered=%d\n",
                    width, height, x, y, int(centered));
        std::fflush(stdout);
        require(width == 960 && height == 540 && centered, "window geometry");
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new KoganeEngagementApp());
    return 0;
}
