// Private Frog family-draw specular acceptance: the corrected specular
// half-vector primitive is reached by lane 16's real family draw path, not a
// fixture-loaded model. The fixture boots the room preview so the Frog generator
// sidecar (p2-frog.txt + default.gen Teki) spawns a live Frog; tekibteki.cpp
// calls pc_p2_frog_draw, whose bracketed shape->drawshape the renderer's
// family-scope counter attributes. Nothing is injected and no material is forced.
// Never install this fixture as the player executable.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "Dolphin/gx.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "PikiMgr.h"
#include "Piki.h"
#include "MoviePlayer.h"
#include "teki.h"
#include "Traversable.h"
#include "Generator.h"
#include "Pellet.h"
#include "pc_p2_frog.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
#include "gl/pc_opengl.h"
#include "pc_gfx.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"

static void require(bool ok, const char* why) {
    if (!ok) { std::printf("FAIL FROG_DRAW_SPECULAR %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}

static std::vector<unsigned char> capture(const char* path) {
    pc_gfx_flush_batch(); glFinish();
    GLint view[4]; glGetIntegerv(GL_VIEWPORT, view);
    require(view[2] > 0 && view[3] > 0 && view[2] <= 4096 && view[3] <= 4096, "viewport");
    std::vector<unsigned char> pixels(size_t(view[2]) * view[3] * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(view[0], view[1], view[2], view[3], GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    require(glGetError() == GL_NO_ERROR, "readback");
    FILE* out = std::fopen(path, "wb"); require(out != nullptr, "capture output");
    std::fprintf(out, "P6\n%d %d\n255\n", view[2], view[3]);
    for (int y = view[3] - 1; y >= 0; --y)
        std::fwrite(pixels.data() + size_t(y) * view[2] * 3, 1, size_t(view[2]) * 3, out);
    std::fclose(out);
    return pixels;
}

class MaterialApp final : public PlugPikiApp {
    int frames = 0, ready = 0;
    Teki* frog = nullptr;
public:
    int idle() override {
        int result = PlugPikiApp::idle(); require(++frames < 15000, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr) return result;
        Navi* n = naviMgr->getNavi(); if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++ready;
        if (ready == 1) {
            int w = 0, h = 0, x = 0, y = 0, centered = 0;
            SDL_GetWindowSize(SDL_GL_GetCurrentWindow(), &w, &h);
            SDL_GetWindowPosition(SDL_GL_GetCurrentWindow(), &x, &y);
            const int display = SDL_GetWindowDisplayIndex(SDL_GL_GetCurrentWindow());
            if (display >= 0) { SDL_Rect b; if (SDL_GetDisplayBounds(display, &b) == 0)
                centered = (std::abs(x + w / 2 - (b.x + b.w / 2)) <= 16 && std::abs(y + h / 2 - (b.y + b.h / 2)) <= 16) ? 1 : 0; }
            const Uint32 flags = SDL_GetWindowFlags(SDL_GL_GetCurrentWindow());
            std::printf("FROG_DRAW_WINDOW w=%d h=%d flags=%s centered=%d\n", w, h, (flags & SDL_WINDOW_HIDDEN) ? "HIDDEN" : "SHOWN", centered);
        }
        if (!frog && ready >= 2) {
            Iterator it(tekiMgr); CI_LOOP(it) {
                Teki* a = static_cast<Teki*>(*it);
                if (a->isAlive() && a->mGenerator && a->mGenerator->_70 == 201001) { frog = a; break; }
            }
            require(frog, "frog generator actor missing");
            require(pc_p2_frog_name(static_cast<PelletView*>(frog)) != nullptr, "frog not family-registered");
            require(cameraMgr && cameraMgr->mCamera, "camera missing");
            cameraMgr->mCamera->mControlsEnabled = false;
            cameraMgr->mCamera->setTarget(frog);
            std::printf("FROG_DRAW_READY species=Frog generator=201001 registered=1\n");
        }
        if (frog && ready == 180) {
            const auto first = capture("frog-family.ppm");
            const auto again = capture("frog-family-repeat.ppm");
            const bool replay = (first == again);
            const unsigned family = pc_gfx_specular_family_draws();
            const unsigned total = pc_gfx_specular_channel_draws();
            const unsigned dircalls = pc_gfx_specular_dir_calls();
            std::printf("FROG_DRAW_SPECULAR family_specular_draws=%u total_specular_draws=%u specular_dir_calls=%u replay_equal=%d\n",
                        family, total, dircalls, replay ? 1 : 0);
            require(replay, "same-frame replay changed pixels");
            require(family >= 1, "family draw did not attribute specular channel draws");
            require(total >= 1, "scene never activated the specular channel");
            require(dircalls >= 1, "scene never initialized the specular half-vector");
            std::puts("PASS FROG_DRAW_SPECULAR");
            std::fflush(nullptr); std::_Exit(0);
        }
        std::fflush(stdout); return result;
    }
};

int main(int argc, char** argv) {
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires room preview");
    int windowWidth = 960, windowHeight = 540; bool smallWindow = true;
    if (const char* value = std::getenv("PIKMIN_P2_ROOM_WINDOW")) {
        if (!std::strcmp(value, "off") || !std::strcmp(value, "0")) smallWindow = false;
        int cw = 0, ch = 0;
        if (std::sscanf(value, "%dx%d", &cw, &ch) == 2 && cw >= 320 && ch >= 240) { windowWidth = cw; windowHeight = ch; }
    }
    if (!pc_window_init("Frog draw specular fixture", windowWidth, windowHeight)) return 3;
    pc_settings_init();
    if (smallWindow) {
        pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
        pc_window_set_window_size(windowWidth, windowHeight);
        pc_window_center();
    }
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr(); gsys->run(new MaterialApp()); return 0;
}
