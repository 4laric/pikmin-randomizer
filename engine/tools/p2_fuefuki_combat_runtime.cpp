// Private real-GL Fuefuki natural-combat fixture, issue #245. Compiled by the
// isolated fixture build only; runs inside the cargo-free practice arena so the
// Napkid 11 vehicle births through the real generator and `pc_p2_hardlanes`
// binds it (same staging as p2_fuefuki_vehicle_runtime.cpp).
//
// First real combat run: drive one source cycle press -> Struggle -> Dead with
// follower release on the bound vehicle, and observe the receiver, the Struggle
// transit, health->Dead and the release from the log. Every injected step is
// labelled inline (injected=1) because no P1 creature emits InteractPress onto a
// Napkid (provider lane 10) and the death health is a fixture write, not natural
// attack damage.
//
// Marker grammar is consumed by experimental/pikmin2_fuefuki_combat_receipt.py.

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MoviePlayer.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "Generator.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "teki.h"
#include "Interactions.h"
#include "pc_p2_hardlanes.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
int gFrames = 0;
int gPhase = 0;
int gStageFrames = 0;
int gStruggleFrames = 0;
int gReleaseFrames = 0;
int gHeldAtDeath = 0;
Teki* gVehicle = nullptr;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL FUEFUKI_COMBAT %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

Teki* findVehicle()
{
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        Teki* teki = static_cast<Teki*>(*it);
        if (teki && teki->mTekiType == TEKI_Napkid && teki->mGenerator
            && teki->mGenerator->_70 == 245001)
            return teki;
    }
    return nullptr;
}

void stagePlacement(float vehicleX, float vehicleZ)
{
    const float ground = mapMgr->getMinY(vehicleX, vehicleZ, false);
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi) navi->resetPosition(Vector3f(vehicleX + 400.0f, ground, vehicleZ + 400.0f));
    const float ring[6][2] = { { 100, 0 }, { 0, 100 }, { -90, 0 }, { 0, -90 }, { 70, 70 }, { -70, 70 } };
    int placed = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it)
    {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        if (placed >= 6) break;
        Vector3f spot(vehicleX + ring[placed][0], 0.0f, vehicleZ + ring[placed][1]);
        spot.y = mapMgr->getMinY(spot.x, spot.z, true) + 2.0f;
        piki->resetPosition(spot);
        piki->mFSM->transit(piki, PIKISTATE_Normal);
        piki->changeMode(PikiMode::FreeMode, navi);
        ++placed;
    }
}
} // namespace

class CombatApp final : public PlugPikiApp {
public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++gFrames < 3600, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if ((!pc_p2_preview_ready() && !pc_p2_preview_cargo_free_ready()) || !naviMgr
            || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)
            return result;
        switch (gPhase) {
        case 0: setup(); break;
        case 1: stagePhase(); break;
        case 2: pressPhase(); break;
        case 3: strugglePhase(); break;
        case 4: deathPhase(); break;
        }
        return result;
    }

private:
    void setup()
    {
        require(pc_p2_hardlanes_fuefuki_ready(), "hardlane Fuefuki not bound to a vehicle");
        gVehicle = findVehicle();
        require(gVehicle != nullptr, "placement vehicle (Napkid 245001) not found");
        std::printf("P2_FUEFUKI_COMBAT_RT_READY state=%d press_count=%u\n",
                    pc_p2_hardlanes_fuefuki_state(),
                    pc_p2_hardlanes_fuefuki_press_count());
        std::fflush(stdout);
        gPhase = 1;
    }

    void stagePhase()
    {
        float x = 0.0f, y = 0.0f, z = 0.0f;
        require(pc_p2_hardlanes_fuefuki_vehicle_position(x, y, z), "vehicle position");
        stagePlacement(x, z);
        if (++gStageFrames % 60 == 0) {
            std::printf("P2_FUEFUKI_COMBAT_RT_STAGE frames=%d state=%d held=%d\n",
                        gStageFrames, pc_p2_hardlanes_fuefuki_state(),
                        pc_p2_hardlanes_fuefuki_held_count());
            std::fflush(stdout);
        }
        require(gStageFrames < 1800, "no natural claim within the staging window");
        // A live claim (Whisle cast admitted at least one in-ring Pikmin) must
        // exist before the press, so the later follower release is observable.
        if (pc_p2_hardlanes_fuefuki_held_count() > 0) gPhase = 2;
    }

    void pressPhase()
    {
        // Injected step (labelled): dispatch the engine's own InteractPress onto
        // the bound vehicle. No P1 creature does this for a Napkid, so the
        // stimulus is fixture-constructed rather than a physical Pikmin press.
        Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
        require(navi != nullptr, "captain missing for press stimulus");
        InteractPress press(navi, 0.0f);
        press.actTeki(gVehicle);
        require(pc_p2_hardlanes_fuefuki_press_count() >= 1, "press stimulus did not latch");
        std::printf("P2_FUEFUKI_COMBAT_RT_PRESS injected=1 press_count=%u state=%d held=%d\n",
                    pc_p2_hardlanes_fuefuki_press_count(),
                    pc_p2_hardlanes_fuefuki_state(),
                    pc_p2_hardlanes_fuefuki_held_count());
        std::fflush(stdout);
        gPhase = 3;
    }

    void strugglePhase()
    {
        ++gStruggleFrames;
        const int state = pc_p2_hardlanes_fuefuki_state();
        require(gStruggleFrames < 120, "no Struggle transit after real press");
        if (state == 8) {
            std::printf("P2_FUEFUKI_COMBAT_RT_STRUGGLE state=8 held=%d\n",
                        pc_p2_hardlanes_fuefuki_held_count());
            std::fflush(stdout);
            gPhase = 4;
        }
    }

    void deathPhase()
    {
        // Injected step (labelled): zero the vehicle health to route the FSM
        // Struggle -> Dead (source health<=0 exits) and release the followers.
        if (gHeldAtDeath == 0) {
            gHeldAtDeath = pc_p2_hardlanes_fuefuki_held_count();
            gVehicle->mHealth = 0.0f;
            std::printf("P2_FUEFUKI_COMBAT_RT_DEATH injected=1 state=%d held=%d\n",
                        pc_p2_hardlanes_fuefuki_state(), gHeldAtDeath);
            std::fflush(stdout);
        }
        ++gReleaseFrames;
        const int held = pc_p2_hardlanes_fuefuki_held_count();
        require(gReleaseFrames < 240, "follower release did not complete");
        if (held == 0 && gReleaseFrames > 1) {
            std::printf("P2_FUEFUKI_COMBAT_RT_RELEASE released=%d held=%d frames=%d state=%d\n",
                        gHeldAtDeath, held, gReleaseFrames,
                        pc_p2_hardlanes_fuefuki_state());
            std::printf("PASS FUEFUKI_COMBAT_RUNTIME\n");
            std::fflush(stdout);
            std::_Exit(0);
        }
    }
};

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    require(pc_window_init("Fuefuki combat fixture", 960, 540), "window init");
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0; SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{ 0, 0, 0, 0 }; SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_FUEFUKI_COMBAT_RT_WINDOW size=%dx%d centered=%d\n",
                    width, height, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new CombatApp());
    return 0;
}
