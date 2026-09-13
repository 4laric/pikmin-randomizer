// Private real-GL BigTreasure host-seam runtime fixture, issue #246. This
// file is compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); it is not part of the game target.
// Boots the frozen host with --experimental-pikmin2-room, binds the
// lane-owned trace adapter to the real P1 static map through a dedicated
// Creature collision proxy, and runs flat-floor/free-space/vertical-wall
// probes plus elec-bounce and water-arc acceptance probes and the host-seam
// lifetime wiring (5 captured pellets + pooled attack nodes).

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Matrix4f.h"
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
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "pc_p2_bigtreasure_host.h"
#include "pc_p2_bigtreasure_map_trace.h"
#include "pc_p2_bigtreasure_visual.h"

// Private one-TU fixture build snapshots these lane implementations as
// dependencies (same pattern as the Groink volley fixture).
#include "../pc_port/pc_p2_bigtreasure.cpp"
#include "../pc_port/pc_p2_bigtreasure_attacks.cpp"
#include "../pc_port/pc_p2_bigtreasure_host.cpp"
#include "../pc_port/pc_p2_bigtreasure_map_trace.cpp"
#include "../pc_port/pc_p2_bigtreasure_motion.cpp"
#include "../pc_port/pc_p2_bigtreasure_visual.cpp"

namespace {
constexpr float kDt = 1.0f / 30.0f;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL BIGTREASURE_RUNTIME %s\n", message);
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
    for (unsigned char v : pixels) {
        nonblack |= v > 8;
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

struct WallProbe {
    bool valid = false;
    P2BigTreasureVec3 center{}, velocity{};
};

class BigTreasureApp final : public PlugPikiApp {
    int frames = 0;
    int phase = 0; // 0 probes pending, 1 wait1 playback, 2 dead playback, 3 done
    int visualFrames = 0;
    int wait1Events = 0;
    bool setup = false, wait1Captured = false, deadCaptured = false;
    float ground = 0.0f;
    P2BigTreasureMapTrace trace;
    P2BigTreasureHostSeam seam;
    WallProbe wall;

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
            trace.reset(mapMgr);
            require(p2_bigtreasure_host_setup("p2-bigtreasure-host.txt", seam), "host setup");
            std::puts("P2_BIGTREASURE_HOST_READY profile=p2-bigtreasure-host.txt placement=fixed "
                      "captures=5 no_ai=1 no_damage=1");
            setup = true;
        }
        switch (phase) {
        case 0:
            runProbes();
            runElecProbe();
            runWaterProbe();
            runHostSeam();
            startVisual();
            phase = 1;
            break;
        case 1:
            stepWait1();
            break;
        case 2:
            stepDead();
            break;
        default:
            break;
        }
        return result;
    }

    void draw(Graphics& gfx) override
    {
        PlugPikiApp::draw(gfx);
        if (phase == 0) {
            return;
        }
        Matrix4f owner;
        owner.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, 0.0f, 0.0f),
                      Vector3f(0.0f, ground, 0.0f));
        pc_p2_bigtreasure_visual_draw(gfx, owner);
        if (phase == 1 && visualFrames == 100 && !wait1Captured) {
            capture("bigtreasure-wait1.ppm");
            wait1Captured = true;
        }
        if (phase == 3 && !deadCaptured) {
            capture("bigtreasure-dead.ppm");
            deadCaptured = true;
            std::puts("PASS BIGTREASURE_RUNTIME");
            std::fflush(stdout);
            std::_Exit(0);
        }
    }

private:
    void runProbes()
    {
        require(mapMgr && mapMgr->mMapModel, "map unavailable");
        ground = mapMgr->getMinY(0, 0, false);
        require(std::isfinite(ground), "center ground unavailable");
        P2BigTreasureTraceResult result{};
        // Flat-floor probe: radius-20 sphere center must rest at ground+20.
        require(P2BigTreasureMapTrace::trace(&trace, { 0, ground + 15, 0 }, { 0, -300, 0 }, kDt,
                                             20.0f, 0.75f, result),
                "center trace");
        std::printf("P2_BIGTREASURE_FLOOR_PROBE ground=%.6f center=%.6f floor=%d\n", ground,
                    result.position.y, result.floor);
        require(result.floor && std::fabs(result.position.y - (ground + 20.0f)) < 0.25f,
                "center floor conversion");
        require(result.hasGroundY && std::fabs(result.groundY - ground) < 0.25f,
                "floor probe terrain sample");
        // Free-space probe: stationary sphere far above the floor sees nothing.
        require(P2BigTreasureMapTrace::trace(&trace, { 0, ground + 100, 0 }, { 0, 0, 0 }, kDt,
                                             20.0f, 0.75f, result),
                "free trace");
        require(!result.floor && !result.wall, "free center collision");
        // Vertical-wall probe from an actual steep map triangle.
        Shape* model = mapMgr->mMapModel;
        for (int i = 0; i < model->mTriCount && !wall.valid; ++i) {
            const CollTriInfo& tri = model->mTriList[i];
            const Vector3f& a    = model->mVertexList[tri.mVertexIndices[0]];
            const Vector3f& b    = model->mVertexList[tri.mVertexIndices[1]];
            const Vector3f& c    = model->mVertexList[tri.mVertexIndices[2]];
            Vector3f center((a.x + b.x + c.x) / 3.0f, (a.y + b.y + c.y) / 3.0f,
                            (a.z + b.z + c.z) / 3.0f);
            const Vector3f normal = tri.mTriangle.mNormal;
            const float mapGround = mapMgr->getMinY(center.x, center.z, false);
            if (std::fabs(normal.y) < 0.05f && center.y > mapGround + 15) {
                wall = { true,
                         { center.x + normal.x * 25, center.y + normal.y * 25,
                           center.z + normal.z * 25 },
                         { -normal.x * 300, -normal.y * 300, -normal.z * 300 } };
            }
        }
        require(wall.valid, "no wall probe candidate");
        require(P2BigTreasureMapTrace::trace(&trace, wall.center, wall.velocity, kDt, 20.0f,
                                             0.75f, result),
                "wall trace");
        require(result.wall, "wall probe did not hit");
        require(result.hasGroundY, "wall probe terrain sample");
        std::printf("P2_BIGTREASURE_WALL_PROBE wall=%d groundY=%.6f\n", result.wall,
                    result.groundY);
        // Ground callback validation.
        float sampled = 0.0f;
        require(P2BigTreasureMapTrace::ground(&trace, 0, 0, &sampled)
                    && std::fabs(sampled - ground) < 1e-4f,
                "ground callback");
        require(!P2BigTreasureMapTrace::ground(&trace, 0, 0, nullptr), "ground null sink");
        std::printf("P2_BIGTREASURE_MAP_PROBES_PASS calls=%llu floors=%llu walls=%llu\n",
                    (unsigned long long)trace.calls(), (unsigned long long)trace.floors(),
                    (unsigned long long)trace.walls());
        trace.reset(mapMgr);
    }

    void runElecProbe()
    {
        // Elec bounce acceptance through the real map: visible nodes scatter
        // from the raised joint, bounce (first-contact events) and settle
        // onto the floor with policy-side friction.
        const float ground = mapMgr->getMinY(0, 0, false);
        require(std::isfinite(ground), "elec ground unavailable");
        P2BigTreasureElecPolicy elec;
        const P2BigTreasureElecParams params = p2_bigtreasure_elec_params(6000.0f, 0.25f);
        const P2BigTreasureVec3 joint{ 0, ground + 100, 0 };
        const float zeroJit[P2BigTreasureElecPolicy::kCapacity] = {};
        require(elec.start(params, joint, 0.0f, zeroJit, zeroJit, zeroJit), "elec start");
        require(elec.activeCount() == 1 + params.maxDischarge, "elec discharge count");
        int totalBounces = 0;
        bool settledOnFloor = false;
        for (int tick = 0; tick < 300; ++tick) {
            int bounces = 0;
            elec.tick(kDt, joint, P2BigTreasureMapTrace::trace, &trace, &bounces);
            totalBounces += bounces;
            for (int i = 0; i < P2BigTreasureElecPolicy::kCapacity; ++i) {
                const P2BigTreasureElecNode& node = elec.node(i);
                if (!node.active || !node.visible) {
                    continue;
                }
                require(std::isfinite(node.position.x) && std::isfinite(node.position.y)
                            && std::isfinite(node.position.z),
                        "elec node position");
                // Node positions are stored with the +20 source raise undone.
                if (node.onFloor && std::fabs(node.position.y - ground) < 0.5f) {
                    settledOnFloor = true;
                }
            }
        }
        require(totalBounces >= 1, "elec no floor bounce");
        require(settledOnFloor, "elec node never settled on floor");
        std::printf("P2_BIGTREASURE_ELEC_PROBE_PASS bounces=%d traces=%llu floors=%llu\n",
                    totalBounces, (unsigned long long)trace.calls(),
                    (unsigned long long)trace.floors());
        elec.finish();
        trace.reset(mapMgr);
    }

    void runWaterProbe()
    {
        // Water arc acceptance: a bubble emitted from the raised joint
        // follows gravity (-20/update) and ends with a ground hit sampled
        // through the adapter's getMinY equivalent.
        const float ground = mapMgr->getMinY(0, 0, false);
        require(std::isfinite(ground), "water ground unavailable");
        P2BigTreasureWaterPolicy water;
        require(water.start(p2_bigtreasure_water_params(6000.0f)), "water start");
        const P2BigTreasureVec3 emit{ 0, ground + 100, 0 };
        const P2BigTreasureVec3 target{ 0, ground, 200 };
        require(water.emitShot(emit, target, 0.0f, 0.0f, kDt), "water emit");
        require(water.activeCount() == 1, "water active count");
        int groundHits = 0;
        int ticks       = 0;
        for (; ticks < 600 && groundHits == 0; ++ticks) {
            int hits = 0;
            water.tick(kDt, P2BigTreasureMapTrace::ground, &trace, &hits);
            groundHits += hits;
            for (int i = 0; i < P2BigTreasureWaterPolicy::kCapacity; ++i) {
                const P2BigTreasureWaterNode& node = water.node(i);
                if (node.active) {
                    require(std::isfinite(node.position.x) && std::isfinite(node.position.y)
                                && std::isfinite(node.position.z),
                            "water node position");
                }
            }
        }
        require(groundHits == 1, "water bubble never hit ground");
        require(water.activeCount() == 0, "water node survived impact");
        std::printf("P2_BIGTREASURE_WATER_PROBE_PASS ticks=%d hits=%d ground=%.6f\n", ticks,
                    groundHits, ground);
        water.defeat();
    }

    void runHostSeam()
    {
        // Multi-actor lifetime wiring at the seam: fixed-placement attack
        // entry (pacer threshold 4 + 2*4 = 12 s, strict) then deterministic
        // defeat teardown (pools first, then 5 captured pellets).
        require(seam.active && seam.ownership.weaponCount() == 4 && seam.ownership.louieAttached(),
                "seam loadout");
        int started = -1;
        for (int i = 0; i < 15 * 30 && started < 0; ++i) {
            started = p2_bigtreasure_host_tick_entry(seam, kDt, false, 0.0f);
        }
        require(started == P2BTWEAPON_Elec, "seam attack never started");
        require(seam.director.pools.isStarted(started), "seam pool not started");
        require(seam.director.pools.emit(started), "seam pool emit");
        P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1] = {};
        const std::size_t events = p2_bigtreasure_host_defeat(seam, drops, P2BTWEAPON_Count + 1);
        require(events == 5, "seam defeat event count");
        require(drops[4].isLouie
                    && drops[4].velocity.y == P2BigTreasureOwnership::kLouiePopY,
                "seam Louie release");
        for (int element = 0; element < P2BTWEAPON_Count; ++element) {
            require(seam.director.pools.inFlight(element) == 0, "seam pool drained");
        }
        std::printf("P2_BIGTREASURE_HOST_SEAM_PASS ticks=%llu attacks=%llu events=%llu\n",
                    (unsigned long long)seam.ticks, (unsigned long long)seam.attacksStarted,
                    (unsigned long long)seam.defeatEvents);
    }

    void startVisual()
    {
        require(pc_p2_bigtreasure_visual_setup("p2-bigtreasure-visual.txt"), "visual setup");
        require(pc_p2_bigtreasure_visual_pellet_count() == 4, "converted pellet count");
        require(pc_p2_bigtreasure_visual_debug_count() == 1, "loozy debug marker count");
        require(pc_p2_bigtreasure_visual_clip("wait1"), "wait1 clip");
        visualFrames = 0;
    }

    void stepWait1()
    {
        // wait1: 90-frame loop with authored (0,0)/(89,1) markers; advance
        // one source frame per idle frame for 200 frames (two full loops).
        require(pc_p2_bigtreasure_visual_update(1.0f) >= 0, "wait1 update");
        ++visualFrames;
        if (visualFrames < 200) {
            return;
        }
        int count = 0;
        const P2BigTreasureVisualEvent* events = pc_p2_bigtreasure_visual_events(&count);
        int loops = 0;
        for (int i = 0; i < count; ++i) {
            require(std::strcmp(events[i].clip, "wait1") == 0, "wait1 event clip");
            require((events[i].frame == 0 && events[i].type == 0)
                        || (events[i].frame == 89 && events[i].type == 1),
                    "wait1 authored event");
            loops += events[i].type == 1;
        }
        require(loops >= 2, "wait1 loop count");
        wait1Events = count;
        std::printf("P2_BIGTREASURE_VISUAL_WAIT1_PASS frames=%d events=%d loops=%d pose=%d\n",
                    visualFrames, count, loops, pc_p2_bigtreasure_visual_pose_index());
        require(pc_p2_bigtreasure_visual_clip("dead"), "dead clip");
        phase        = 2;
        visualFrames = 0;
    }

    void stepDead()
    {
        // dead: 332-frame one-shot; all 11 authored key events fire in
        // order, including the KEYEVENT_100 throwupItem anchor at frame 320,
        // then the implicit type-1000 completion.
        require(pc_p2_bigtreasure_visual_update(1.0f) >= 0, "dead update");
        ++visualFrames;
        if (!pc_p2_bigtreasure_visual_completed()) {
            require(visualFrames < 400, "dead never completed");
            return;
        }
        static const int kExpected[][2] = {
            { 60, 2 }, { 100, 3 }, { 125, 4 }, { 150, 5 }, { 175, 6 }, { 200, 7 },
            { 290, 8 }, { 295, 9 }, { 300, 10 }, { 305, 11 }, { 320, 100 },
        };
        int count = 0;
        const P2BigTreasureVisualEvent* events = pc_p2_bigtreasure_visual_events(&count);
        const int base = wait1Events;
        require(count - base == 12, "dead event count");
        for (int i = 0; i < 11; ++i) {
            const P2BigTreasureVisualEvent& event = events[base + i];
            require(std::strcmp(event.clip, "dead") == 0, "dead event clip");
            require(event.frame == kExpected[i][0] && event.type == kExpected[i][1],
                    "dead authored event order");
        }
        require(events[count - 1].type == 1000, "dead implicit completion");
        std::printf("P2_BIGTREASURE_VISUAL_DEAD_PASS frames=%d events=%d keyevent100=%d\n",
                    visualFrames, count - base, events[base + 10].frame);
        phase = 3;
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
    require(pc_window_init("BigTreasure host-seam runtime fixture", 960, 720), "window init");
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new BigTreasureApp());
    return 0;
}
