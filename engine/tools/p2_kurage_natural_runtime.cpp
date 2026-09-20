// rd-p2-kurage-natural (#832): guarded natural-engagement observation fixture
// for the private-adapter Kurage (source id 57).
//
// Replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp.  It boots the isolated P2 room preview, lets
// GameCoreSection::finalSetup bind the generated source-57 actor through the
// production private adapter, stages the live red squad already in the room,
// and records whether a FreeMode P1 squad can naturally acquire and damage the
// bound adapter with NO forced input from this fixture.
//
// It deliberately does NOT call groundAndSeal, InteractAttack, InteractBury or
// any health/state write.  The production adapter itself keeps the actor
// grounded with its injected `groundAndSeal` concession
// (pc_port/pc_p2_kurage_teki.cpp:174); this fixture records that dependency and
// refuses to credit a kill that only happened because of it:
//
//   P2_KURAGE_NATURAL_ADAPTER    bound actor + airborne/grounded state
//   P2_KURAGE_NATURAL_OBSERVE    periodic health / flying / stick census
//   P2_KURAGE_NATURAL_BLOCKED    the chain stalls at target acquisition
//
// Captain safety #632 is adopted first-after-engine-idle for every observed
// tick: `p2_fixture_require_captain(GameStat::orimaDead, !navi->isAlive(),
// navi->mHealth, observed)` (canonical guard sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).  The
// captain is parked beyond the adapter's engage volume when no captain hit is
// under test, and a CAPTAIN_DOWN exits BLOCKED (86) with no PASS.
//
// Compile-checked as ${p2_kurage_natural_runtime_compile}; a real-GL run needs
// a staged p2-kurage-teki.txt arena (experimental/pikmin2_kurage_teki_stage.py)
// and is recorded as remaining work in the lane evidence.
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
#include "PikiState.h"
#include "Collision.h"
#include "MoviePlayer.h"
#include "teki.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "pc_p2_kurage_natural.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
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
    std::printf("FAIL KURAGE_NATURAL %s\n", message);
    std::fflush(stdout);
    std::_Exit(1);
}

BTeki* boundAdapter()
{
    if (!tekiMgr) return nullptr;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (teki && pc_p2_kurage_teki_is_bound(static_cast<BTeki*>(teki)))
            return static_cast<BTeki*>(teki);
    }
    return nullptr;
}

int sticksTo(const BTeki* actor)
{
    if (!pikiMgr || !actor) return 0;
    int count = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (piki && piki->isAlive() && piki->isStickTo()
            && piki->getStickObject() == static_cast<const Creature*>(actor))
            ++count;
    }
    return count;
}

class KurageNaturalApp final : public PlugPikiApp {
    int frames = 0, observed = 0, stage = 0;
    float startHealth = -1.0f, minHealth = 1.0e9f, startX = 0.0f, startZ = 0.0f;
    bool groundedByAdapter = false, acquired = false, damageSeen = false;
    BTeki* actor = nullptr;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 9000, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!naviMgr || !pikiMgr || !tekiMgr) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;

        // #632 captain safety, first after engine idle, before every observed
        // tick and before any pause/movie return.
        ++observed;
        p2_fixture_require_captain(GameStat::orimaDead, !navi->isAlive(), navi->mHealth, observed);

        if (!pc_p2_preview_ready()) return result;

        if (stage == 0) {
            actor = boundAdapter();
            require(actor != nullptr, "no bound source-57 private-adapter actor");
            startHealth = actor->mHealth;
            minHealth = startHealth;
            startX = actor->mSRT.t.x;
            startZ = actor->mSRT.t.z;
            std::printf("P2_KURAGE_NATURAL_ADAPTER generator=%u type=%d binding=private_adapter "
                        "flying=%d health=%.2f ticks=%d\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u, actor->mTekiType,
                        int(actor->isFlying()), actor->mHealth,
                        pc_p2_kurage_teki_tick_calls());
            std::fflush(stdout);

            // Park the captain beyond the adapter's engage keep range: no
            // captain hit is under test, and the squad follows on its own.
            Vector3f park(startX - 120.0f, 0.0f, startZ - 120.0f);
            park.y = mapMgr ? mapMgr->getMinY(park.x, park.z, true) : 0.0f;
            navi->resetPosition(park);
            navi->mVelocity.set(0.0f, 0.0f, 0.0f);
            std::printf("P2_KURAGE_NATURAL_PARK x=%.2f z=%.2f\n", park.x, park.z);
            std::fflush(stdout);
            stage = 1;
            return result;
        }

        // The production adapter's injected groundAndSeal clears CF_IsFlying
        // every tick (pc_p2_kurage_teki.cpp:174).  Detect that dependency: any
        // grounded frame after the adapter ticked is adapter-injected.
        if (pc_p2_kurage_teki_tick_calls() > 0 && !actor->isFlying())
            groundedByAdapter = true;
        const int stuck = sticksTo(actor);
        if (stuck > 0) acquired = true;
        if (actor->mHealth < startHealth) damageSeen = true;
        if (actor->mHealth > 0.0f && actor->mHealth < minHealth) minHealth = actor->mHealth;

        if (observed % 60 == 0) {
            std::printf("P2_KURAGE_NATURAL_OBSERVE tick=%d health=%.2f flying=%d stuck=%d "
                        "adapter_ticks=%d grounded_by_adapter=%d squad=%d\n",
                        observed, actor->mHealth, int(actor->isFlying()), stuck,
                        pc_p2_kurage_teki_tick_calls(), int(groundedByAdapter),
                        int(pikiMgr ? 1 : 0));
            std::fflush(stdout);
        }

        const bool dead = actor->mHealth <= 0.0f || !actor->isAlive();
        if (dead) {
            // A kill did happen, but only after the adapter's injected
            // grounding made the free squad able to acquire it.  That is not a
            // natural gateway and must not be credited as one.
            std::printf("P2_KURAGE_NATURAL_BLOCKED reason=%s grounded_by_adapter=%d "
                        "acquired=%d damaged=%d health=%.2f\n",
                        groundedByAdapter
                            ? "only_engagement_after_injected_grounding"
                            : "death_without_free_squad_attribution",
                        int(groundedByAdapter), int(acquired), int(damageSeen), actor->mHealth);
            std::fflush(stdout);
            std::_Exit(2);
        }

        // Timeout: no free-squad acquisition at all.
        if (observed >= 3000) {
            std::printf("P2_KURAGE_NATURAL_BLOCKED reason=%s callsite=%s "
                        "health_floor=%.2f acquired=%d adapter_ticks=%d\n",
                        p2kurage_natural::stall_token(
                            p2kurage_natural::Stall::NoEngagementFreeSquadSkipsFlying),
                        p2kurage_natural::stall_callsite(
                            p2kurage_natural::Stall::NoEngagementFreeSquadSkipsFlying),
                        minHealth, int(acquired), pc_p2_kurage_teki_tick_calls());
            std::fflush(stdout);
            std::_Exit(2);
        }
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
    if (!pc_window_init("P2 Kurage source-57 natural-engagement fixture", 960, 540)) return 3;
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
        std::printf("P2_KURAGE_NATURAL_WINDOW size=%dx%d pos=%d,%d centered=%d\n",
                    width, height, x, y, int(centered));
        std::fflush(stdout);
        require(width == 960 && height == 540 && centered, "window geometry");
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new KurageNaturalApp());
    return 0;
}
