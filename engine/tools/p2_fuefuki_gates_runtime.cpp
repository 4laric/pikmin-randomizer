// Private real-GL Fuefuki gate fixture, issue #245. Compiled by the isolated
// fixture build only; runs on a staged arena where the Napkid 11 placement
// vehicle births through the real generator and `pc_p2_hardlanes` binds it.
//
// Covers the three remaining lane gates in one real-GL run:
//   * movement/animation: samples the bound P1 Napkid host position AND the lane
//     FSM state + converted motion clip/pose counter across many ticks. The host
//     (P1 Napkid, grounded-seek labelled) and the lane component (FSM state ->
//     converted clip, motion pose) are logged separately.
//   * attacks/receivers: the ordinary engine InteractAttack::actTeki receiver
//     delivers Pikmin attacks to the live vehicle; the lane hook records the hit
//     and the fixture observes the target's real mHealth drop.
//   * cleanup/re-entry: after the natural death the stage-boundary reset seam
//     (pc_p2_reset_all_teki, the exact call GameCoreSection::exitStage makes) is
//     driven, then the real generator re-births a fresh vehicle and
//     pc_p2_hardlanes_setup() re-binds it, proving no stale pointer survives.
//
// Fixture concessions are labelled inline: the squad is placed on a ring around
// the grounded vehicle (engineered placement; the attack itself is the ordinary
// Piki -> InteractAttack path) and the vehicle is grounded by the lane's
// preview-only engagement seal (no source Fuefuki actor exists, #186/#128).

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
#include "Generator.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "pc_p2_teki_lifetime.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "teki.h"
#include "pc_p2_hardlanes.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
int gFrames = 0;
int gPhase = 0;
Teki* gVehicle = nullptr;
Generator* gGenerator = nullptr;
Vector3f gMoveStart;
float gMoveMax = 0.0f;
int gMoveFrames = 0;
int gAttackFrames = 0;
float gHealthAtPhase2 = -1.0f;
int gDeathFrames = 0;
bool gAttackStaged = false;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL FUEFUKI_GATES %s\n", message);
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

float xzDist(const Vector3f& a, const Vector3f& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return speedy_sqrtf(dx * dx + dz * dz);
}

// Labelled fixture placement (engineered, not natural recruitment): park the
// captain beyond the 250u join-party range and release the squad in FreeMode on
// a ring around the grounded vehicle so Piki::graspSituation -> AttackMode emits
// the ordinary InteractAttack receiver.
void stageAttackers(float vx, float vz)
{
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    require(navi != nullptr, "captain missing for attack staging");
    const float ground = mapMgr->getMinY(vx, vz, false);
    navi->resetPosition(Vector3f(vx + 300.0f, ground, vz + 300.0f));
    navi->mVelocity.set(0.0f, 0.0f, 0.0f);
    int placed = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it)
    {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        if (placed >= 12) break;
        const float angle = float(placed) * 2.0f * 3.14159265358979323846f / 12.0f;
        Vector3f spot(vx + 42.0f * std::sin(angle), 0.0f, vz + 42.0f * std::cos(angle));
        spot.y = mapMgr->getMinY(spot.x, spot.z, true) + 2.0f;
        piki->resetPosition(spot);
        piki->mFSM->transit(piki, PIKISTATE_Normal);
        piki->changeMode(PikiMode::FreeMode, navi);
        ++placed;
    }
    std::printf("P2_FUEFUKI_GATES_ATTACK_STAGE placed=%d\n", placed);
    std::fflush(stdout);
}
} // namespace

class GatesApp final : public PlugPikiApp {
public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++gFrames < 14000, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if ((!pc_p2_preview_ready() && !pc_p2_preview_cargo_free_ready()) || !naviMgr
            || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)
            return result;
        switch (gPhase) {
        case 0: setup(); break;
        case 1: movementPhase(); break;
        case 2: attackPhase(); break;
        case 3: deathPhase(); break;
        }
        return result;
    }

private:
    void setup()
    {
        require(pc_p2_hardlanes_fuefuki_ready(), "hardlane Fuefuki not bound to a vehicle");
        gVehicle = findVehicle();
        require(gVehicle != nullptr, "placement vehicle (Napkid 245001) not found");
        gGenerator = pc_p2_hardlanes_fuefuki_generator_object();
        require(gGenerator != nullptr, "bound vehicle generator not captured");
        float x = 0.0f, y = 0.0f, z = 0.0f;
        require(pc_p2_hardlanes_fuefuki_vehicle_position(x, y, z), "vehicle position");
        gMoveStart = Vector3f(x, y, z);
        std::printf("P2_FUEFUKI_GATES_READY host=%.2f,%.2f,%.2f state=%d clip=%s motion=%d\n",
                    x, y, z, pc_p2_hardlanes_fuefuki_motion_state(),
                    pc_p2_hardlanes_fuefuki_motion_clip(),
                    pc_p2_hardlanes_fuefuki_motion_pose() >= 0 ? 1 : 0);
        std::fflush(stdout);
        gPhase = 1;
    }

    // Gate 2: the P1 Napkid host moves over time (grounded seek) AND the lane FSM
    // state/clip/pose counter advances; both are logged across many ticks.
    void movementPhase()
    {
        float x = 0.0f, y = 0.0f, z = 0.0f;
        if (pc_p2_hardlanes_fuefuki_vehicle_position(x, y, z)) {
            gMoveMax = std::fmax(gMoveMax, xzDist(Vector3f(x, y, z), gMoveStart));
        }
        ++gMoveFrames;
        if (gMoveFrames % 10 == 0) {
            std::printf("P2_FUEFUKI_GATES_MOVE frame=%d host=%.2f,%.2f,%.2f moved=%.2f "
                        "fsm=%d clip=%s pose=%d lane_ticks=%lu\n",
                        gMoveFrames, x, y, z, gMoveMax,
                        pc_p2_hardlanes_fuefuki_motion_state(),
                        pc_p2_hardlanes_fuefuki_motion_clip(),
                        pc_p2_hardlanes_fuefuki_motion_pose(),
                        pc_p2_hardlanes_fuefuki_tick_count());
            std::fflush(stdout);
        }
        if (gMoveFrames >= 180) {
            require(gMoveMax >= 5.0f, "bound host did not move");
            require(pc_p2_hardlanes_fuefuki_tick_count() > 0, "lane FSM never ticked");
            std::printf("P2_FUEFUKI_GATES_MOVE_SUMMARY host_moved=%.2f frames=%d "
                        "lane_ticks=%lu final_state=%d final_clip=%s final_pose=%d\n",
                        gMoveMax, gMoveFrames, pc_p2_hardlanes_fuefuki_tick_count(),
                        pc_p2_hardlanes_fuefuki_motion_state(),
                        pc_p2_hardlanes_fuefuki_motion_clip(),
                        pc_p2_hardlanes_fuefuki_motion_pose());
            std::fflush(stdout);
            gPhase = 2;
        }
    }

    // Gate 3: real engine InteractAttack receiver on the live vehicle changing its
    // health. The lane hook prints P2_FUEFUKI_HIT; hardlanes update prints
    // P2_FUEFUKI_HIT_APPLY on the health drop.
    void attackPhase()
    {
        if (!gAttackStaged) {
            gAttackStaged = true;
            gHealthAtPhase2 = gVehicle ? gVehicle->mHealth : -1.0f;
            float x = 0.0f, y = 0.0f, z = 0.0f;
            require(pc_p2_hardlanes_fuefuki_vehicle_position(x, y, z), "vehicle position");
            stageAttackers(x, z);
        }
        ++gAttackFrames;
        const unsigned hits = pc_p2_hardlanes_fuefuki_hit_count();
        if (hits > 0 && gVehicle && gVehicle->mHealth < gHealthAtPhase2 - 0.01f) {
            std::printf("P2_FUEFUKI_GATES_ATTACK hits=%u health_before=%.2f health_after=%.2f\n",
                        hits, gHealthAtPhase2, gVehicle->mHealth);
            std::fflush(stdout);
            gPhase = 3;
            return;
        }
        require(gAttackFrames < 3600, "no natural attack landed on the vehicle");
    }

    // Death by the ordinary attack drain, then the gate-6 forget/reset/re-entry.
    void deathPhase()
    {
        ++gDeathFrames;
        if (gVehicle && (!gVehicle->isAlive() || gVehicle->mHealth <= 0.0f)) {
            std::printf("P2_FUEFUKI_GATES_DEATH health=%.2f frames=%d\n",
                        gVehicle->mHealth, gDeathFrames);
            std::fflush(stdout);
            cleanupPhase();
            return;
        }
        require(gDeathFrames < 3600, "vehicle did not die from the natural attack drain");
    }

    void cleanupPhase()
    {
        const unsigned forgetBefore = pc_p2_hardlanes_fuefuki_forget_count();
        const unsigned resetBefore = pc_p2_hardlanes_fuefuki_reset_count();
        void* const oldVehicle = static_cast<void*>(gVehicle);
        // Real stage-boundary teardown (GameCoreSection::exitStage calls exactly
        // this) then the real scene-enter bind seam: a scene re-entry.
        pc_p2_reset_all_teki();
        require(!pc_p2_hardlanes_fuefuki_ready(), "reset left a bound vehicle pointer");
        require(gGenerator && gGenerator->mGenType, "generator lost across reset");
        gGenerator->mGenType->init(gGenerator);
        Teki* fresh = static_cast<Teki*>(gGenerator->mLatestSpawnCreature);
        require(fresh != nullptr, "generator rebirth produced no actor");
        require(static_cast<void*>(fresh) != oldVehicle,
                "allocator reused the dead vehicle address; stale proof inconclusive");
        pc_p2_hardlanes_setup();
        require(pc_p2_hardlanes_fuefuki_ready(), "re-entry did not bind the fresh vehicle");
        require(pc_p2_hardlanes_fuefuki_motion_state() >= 0, "fresh vehicle has no lane FSM");
        std::printf("P2_FUEFUKI_REENTRY old=%p new=%p stale=0 fresh=1 forget=%u reset=%u\n",
                    oldVehicle, static_cast<void*>(fresh),
                    pc_p2_hardlanes_fuefuki_forget_count(),
                    pc_p2_hardlanes_fuefuki_reset_count());
        std::printf("P2_FUEFUKI_GATES_CLEANUP forget_delta=%u reset_delta=%u fresh_state=%d\n",
                    pc_p2_hardlanes_fuefuki_forget_count() - forgetBefore,
                    pc_p2_hardlanes_fuefuki_reset_count() - resetBefore,
                    pc_p2_hardlanes_fuefuki_motion_state());
        std::printf("PASS FUEFUKI_GATES movement=1 attacks=1 cleanup=1\n");
        std::fflush(stdout);
        std::_Exit(0);
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
    require(pc_window_init("Fuefuki gate fixture", 960, 540), "window init");
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0; SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{ 0, 0, 0, 0 }; SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_FUEFUKI_GATES_WINDOW size=%dx%d centered=%d\n",
                    width, height, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new GatesApp());
    return 0;
}
