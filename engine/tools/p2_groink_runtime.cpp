// Private real-GL Groink arena fixture. This file is compiled by the isolated
// fixture build only; it is not part of the game target.
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
#include "pc_p2_groink_arena.h"
#include "pc_p2_groink_map_trace.h"
#include "pc_p2_groink_clock.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
void require(bool value, const char* message) {
    if (!value) { std::printf("FAIL GROINK_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

void capture(const char* path) {
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind != nullptr, "framebuffer entry point unavailable");
    GLint previous = 0; glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous); bind(GL_FRAMEBUFFER, 0);
    int w = 0, h = 0; SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &w, &h);
    std::vector<unsigned char> pixels(size_t(w) * size_t(h) * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1); glReadBuffer(GL_BACK);
    glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, pixels.data()); bind(GL_FRAMEBUFFER, previous);
    require(glGetError() == GL_NO_ERROR, "capture GL error");
    bool nonblack = false; for (unsigned char v : pixels) nonblack |= v > 8;
    require(nonblack, "empty capture");
    FILE* f = std::fopen(path, "wb"); require(f != nullptr, "capture file");
    std::fprintf(f, "P6\n%d %d\n255\n", w, h);
    for (int y = h - 1; y >= 0; --y) std::fwrite(pixels.data() + size_t(y) * w * 3, 1, size_t(w) * 3, f);
    std::fclose(f);
}

struct WallProbe { bool valid = false; P2GroinkVec3 center{}, velocity{}; };

class GroinkApp final : public PlugPikiApp {
    int frames = 0, sourceTicks = 0;
    bool setup = false, probes = false, fired = false, flightCapture = false, flightCaptured = false, terminalCapture = false;
    P2GroinkMapTrace trace;
    P2GroinkSourceClock clock;
    WallProbe wall;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 1800, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            clock.reset(); gameflow.mMoviePlayer->requestSkip(); return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) { clock.reset(); return result; }
        Navi* n = naviMgr->getNavi();
        if (!setup) {
            n->resetPosition(Vector3f(0, 0, -250)); n->mFaceDirection = 0; n->mSRT.r.set(0, 0, 0);
            trace.reset(mapMgr);
            require(pc_p2_groink_arena_setup("p2-groink-arena.txt"), "arena setup"); setup = true;
        }
        if (!probes) { runProbes(); probes = true; std::puts("P2_GROINK_MAP_PROBES_PASS"); trace.reset(mapMgr); }
        // The source clock is independent of presentation count; a pause drops debt.
        const int ticks = clock.step(gsys->getFrameTime(), true);
        for (int i = 0; i < ticks; ++i) {
            ++sourceTicks;
            bool fire = !fired && sourceTicks >= 40; fired |= fire;
            require(pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, fire, P2GroinkMapTrace::trace, &trace), "arena update");
            if (fire) std::printf("P2_GROINK_FIRE source_tick=%d traces=%llu\n",sourceTicks,(unsigned long long)trace.calls());
        }
        if (trace.calls() >= 3 && !flightCaptured) flightCapture = true;
        if ((trace.floors() || trace.walls()) && fired) terminalCapture = true;
        return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if (!setup) return;
        pc_p2_groink_arena_draw(gfx);
        if (flightCapture) { capture("groink-weighted-flight.ppm"); flightCapture = false; flightCaptured = true; }
        if (terminalCapture) {
            require(flightCaptured,"no flight capture");
            capture("groink-weighted-terminal.ppm");
            std::printf("P2_GROINK_FLIGHT_PASS ticks=%d traces=%llu floors=%llu walls=%llu\n",sourceTicks,(unsigned long long)trace.calls(),(unsigned long long)trace.floors(),(unsigned long long)trace.walls());
            std::puts("PASS GROINK_RUNTIME"); std::fflush(stdout); std::_Exit(0);
        }
    }
private:
    void runProbes() {
        require(mapMgr && mapMgr->mMapModel, "map unavailable");
        float ground = mapMgr->getMinY(0, 0, false); require(std::isfinite(ground), "center ground unavailable");
        P2GroinkTraceResult result{};
        require(P2GroinkMapTrace::trace(&trace, {0, ground + 15, 0}, {0, -300, 0}, P2GroinkPolicy::kSourceDelta, P2GroinkPolicy::kShellRadius, result), "center trace");
        std::printf("P2_GROINK_FLOOR_PROBE ground=%.6f center=%.6f floor=%d\n",ground,result.position.y,result.floor);
        require(result.floor && std::fabs(result.position.y - (ground + 10)) < 0.25f, "center floor conversion");
        require(P2GroinkMapTrace::trace(&trace, {0, ground + 100, 0}, {0, 0, 0}, P2GroinkPolicy::kSourceDelta, P2GroinkPolicy::kShellRadius, result), "free trace");
        require(!result.floor && !result.wall, "free center collision");
        Shape* model = mapMgr->mMapModel;
        for (int i = 0; i < model->mTriCount && !wall.valid; ++i) {
            const CollTriInfo& tri = model->mTriList[i];
            const Vector3f& a = model->mVertexList[tri.mVertexIndices[0]];
            const Vector3f& b = model->mVertexList[tri.mVertexIndices[1]];
            const Vector3f& c = model->mVertexList[tri.mVertexIndices[2]];
            Vector3f center((a.x + b.x + c.x) / 3.0f,
                            (a.y + b.y + c.y) / 3.0f,
                            (a.z + b.z + c.z) / 3.0f);
            const Vector3f normal = tri.mTriangle.mNormal;
            float mapGround = mapMgr->getMinY(center.x, center.z, false);
            if (std::fabs(normal.y) < 0.05f && center.y > mapGround + 15) {
                wall = {true, {center.x + normal.x * 15, center.y + normal.y * 15, center.z + normal.z * 15},
                        {-normal.x * 300, -normal.y * 300, -normal.z * 300}};
            }
        }
        require(wall.valid, "no wall probe candidate");
        require(P2GroinkMapTrace::trace(&trace, wall.center, wall.velocity, P2GroinkPolicy::kSourceDelta, P2GroinkPolicy::kShellRadius, result), "wall trace");
        require(result.wall, "wall probe did not hit");
    }
};
}

int main(int argc, char** argv) {
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    require(pc_window_init("Groink weighted runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new GroinkApp()); return 0;
}
