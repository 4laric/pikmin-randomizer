// Private real-GL Fuefuki real-vehicle claim fixture, issue #245. Compiled by
// the isolated fixture build only; run inside the cargo-free practice arena so
// the Napkid 11 vehicle births through the real generator and `pc_p2_hardlanes`
// binds it. The fixture repositions the captain and the staged Pikmin into the
// whistle annulus (outside the 60-unit private radius, inside the 130-unit ring)
// so the lane FSM can reach Whisle, cast and claim real Pikmin, then verifies the
// follow locomotion moves them on the real vehicle.
//
// Honest scope: the vehicle is Napkid 11 (not enemy 41); the FSM is driven by
// the converted motion event table, not the source Beetle skeletal animation.

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
#include "Shape.h"
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
#include "Traversable.h"
#include "pc_p2_hardlanes.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
int gFrames = 0;
int gPhase = 0;
int gStageFrames = 0;
int gMeasureFrames = 0;
int gDeathFrames = 0;
Vector3f gVehicleStart;
std::vector<Vector3f> gHeldStart;
bool gVehicleKilled = false;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL FUEFUKI_VEHICLE %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

float xzDist(const Vector3f& a, const Vector3f& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return speedy_sqrtf(dx * dx + dz * dz);
}

void stagePlacement(float vehicleX, float vehicleZ)
{
    const float ground = mapMgr->getMinY(vehicleX, vehicleZ, false);
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi) navi->resetPosition(Vector3f(vehicleX + 400.0f, ground, vehicleZ + 400.0f));
    // Keep the first six Pikmin in the 60..130 annulus around the vehicle.
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

class VehicleApp final : public PlugPikiApp {
public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++gFrames < 2400, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if ((!pc_p2_preview_ready() && !pc_p2_preview_cargo_free_ready()) || !naviMgr
            || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) {
            return result;
        }
        switch (gPhase) {
        case 0: setup(); break;
        case 1: stagePhase(); break;
        case 2: measurePhase(); break;
        case 3: deathPhase(); break;
        }
        return result;
    }

private:
    void setup()
    {
        require(pc_p2_hardlanes_fuefuki_ready(), "hardlane Fuefuki not bound to a vehicle");
        float x = 0.0f, y = 0.0f, z = 0.0f;
        require(pc_p2_hardlanes_fuefuki_vehicle_position(x, y, z), "vehicle position");
        gVehicleStart = Vector3f(x, y, z);
        std::printf("P2_FUEFUKI_VEHICLE_RT_READY vehicle=%.1f,%.1f,%.1f state=%d\n",
                    x, y, z, pc_p2_hardlanes_fuefuki_state());
        std::fflush(stdout);
        gPhase = 1;
    }

    void stagePhase()
    {
        float x = 0.0f, y = 0.0f, z = 0.0f;
        require(pc_p2_hardlanes_fuefuki_vehicle_position(x, y, z), "vehicle position");
        stagePlacement(x, z);
        if (++gStageFrames % 30 == 0) {
            std::printf("P2_FUEFUKI_VEHICLE_RT_STAGE frames=%d state=%d held=%d\n",
                        gStageFrames, pc_p2_hardlanes_fuefuki_state(),
                        pc_p2_hardlanes_fuefuki_held_count());
            std::fflush(stdout);
        }
        require(gStageFrames < 900, "no natural claim within the staging window");
        if (pc_p2_hardlanes_fuefuki_held_count() > 0) {
            const int held = pc_p2_hardlanes_fuefuki_held_count();
            gHeldStart.clear();
            for (int i = 0; i < held; ++i) {
                Piki* piki = pc_p2_hardlanes_fuefuki_held(i);
                if (piki) gHeldStart.push_back(piki->mSRT.t);
            }
            std::printf("P2_FUEFUKI_VEHICLE_RT_CLAIM state=%d held=%d frames=%d\n",
                        pc_p2_hardlanes_fuefuki_state(), held, gStageFrames);
            std::fflush(stdout);
            gPhase = 2;
        }
    }

    void measurePhase()
    {
        ++gMeasureFrames;
        float moved = 0.0f;
        for (int i = 0; i < (int)gHeldStart.size(); ++i) {
            Piki* piki = pc_p2_hardlanes_fuefuki_held(i);
            if (piki) moved = std::fmax(moved, xzDist(piki->mSRT.t, gHeldStart[i]));
        }
        if (moved >= 12.0f || gMeasureFrames >= 90) {
            require(moved >= 5.0f, "claimed Pikmin did not move (follow locomotion)");
            std::printf("P2_FUEFUKI_VEHICLE_RT_MOVE held=%d moved=%.1f frames=%d state=%d\n",
                        (int)gHeldStart.size(), moved, gMeasureFrames,
                        pc_p2_hardlanes_fuefuki_state());
            std::fflush(stdout);
            gPhase = 3;
        }
    }

    void deathPhase()
    {
        if (!gVehicleKilled) {
            // Defeat the real placement vehicle; the FSM must route to Dead and
            // release every follower (owner-death Panic release).
            Iterator it(tekiMgr);
            CI_LOOP(it)
            {
                Teki* teki = static_cast<Teki*>(*it);
                if (teki && teki->mTekiType == TEKI_Napkid && teki->mGenerator
                    && teki->mGenerator->_70 == 245001) {
                    teki->mHealth = 0.0f;
                    gVehicleKilled = true;
                    std::printf("P2_FUEFUKI_VEHICLE_RT_KILL health=0\n");
                    std::fflush(stdout);
                    break;
                }
            }
            require(gVehicleKilled, "placement vehicle not found to defeat");
        }
        ++gDeathFrames;
        const int state = pc_p2_hardlanes_fuefuki_state();
        const int held = pc_p2_hardlanes_fuefuki_held_count();
        require(gDeathFrames < 240, "death release did not complete");
        if (state == 0 && held == 0 && gDeathFrames > 1) {
            std::printf("P2_FUEFUKI_VEHICLE_RT_DEATH state=0 held=0 frames=%d\n", gDeathFrames);
            std::printf("PASS FUEFUKI_VEHICLE_RUNTIME\n");
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
    require(pc_window_init("Fuefuki vehicle claim fixture", 960, 540), "window init");
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0; SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0}; SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_FUEFUKI_VEHICLE_RT_WINDOW size=%dx%d centered=%d\n",
                    width, height, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new VehicleApp());
    return 0;
}
