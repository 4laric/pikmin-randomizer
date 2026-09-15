// Private real-GL Waterwraith ENCOUNTER runtime fixture (#443 / parent #175).
// Compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); it is not part of the game target.
//
// Boots the frozen host with --experimental-pikmin2-room and lets the real
// engine preview setup install the lane-31 registration seam, which now also
// drives the combat consumer (pc_p2_waterwraith_encounter). The fixture does
// NOT call the combat API directly: it only arranges live squad Pikmin near the
// registered actor (repositioning real Piki objects and converting some to
// Purple) and observes the encounter markers/stats.
//
// Coverage:
//   * Stage A (reds only adjacent): the roller crushes them (InteractFlick),
//     but non-Purple never damages the actor (`damageDealt == 0`).
//   * Stage B (Purple adjacent): Purple stuns the riding roller, accepted hits
//     deplete the Tyre health, the roller death script dismounts and removes the
//     child, and the exposed body is finished through its own death (body zero
//     -> Dead key5 stand-in corpse drop -> Dead end teardown).
//   * Cleanup/re-entry: after natural death, reset then re-setup the seam and
//     require it is ready again with restored health and no stale state.

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Matrix4f.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_purple.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "pc_p2_waterwraith_encounter.h"
#include "pc_p2_waterwraith_register.h"

namespace {
constexpr int kStageA_Frames = 45;
constexpr int kMaxFrames = 3600;
constexpr float kPurpleOffsetX[3] = { 30.0f, 0.0f, -30.0f };
constexpr float kPurpleOffsetZ[3] = { 0.0f, 30.0f, 0.0f };
constexpr float kRedOffsetX[2] = { 50.0f, -50.0f };
constexpr float kRedOffsetZ[2] = { 0.0f, 0.0f };

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL WATERWRAITH_ENCOUNTER_RUNTIME %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

void capture(const char* path)
{
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    GLint previous = 0;
    glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous);
    bind(GL_FRAMEBUFFER, 0);
    int w = 0, h = 0;
    SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &w, &h);
    std::vector<unsigned char> pixels(size_t(w) * size_t(h) * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadBuffer(GL_BACK);
    glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bind(GL_FRAMEBUFFER, previous);
    require(glGetError() == GL_NO_ERROR, "capture GL error");
    bool nonblack = false;
    for (unsigned char value : pixels) {
        nonblack |= value > 8;
    }
    require(nonblack, "empty capture");
    FILE* file = std::fopen(path, "wb");
    require(file != nullptr, "capture file");
    std::fprintf(file, "P6\n%d %d\n255\n", w, h);
    for (int y = h - 1; y >= 0; --y) {
        std::fwrite(pixels.data() + size_t(y) * w * 3, 1, size_t(w) * 3, file);
    }
    std::fclose(file);
}

class WaterwraithEncounterApp final : public PlugPikiApp {
    int frames = 0;
    bool windowPrinted = false;
    bool readyPrinted = false;
    bool stagedReds = false;
    bool convertedPurple = false;
    int stageAFrames = 0;
    bool stageAOk = false;
    bool captured = false;
    bool reentryChecked = false;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < kMaxFrames, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) {
            return result;
        }
        require(pc_p2_waterwraith_register_ready(),
                "register seam not installed (missing p2-waterwraith-actor.txt?)");

        if (!windowPrinted) {
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int windowWidth = 0, windowHeight = 0;
            SDL_GetWindowSize(window, &windowWidth, &windowHeight);
            require(windowWidth == 960 && windowHeight == 540, "window size 960x540");
            std::printf("P2_WATERWRAITH_ENCOUNTER_WINDOW size=960x540\n");
            windowPrinted = true;
        }
        if (!readyPrinted) {
            std::printf("P2_WATERWRAITH_ENCOUNTER_READY\n");
            readyPrinted = true;
        }

        const P2WaterwraithEncounterStats& stats = pc_p2_waterwraith_encounter_stats();
        const P2WaterwraithVec3 roller = pc_p2_waterwraith_register_roller_position();
        const P2WaterwraithVec3 wraith = pc_p2_waterwraith_register_wraith_position();
        const P2WaterwraithVec3 ref = pc_p2_waterwraith_register_attached() ? roller : wraith;

        // Collect a small live Piki working set once.
        static std::vector<Piki*> squad;
        if (!stagedReds) {
            if (pikiMgr) {
                Iterator iterator(pikiMgr);
                CI_LOOP(iterator) {
                    Piki* piki = static_cast<Piki*>(*iterator);
                    if (piki && piki->isAlive() && squad.size() < 8) {
                        squad.push_back(piki);
                    }
                }
            }
            stagedReds = !squad.empty();
            if (!stagedReds) {
                return result;
            }
            std::printf("P2_WATERWRAITH_ENCOUNTER_SQUAD count=%d\n", static_cast<int>(squad.size()));
        }

        // Keep two reds under the rollers (crush). This never damages the actor.
        const int redCount = 2;
        for (int i = 0; i < redCount && i < static_cast<int>(squad.size()); ++i) {
            if (!squad[i]->isAlive()) {
                continue;
            }
            squad[i]->resetPosition(Vector3f(ref.x + kRedOffsetX[i], 0.0f, ref.z + kRedOffsetZ[i]));
        }

        if (!stageAOk) {
            ++stageAFrames;
            if (stats.damageDealt != 0.0f || stats.purpleHits != 0) {
                require(false, "non-Purple squad damaged the actor");
            }
            if (stageAFrames >= kStageA_Frames) {
                require(stats.crushes > 0, "roller did not crush adjacent non-Purple Pikmin");
                stageAOk = true;
                std::printf("P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=%llu damage=%.1f\n",
                            static_cast<unsigned long long>(stats.crushes), stats.damageDealt);
            }
            return result;
        }

        // Convert three squad members to Purple and keep them adjacent.
        if (!convertedPurple) {
            for (int i = 0; i < 3 && i < static_cast<int>(squad.size()); ++i) {
                if (squad[i]->isAlive()) {
                    pc_p2_make_purple(squad[i]);
                }
            }
            convertedPurple = true;
            std::printf("P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP\n");
        }
        for (int i = 0; i < 3 && i < static_cast<int>(squad.size()); ++i) {
            if (!squad[i]->isAlive()) {
                continue;
            }
            squad[i]->resetPosition(Vector3f(ref.x + kPurpleOffsetX[i], 0.0f, ref.z + kPurpleOffsetZ[i]));
        }

        return result;
    }

    void draw(Graphics& gfx) override
    {
        PlugPikiApp::draw(gfx);
        if (!stageAOk || !convertedPurple || captured) {
            return;
        }
        const P2WaterwraithEncounterStats& stats = pc_p2_waterwraith_encounter_stats();
        // Full natural chain: stun -> roller death -> child removal -> exposed
        // body death -> corpse drop -> teardown.
        if (!(stats.stunned > 0 && stats.purpleHits > 0 && stats.damageDealt > 0.0f
              && stats.rollerZeroed && stats.childRemoved && stats.bodyZeroed
              && stats.treasureReleased && stats.killed
              && pc_p2_waterwraith_register_corpse_spawned()
              && pc_p2_waterwraith_register_finished())) {
            return;
        }

        require(pc_p2_waterwraith_register_tyre_health() <= 0.0f, "roller health not zeroed");
        require(pc_p2_waterwraith_register_body_health() <= 0.0f, "body health not zeroed");

        // Snapshot the combat counters before cleanup zeroes them.
        const P2WaterwraithEncounterStats summary = pc_p2_waterwraith_encounter_stats();
        require(summary.stunned > 0 && summary.purpleHits > 0 && summary.crushes > 0
                    && summary.damageDealt > 0.0f && summary.bodyZeroed
                    && summary.treasureReleased && summary.killed,
                "combat counters incomplete");

        // Cleanup and re-entry: tear the seam down and bring it back with no
        // stale actor/child/squad/body/corpse state.
        if (!reentryChecked) {
            pc_p2_waterwraith_register_reset();
            require(!pc_p2_waterwraith_register_ready(), "register seam did not reset");
            require(!pc_p2_waterwraith_register_finished(),
                    "finished flag did not clear on reset");
            require(!pc_p2_waterwraith_register_corpse_spawned(),
                    "corpse flag did not clear on reset");
            require(pc_p2_waterwraith_encounter_stats().stunned == 0, "encounter stats did not reset");
            require(pc_p2_waterwraith_register_setup("p2-waterwraith-actor.txt"),
                    "register seam re-setup failed");
            require(pc_p2_waterwraith_register_ready() && pc_p2_waterwraith_register_attached(),
                    "re-entry seam not ready/attached");
            require(pc_p2_waterwraith_register_body_health() > 0.0f,
                    "re-entry body health not restored");
            std::printf("P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY ready=1 attached=1\n");
            reentryChecked = true;
        }

        capture("waterwraith-encounter.ppm");
        std::printf("P2_WATERWRAITH_ENCOUNTER_PASS stuns=%llu hits=%llu crushes=%llu damage=%.1f "
                    "zeroed=1 child_removed=1 body_zeroed=1 treasure=1 kill=1\n",
                    static_cast<unsigned long long>(summary.stunned),
                    static_cast<unsigned long long>(summary.purpleHits),
                    static_cast<unsigned long long>(summary.crushes), summary.damageDealt);
        captured = true;
        std::puts("PASS WATERWRAITH_ENCOUNTER_RUNTIME");
        std::fflush(stdout);
        std::_Exit(0);
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
    require(pc_window_init("Waterwraith encounter runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new WaterwraithEncounterApp());
    return 0;
}
