// Private real-GL Waterwraith/Tyre visual runtime fixture (#175/#443). This
// file is compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); it is not part of the game target. Boots
// the frozen host with --experimental-pikmin2-room, loads the two-species
// sampled-pose bank (P2_WATERWRAITH_VISUAL_1), loops one clip per species,
// draws and captures a frame. Display slice only: no source actor, AI,
// ownership or gameplay.

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
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "pc_p2_waterwraith_visual.h"
#include "pc_p2_waterwraith_host.h"

namespace {
constexpr float kDt = 1.0f / 30.0f;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL WATERWRAITH_RUNTIME %s\n", message);
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

class WaterwraithApp final : public PlugPikiApp {
    int frames = 0;
    int visualFrames = 0;
    bool setup = false;
    bool captured = false;
    float ground = 0.0f;
    P2WaterwraithHostSeam seam;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 3600, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) {
            return result;
        }
        Navi* navi = naviMgr->getNavi();
        if (!setup) {
            navi->resetPosition(Vector3f(0, 0, -250));
            navi->mFaceDirection = 0;
            navi->mSRT.r.set(0, 0, 0);
            ground = mapMgr ? mapMgr->getMinY(0, 0, false) : 0.0f;
            if (!std::isfinite(ground)) {
                ground = 0.0f;
            }
            require(pc_p2_waterwraith_visual_setup("p2-waterwraith-visual.txt"), "visual setup");
            require(pc_p2_waterwraith_visual_species_count() == 2, "species count");
            require(pc_p2_waterwraith_visual_play("BlackMan", "kagebozu_walk", true),
                    "BlackMan walk play");
            require(pc_p2_waterwraith_visual_play("Tyre", "tyre_move", true), "Tyre move play");
            require(p2_waterwraith_host_setup(seam), "host setup");
            require(seam.rig.alive() && seam.rig.attachedToOwner(), "roller birth");
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int windowWidth = 0, windowHeight = 0, windowX = 0, windowY = 0;
            SDL_GetWindowSize(window, &windowWidth, &windowHeight);
            SDL_GetWindowPosition(window, &windowX, &windowY);
            require(windowWidth == 960 && windowHeight == 540, "window size 960x540");
            std::printf("P2_WATERWRAITH_WINDOW size=%dx%d pos=%d,%d\n", windowWidth, windowHeight,
                        windowX, windowY);
            std::printf("P2_WATERWRAITH_VISUAL_PLAY BlackMan=kagebozu_walk Tyre=tyre_move\n");
            setup = true;
        }
        require(pc_p2_waterwraith_visual_update() == 2, "visual update");
        p2_waterwraith_host_tick(seam, kDt);
        ++visualFrames;
        return result;
    }

    void draw(Graphics& gfx) override
    {
        PlugPikiApp::draw(gfx);
        if (!setup) {
            return;
        }
        // BlackMan walks the host route; the rig-owned Tyre child follows at
        // the pushed position with the derived roll angle applied.
        const P2WaterwraithVec3 roller = seam.rig.position();
        Matrix4f wraithWorld;
        wraithWorld.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, seam.facing, 0.0f),
                            Vector3f(seam.x, seam.y, seam.z));
        Matrix4f tyreWorld;
        tyreWorld.makeSRT(Vector3f(1.0f, 1.0f, 1.0f),
                          Vector3f(0.0f, 0.0f, seam.rig.rollAngle()),
                          Vector3f(roller.x, roller.y, roller.z));
        const int wraithDrawn =
            pc_p2_waterwraith_visual_draw_species(gfx, "BlackMan", wraithWorld);
        const int tyreDrawn = pc_p2_waterwraith_visual_draw_species(gfx, "Tyre", tyreWorld);
        require(wraithDrawn == 1 && tyreDrawn == 1, "visual draw");
        if (visualFrames >= 90 && !captured) {
            require(seam.rig.travelledDistance() > 0.0f, "roller travelled");
            require(seam.rig.rollAngle() > 0.0f, "roller rolled");
            std::printf("P2_WATERWRAITH_HOST_PASS ticks=%llu distance=%.3f roll=%.4f phase=%s\n",
                        (unsigned long long)seam.ticks, seam.rig.travelledDistance(),
                        seam.rig.rollAngle(),
                        seam.rig.tyrePhase() == P2TYRE_Move ? "Move" : "Freeze");
            capture("waterwraith-visual.ppm");
            captured = true;
            std::puts("PASS WATERWRAITH_RUNTIME");
            std::fflush(stdout);
            std::_Exit(0);
        }
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
    require(pc_window_init("Waterwraith visual runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new WaterwraithApp());
    return 0;
}
