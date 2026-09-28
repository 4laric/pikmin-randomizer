// Private real-GL Groink arena fixture. This file is compiled by the isolated
// fixture build only; it is not part of the game target.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "gl/pc_gfx.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MoviePlayer.h"
#include "Shape.h"
#include "Camera.h"
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
#include <fstream>
#include <sstream>
// Policies link from the pinned integration build; do not embed duplicate implementations.
#include "../pc_port/pc_p2_groink_volley.h"

namespace {
void require(bool value, const char* message) {
    if (!value) { std::printf("FAIL GROINK_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

void capture(const char* path) {
    pc_gfx_flush_batch();
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

class GroinkVolleyApp final : public PlugPikiApp {
    int frames = 0, sourceTicks = 0;
    bool setup = false, probes = false, fired = false, flightCapture = false, flightCaptured = false, terminalCapture = false;
    P2GroinkMapTrace trace;
    P2GroinkSourceClock clock;
    WallProbe wall;
    P2GroinkVolley volley;
    P2GroinkMuzzle muzzle;
    P2GroinkVec3 owner, target;
    float search = 0, radius = 0, angle = 0;
    unsigned emitted = 0, impacts = 0, primaryImpacts = 0;
    const std::array<P2GroinkVec3,3> spread{{{0.5f,0.5f,0.5f},{0,0.5f,0},{1,0.5f,1}}};
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
            n->resetPosition(Vector3f(0, 0, 100)); n->mFaceDirection = 0; n->mSRT.r.set(0, 0, 0);
            trace.reset(mapMgr);
            require(pc_p2_groink_arena_setup("p2-groink-arena.txt"), "arena setup"); loadProfile(); setup = true;
        }
        if (!probes) { runProbes(); probes = true; std::puts("P2_GROINK_MAP_PROBES_PASS"); trace.reset(mapMgr); }
        // The source clock is independent of presentation count; a pause drops debt.
        const int ticks = clock.step(gsys->getFrameTime(), true);
        for (int i = 0; i < ticks; ++i) {
            ++sourceTicks;
            require(sourceTicks < 200, "volley did not finish on terrain");
            auto aim = P2GroinkPolicy::aim(muzzle.column3,target,search,radius,P2GroinkPolicy::kSourceDelta,angle);
            require(aim.valid, "volley aim"); angle = aim.angle;
            if (sourceTicks == 40 || sourceTicks == 44) {
                require(aim.locked, "injected fire before aim lock");
                bool valid = false;
                auto rotated = p2_groink_rotate_vertical(muzzle,angle,valid);
                require(valid, "muzzle rotation");
                auto receipt = volley.emit(rotated,aim.shellSpeed,spread);
                require(receipt.valid && receipt.count == 3, "three-shell emission");
                emitted += unsigned(receipt.count); fired = true;
                require(volley.activeCount() == emitted, "expected overlapping volleys");
                std::printf("P2_GROINK_VOLLEY_FIRE tick=%d emitted=%u active=%u\n",sourceTicks,emitted,unsigned(volley.activeCount()));
            }
            require(volley.update(owner,P2GroinkPolicy::kSourceDelta,P2GroinkMapTrace::trace,&trace), "volley update");
            for (std::size_t j=0;j<volley.terminalCount();++j) {
                const auto& hit = volley.terminals()[j];
                require(hit.step.valid && (hit.step.reason == P2GroinkTerminalReason::Floor || hit.step.reason == P2GroinkTerminalReason::Wall), "non-terrain terminal");
                ++impacts; primaryImpacts += hit.primary;
                std::printf("P2_GROINK_VOLLEY_IMPACT tick=%d slot=%u primary=%d reason=%d xyz=%.3f,%.3f,%.3f\n",sourceTicks,unsigned(hit.slot),hit.primary,int(hit.step.reason),hit.step.end.x,hit.step.end.y,hit.step.end.z);
            }
        }
        if (emitted == 6 && volley.activeCount() == 6 && !flightCaptured) flightCapture = true;
        if (impacts == 6) terminalCapture = true;
        return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if (!setup) return;
        pc_p2_groink_arena_draw(gfx);
        require(gfx.mCamera != nullptr, "camera");
        for (std::size_t i=0;i<P2GroinkVolley::kCapacity;++i) {
            const auto shell = volley.shell(i);
            const Colour colors[]{Colour(255,0,0,255),Colour(0,255,0,255),Colour(0,80,255,255),
                                  Colour(255,0,255,255),Colour(255,200,0,255),Colour(0,255,255,255)};
            gfx.setColour(colors[i],true);
            if (shell.active) gfx.drawSphere(Vector3f(shell.position.x,shell.position.y,shell.position.z),10,gfx.mCamera->mLookAtMtx);
        }
        if (flightCapture) { capture("groink-volley-flight.ppm"); flightCapture = false; flightCaptured = true; }
        if (sourceTicks == 60 && volley.activeCount() == 6) capture("groink-volley-spread.ppm");
        if (terminalCapture) {
            require(flightCaptured,"no flight capture");
            capture("groink-volley-terminal.ppm");
            std::printf("P2_GROINK_FLIGHT_PASS ticks=%d traces=%llu floors=%llu walls=%llu\n",sourceTicks,(unsigned long long)trace.calls(),(unsigned long long)trace.floors(),(unsigned long long)trace.walls());
            require(primaryImpacts == 2 && volley.activeCount() == 0, "terminal accounting");
            volley.reset(); clock.reset();
            require(volley.activeCount() == 0 && volley.terminalCount() == 0, "pool reset");
            require(volley.emit(muzzle,100,spread).count == 3, "pool reuse after reset"); volley.reset();
            std::printf("P2_GROINK_VOLLEY_PASS emitted=%u impacts=%u primary=%u reset=1\n",emitted,impacts,primaryImpacts);
            std::puts("PASS GROINK_VOLLEY_RUNTIME"); std::fflush(stdout); std::_Exit(0);
        }
    }
private:
    void loadProfile() {
        // Arena setup has already validated bounds, file size and model. This
        // fixture supports yaw zero only; production owner tracking is separate.
        std::ifstream in("p2-groink-arena.txt"); std::string line, key;
        std::getline(in,line); std::getline(in,line);
        in >> key >> search >> radius;
        require(key == "params", "profile params");
        float yaw = 0;
        in >> key >> owner.x >> owner.y >> owner.z >> yaw;
        require(key == "owner" && yaw == 0, "fixture requires zero owner yaw");
        in >> key >> target.x >> target.y >> target.z;
        require(key == "target", "profile target");
        float m[12]; in >> key;
        for (float& v:m) in >> v;
        require(bool(in) && key == "muzzle", "profile muzzle");
        muzzle = {{m[0],m[4],m[8]},{m[1],m[5],m[9]},{m[2],m[6],m[10]},
                  {m[3]+owner.x,m[7]+owner.y,m[11]+owner.z}};
    }
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
    require(pc_window_init("Groink volley runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new GroinkVolleyApp()); return 0;
}
