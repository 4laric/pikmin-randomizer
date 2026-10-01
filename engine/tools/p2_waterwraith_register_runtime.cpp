// Private real-GL Waterwraith REGISTER runtime fixture (#443 / parent #175).
// Compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); it is not part of the game target.
//
// Unlike the actor/visual fixtures, this one does NOT drive the actor itself:
// it boots the frozen host with --experimental-pikmin2-room and lets the real
// engine preview setup install the lane-31 registration seam
// (pc_p2_preview_setup -> pc_p2_hardlanes_setup -> pc_p2_waterwraith_register_*).
// The engine update tick and draw path then advance and render the
// source-correct BlackMan + Tyre actor. The fixture observes the register
// accessors, captures a frame and reports ticks/distance/roll.

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

#include "pc_p2_waterwraith_register.h"

namespace {
constexpr int kTargetTicks = 90;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL WATERWRAITH_REGISTER_RUNTIME %s\n", message);
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

class WaterwraithRegisterApp final : public PlugPikiApp {
    int frames = 0;
    bool windowPrinted = false;
    bool readyPrinted = false;
    bool captured = false;
    bool naviMoved = false;

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

        // The register seam is installed during preview setup; it must be ready
        // as soon as the room preview is.
        require(pc_p2_waterwraith_register_ready(),
                "register seam not installed (missing p2-waterwraith-actor.txt?)");

        Navi* navi = naviMgr->getNavi();
        if (!naviMoved) {
            navi->resetPosition(Vector3f(0, 0, -250));
            navi->mFaceDirection = 0;
            navi->mSRT.r.set(0, 0, 0);
            naviMoved = true;
        }
        if (!windowPrinted) {
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int windowWidth = 0, windowHeight = 0;
            SDL_GetWindowSize(window, &windowWidth, &windowHeight);
            require(windowWidth == 960 && windowHeight == 540, "window size 960x540");
            std::printf("P2_WATERWRAITH_REGISTER_WINDOW size=960x540\n");
            windowPrinted = true;
        }
        if (!readyPrinted) {
            std::printf("P2_WATERWRAITH_REGISTER_READY\n");
            readyPrinted = true;
        }
        return result;
    }

    void draw(Graphics& gfx) override
    {
        PlugPikiApp::draw(gfx);
        if (!readyPrinted || captured) {
            return;
        }
        if (pc_p2_waterwraith_register_ticks() < static_cast<std::uint64_t>(kTargetTicks)) {
            return;
        }
        require(pc_p2_waterwraith_register_distance() > 0.0f, "roller travelled");
        require(pc_p2_waterwraith_register_roll() > 0.0f, "roller rolled");
        capture("waterwraith-register.ppm");
        std::printf("P2_WATERWRAITH_REGISTER_PASS ticks=%llu distance=%.3f roll=%.4f\n",
                    (unsigned long long)pc_p2_waterwraith_register_ticks(),
                    pc_p2_waterwraith_register_distance(),
                    pc_p2_waterwraith_register_roll());
        captured = true;
        std::puts("PASS WATERWRAITH_REGISTER_RUNTIME");
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
    require(pc_window_init("Waterwraith register runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new WaterwraithRegisterApp());
    return 0;
}
