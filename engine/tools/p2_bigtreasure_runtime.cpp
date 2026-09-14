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
#include "pc_p2_bigtreasure_fsmhost.h"
#include "pc_p2_bigtreasure_map_trace.h"
#include "pc_p2_bigtreasure_visual.h"
#include "pc_p2_hardlanes.h"

// Batch 2: the lane implementations are part of the shared pikmin_pc target,
// so the fixture links against the build objects instead of compiling them into
// this translation unit (avoids duplicate symbols).

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

// Minimal host-side damage receiver for the encounter phase: a health pool
// that the fixture decrements when a real element policy registers a hit.
// Stands in for the Pikmin/Navi receiver adapter (lane 10) so the attack
// geometry has an observable target.
struct EncounterReceiverSink {
    float health = P2BigTreasureOwnership::kWeaponMaxHealth;
    int hits = 0;

    void apply(float damage)
    {
        health -= damage;
        ++hits;
    }
};

class BigTreasureApp final : public PlugPikiApp {
    int frames = 0;
    int phase = 0; // 0 probes pending, 1 wait1 playback, 2 dead playback, 3 dead
                   // capture, 4 extra-clip motion playback, 5 exit
    int visualFrames = 0;
    int wait1Events = 0;
    int motionIndex = 0;
    int motionClips = 0;
    int motionEvents = 0;
    int motionBase = 0;
    int motionFrames = 0;
    const char* motionName = nullptr;
    std::vector<p2retail::Event> motionExpected;
    bool motionClipLoop = false;
    int motionLoopFrames = 0;
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
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int windowWidth = 0, windowHeight = 0, windowX = 0, windowY = 0;
            SDL_GetWindowSize(window, &windowWidth, &windowHeight);
            SDL_GetWindowPosition(window, &windowX, &windowY);
            require(windowWidth == 960 && windowHeight == 540, "window size 960x540");
            std::printf("P2_BIGTREASURE_WINDOW size=%dx%d pos=%d,%d\n", windowWidth, windowHeight,
                        windowX, windowY);
            setup = true;
        }
        switch (phase) {
        case 0:
            runProbes();
            runElecProbe();
            runWaterProbe();
            runHostSeam();
            runFsmHost();
            runEncounter();
            startVisual();
            phase = 1;
            break;
        case 1:
            stepWait1();
            break;
        case 2:
            stepDead();
            break;
        case 4:
            stepMotion();
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
            startMotion();
            phase = 4;
        }
        if (phase == 5) {
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

    void runFsmHost()
    {
        // FSM host binding on the real map: drive the 12-state policy to an
        // attack, apply real weapon damage and observe the knock-off phase
        // transition (live weapon count drops and the policy re-enters
        // PreAttack in the same tick). Re-installs the seam after the defeat
        // probe above.
        require(p2_bigtreasure_host_setup("p2-bigtreasure-host.txt", seam), "fsmhost setup");
        P2BigTreasureFsmHost fsmHost;
        P2BigTreasureFsmParms parms;
        fsmHost.reset(parms);
        P2BigTreasureFsmHostInput in;
        P2BigTreasureFsmHostOutput out;

        in.hasTarget = true;
        int guard = 0;
        while (fsmHost.phase() != P2BT_Land && guard++ < 400) {
            fsmHost.tick(seam, in, out);
        }
        require(fsmHost.phase() == P2BT_Land, "fsmhost Stay->Land");
        in.animEnd = true;
        fsmHost.tick(seam, in, out);
        require(fsmHost.phase() == P2BT_ItemWalk, "fsmhost Land->ItemWalk");
        in = P2BigTreasureFsmHostInput{};
        in.hasTarget = true;
        in.attackLimitTime = true;
        fsmHost.tick(seam, in, out);
        in = P2BigTreasureFsmHostInput{};
        in.hasTarget = true;
        in.finishIKMotion = true;
        fsmHost.tick(seam, in, out);
        require(fsmHost.phase() == P2BT_PreAttack, "fsmhost ItemWalk->PreAttack");
        in = P2BigTreasureFsmHostInput{};
        in.animEnd = true;
        fsmHost.tick(seam, in, out);
        require(fsmHost.phase() == P2BT_Attack, "fsmhost PreAttack->Attack");
        in = P2BigTreasureFsmHostInput{};
        in.keyEvent2 = true;
        fsmHost.tick(seam, in, out);
        require(fsmHost.chosenWeapon() == P2BTWEAPON_Elec
                    && seam.director.pools.isStarted(fsmHost.chosenWeapon()),
                "fsmhost attack start");

        // Full four-weapon knock-off sequence: each weapon is damaged to zero
        // on the real map, the roller drops, and the policy re-picks (or drops
        // to DropItem when the last one goes). This is the weapon-count phase
        // progression the audit calls the real per-weapon escalation.
        int transitions = 0;
        for (int remaining = P2BTWEAPON_Count; remaining >= 1; --remaining) {
            const int weapon = fsmHost.chosenWeapon();
            require(weapon >= 0 && seam.ownership.isWeaponAttached(weapon),
                    "fsmhost chosen weapon attached");
            P2BigTreasureFsmHostInput damage;
            damage.damage = P2BigTreasureOwnership::kWeaponMaxHealth;
            damage.damageWeapon = weapon;
            fsmHost.tick(seam, damage, out);
            require(out.damageResult == P2BTDMG_Weapon, "fsmhost damage routing");
            require(out.knockedOff == 1 && seam.ownership.weaponCount() == remaining - 1,
                    "fsmhost knock-off sequence");
            require(!seam.ownership.isWeaponAttached(weapon), "fsmhost weapon released");
            if (remaining > 1) {
                require(fsmHost.phase() == P2BT_PreAttack, "fsmhost re-pick phase");
                P2BigTreasureFsmHostInput advance;
                advance.animEnd = true;
                fsmHost.tick(seam, advance, out);
                require(fsmHost.phase() == P2BT_Attack, "fsmhost attack after re-pick");
                P2BigTreasureFsmHostInput restart;
                restart.keyEvent2 = true;
                fsmHost.tick(seam, restart, out);
                require(fsmHost.chosenWeapon() != weapon
                            && seam.director.pools.isStarted(fsmHost.chosenWeapon()),
                        "fsmhost next attack started");
            }
            ++transitions;
        }
        require(transitions == P2BTWEAPON_Count, "fsmhost transition count");
        require(seam.ownership.isBodyExposed(), "fsmhost body exposed");
        require(fsmHost.phase() == P2BT_DropItem, "fsmhost DropItem with no weapons");

        // With every weapon gone the body is damageable and routes to boss HP.
        P2BigTreasureFsmHostInput body;
        body.damage = 250.0f;
        body.damageWeapon = -1;
        fsmHost.tick(seam, body, out);
        require(out.damageResult == P2BTDMG_Body && out.liveWeapons == 0, "fsmhost body damage");
        std::printf("P2_BIGTREASURE_FSMHOST_FULL_PASS knockoffs=%llu weapons=%d phase=%s "
                    "transitions=%d\n",
                    (unsigned long long)fsmHost.knockOffs(), seam.ownership.weaponCount(),
                    P2BigTreasureFsm::stateName(fsmHost.phase()), transitions);
    }

    // Starts the real element controller for `weapon` and steps it against the
    // real P1 map through P2BigTreasureMapTrace (the runElecProbe/runWaterProbe
    // pattern), returning true once its source hit geometry registers against
    // the host-side receiver sink. Fire and gas are self-contained source
    // policies (no map trace in their tick); their emit anchor is placed on the
    // real map floor. Elec/water consume the real trace/ground callbacks.
    bool encounterElementHit(int weapon, float ground)
    {
        if (weapon == P2BTWEAPON_Elec) {
            P2BigTreasureElecPolicy elec;
            const P2BigTreasureElecParams params =
                p2_bigtreasure_elec_params(P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f);
            const P2BigTreasureVec3 joint{ 0, ground + 100, 0 };
            const float zero[P2BigTreasureElecPolicy::kCapacity] = {};
            if (!elec.start(params, joint, 0.0f, zero, zero, zero)) {
                return false;
            }
            for (int tick = 0; tick < 300; ++tick) {
                int bounces = 0;
                elec.tick(kDt, joint, P2BigTreasureMapTrace::trace, &trace, &bounces);
                for (int a = 0; a < P2BigTreasureElecPolicy::kCapacity; ++a) {
                    const P2BigTreasureElecNode& node = elec.node(a);
                    if (!node.active || node.connected < 0) {
                        continue;
                    }
                    const P2BigTreasureElecNode& partner = elec.node(node.connected);
                    if (!partner.active) {
                        continue;
                    }
                    const P2BigTreasureVec3 target{ (node.position.x + partner.position.x) * 0.5f,
                                                    (node.position.y + partner.position.y) * 0.5f,
                                                    (node.position.z + partner.position.z) * 0.5f };
                    if (P2BigTreasureElecPolicy::chainHit(node.position, partner.position, target)) {
                        elec.finish();
                        return true;
                    }
                }
            }
            elec.finish();
            return false;
        }
        if (weapon == P2BTWEAPON_Fire) {
            P2BigTreasureFirePolicy fire;
            const P2BigTreasureFireParams params =
                p2_bigtreasure_fire_params(P2BigTreasureOwnership::kWeaponMaxHealth);
            if (!fire.start(params)) {
                return false;
            }
            const P2BigTreasureVec3 emit{ 0, ground + 60, 0 };
            const P2BigTreasureVec3 dir{ 0, 0, 1 };
            for (int tick = 0; tick < 3; ++tick) {
                fire.tick(kDt);
            }
            const float ratio = fire.nodeRatio(0);
            const float scale = ratio * (params.scale * P2BigTreasureFirePolicy::kExtent);
            const P2BigTreasureVec3 target{ emit.x + dir.x * scale, emit.y + dir.y * scale - 25.0f,
                                            emit.z + dir.z * scale };
            return fire.nodeHit(0, emit, dir, target);
        }
        if (weapon == P2BTWEAPON_Gas) {
            P2BigTreasureGasPolicy gas;
            const P2BigTreasureGasParams params =
                p2_bigtreasure_gas_params(P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f);
            if (!gas.start(params, 0.0f, true)) {
                return false;
            }
            const P2BigTreasureVec3 emit{ 0, ground + 60, 0 };
            for (int tick = 0; tick < 15; ++tick) {
                gas.tick(kDt, false);
            }
            const float ratio = gas.nodeRatio(0);
            const float angle = gas.armAngle(0);
            const P2BigTreasureVec3 target{
                emit.x + std::sin(angle) * (P2BigTreasureGasPolicy::kExtent * ratio),
                emit.y - 15.0f,
                emit.z + std::cos(angle) * (P2BigTreasureGasPolicy::kExtent * ratio)
            };
            return gas.nodeHit(emit, 0, ratio, target);
        }
        if (weapon == P2BTWEAPON_Water) {
            P2BigTreasureWaterPolicy water;
            if (!water.start(p2_bigtreasure_water_params(P2BigTreasureOwnership::kWeaponMaxHealth))) {
                return false;
            }
            const P2BigTreasureVec3 emit{ 0, ground + 100, 0 };
            const P2BigTreasureVec3 target{ 0, ground, 200 };
            if (!water.emitShot(emit, target, 0.0f, 0.0f, kDt)) {
                return false;
            }
            for (int tick = 0; tick < 5; ++tick) {
                int hits = 0;
                water.tick(kDt, P2BigTreasureMapTrace::ground, &trace, &hits);
                for (int i = 0; i < P2BigTreasureWaterPolicy::kCapacity; ++i) {
                    if (water.node(i).active
                        && water.nodeHit(i, water.node(i).position, false)) {
                        water.defeat();
                        return true;
                    }
                }
            }
            water.defeat();
            return false;
        }
        return false;
    }

    void runEncounter()
    {
        // Full encounter on the real map: for each of the four weapons drive
        // the FSM to Attack, start the real element controller (stepped against
        // the P1 map through P2BigTreasureMapTrace) and register a real hit on
        // the host-side receiver sink, then apply weapon damage to zero and
        // knock the weapon off. After the body is exposed, kill the boss
        // (killed -> Dead, KEYEVENT_100 finale release, KEYEVENT_END kill) and
        // run the deterministic teardown.
        require(p2_bigtreasure_host_setup("p2-bigtreasure-host.txt", seam), "encounter setup");
        trace.reset(mapMgr);
        const float ground = mapMgr->getMinY(0, 0, false);
        require(std::isfinite(ground), "encounter ground");

        P2BigTreasureFsmHost fsmHost;
        P2BigTreasureFsmParms parms;
        fsmHost.reset(parms);
        P2BigTreasureFsmHostInput in;
        P2BigTreasureFsmHostOutput out;
        EncounterReceiverSink sink;

        // Stay -> Land (target detection), Land -> ItemWalk, ItemWalk ->
        // PreAttack (attack limit / IK finish), mirroring the FSM-host phase.
        in.hasTarget = true;
        int guard = 0;
        while (fsmHost.phase() != P2BT_Land && guard++ < 400) {
            fsmHost.tick(seam, in, out);
        }
        require(fsmHost.phase() == P2BT_Land, "encounter Stay->Land");
        in = P2BigTreasureFsmHostInput{};
        in.hasTarget = true;
        in.animEnd = true;
        fsmHost.tick(seam, in, out);
        require(fsmHost.phase() == P2BT_ItemWalk, "encounter Land->ItemWalk");
        in = P2BigTreasureFsmHostInput{};
        in.hasTarget = true;
        in.attackLimitTime = true;
        fsmHost.tick(seam, in, out);
        in = P2BigTreasureFsmHostInput{};
        in.hasTarget = true;
        in.finishIKMotion = true;
        fsmHost.tick(seam, in, out);
        require(fsmHost.phase() == P2BT_PreAttack, "encounter ItemWalk->PreAttack");

        static const int kExpectedOrder[P2BTWEAPON_Count] = {
            P2BTWEAPON_Elec, P2BTWEAPON_Fire, P2BTWEAPON_Gas, P2BTWEAPON_Water
        };
        std::size_t events = 0;
        int hits = 0;
        for (int remaining = P2BTWEAPON_Count; remaining >= 1; --remaining) {
            // PreAttack -> Attack (the pick already ran on PreAttack entry).
            in = P2BigTreasureFsmHostInput{};
            in.animEnd = true;
            fsmHost.tick(seam, in, out);
            require(fsmHost.phase() == P2BT_Attack, "encounter PreAttack->Attack");
            const int weapon = fsmHost.chosenWeapon();
            require(weapon == kExpectedOrder[P2BTWEAPON_Count - remaining],
                    "encounter weapon order");
            require(seam.ownership.isWeaponAttached(weapon), "encounter weapon attached");

            // Attack KEYEVENT_2: startAttack -> pools.start(chosenWeapon).
            in = P2BigTreasureFsmHostInput{};
            in.keyEvent2 = true;
            fsmHost.tick(seam, in, out);
            require(out.fsm.startAttack && seam.director.pools.isStarted(weapon),
                    "encounter attack started");

            // Real element controller against the real P1 map; one registered
            // hit on the receiver sink.
            require(encounterElementHit(weapon, ground), "encounter element hit");
            sink.apply(P2BigTreasureOwnership::kWeaponMaxHealth);
            ++hits;
            require(sink.hits == hits, "encounter receiver sink");

            // Apply weapon damage to zero and knock the weapon off; the FSM
            // observes the reduced loadout and re-picks (or drops to DropItem).
            P2BigTreasureFsmHostInput damage;
            damage.damage = P2BigTreasureOwnership::kWeaponMaxHealth;
            damage.damageWeapon = weapon;
            fsmHost.tick(seam, damage, out);
            require(out.damageResult == P2BTDMG_Weapon, "encounter damage routing");
            require(out.knockedOff == 1, "encounter knock-off");
            events += static_cast<std::size_t>(out.knockedOff);
            require(!seam.ownership.isWeaponAttached(weapon), "encounter weapon released");
            if (remaining > 1) {
                require(fsmHost.phase() == P2BT_PreAttack, "encounter re-pick phase");
            }
        }
        require(hits == P2BTWEAPON_Count, "encounter hit count");
        require(fsmHost.knockOffs() == P2BTWEAPON_Count, "encounter knock-off count");
        require(seam.ownership.isBodyExposed(), "encounter body exposed");
        require(fsmHost.phase() == P2BT_DropItem, "encounter DropItem with no weapons");

        // Body damage is accepted once every weapon is gone.
        P2BigTreasureFsmHostInput body;
        body.damage = 250.0f;
        body.damageWeapon = -1;
        fsmHost.tick(seam, body, out);
        require(out.damageResult == P2BTDMG_Body, "encounter body damage");

        // Boss death: onKill -> Dead, KEYEVENT_100 throwupItem + releaseLoozy,
        // KEYEVENT_END kill, then the deterministic host teardown.
        P2BigTreasureFsmHostInput kill;
        kill.killed = true;
        fsmHost.tick(seam, kill, out);
        require(fsmHost.phase() == P2BT_Dead, "encounter killed->Dead");
        kill = P2BigTreasureFsmHostInput{};
        kill.keyEvent100 = true;
        fsmHost.tick(seam, kill, out);
        require(out.fsm.throwupItem && out.fsm.releaseLoozy, "encounter finale release");
        events += 1; // Louie's source (0,150,0) release at KEYEVENT_100
        kill = P2BigTreasureFsmHostInput{};
        kill.animEnd = true;
        fsmHost.tick(seam, kill, out);
        require(out.fsm.killRequested, "encounter animEnd kill");
        P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1] = {};
        events += p2_bigtreasure_host_defeat(seam, drops, P2BTWEAPON_Count + 1);
        require(fsmHost.phase() == P2BT_Dead, "encounter final phase");
        require(events >= P2BTWEAPON_Count, "encounter teardown events");
        std::printf("P2_BIGTREASURE_ENCOUNTER_PASS knockoffs=%llu hits=%d phase=%s events=%llu\n",
                    (unsigned long long)fsmHost.knockOffs(), hits,
                    P2BigTreasureFsm::stateName(fsmHost.phase()),
                    (unsigned long long)events);
    }

    void startVisual()
    {
        // Own the clip player for the deterministic per-clip phases below; the
        // production hardlanes clock would otherwise advance the same player.
        pc_p2_hardlanes_set_bigtreasure_visual_driven(false);
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

    // Additive (#246 motion staging): after wait1/dead, replay every other
    // clip staged in the generated profile through the vendored retail event
    // player and assert each one dispatches its authored key events. The clip
    // list comes from the stage subset, so widening the stage widens playback
    // without touching this fixture; the dispatch log is the same bounded event
    // bank wait1/dead already use. One-shot clips run to the implicit type-1000
    // completion; loops run exactly to their first authored (type-1) loop
    // marker, which is the fixed window retail wraps on.
    void startMotion()
    {
        motionIndex = 0;
        motionClips = 0;
        motionEvents = 0;
        motionFrames = 0;
        int count = 0;
        pc_p2_bigtreasure_visual_events(&count);
        motionBase = count;
        if (!beginMotionClip()) {
            finishMotion();
        }
    }

    bool beginMotionClip()
    {
        while (motionIndex < pc_p2_bigtreasure_visual_clip_count()) {
            const char* name = pc_p2_bigtreasure_visual_clip_name(motionIndex++);
            if (!name || std::strcmp(name, "wait1") == 0 || std::strcmp(name, "dead") == 0) {
                continue;
            }
            if (!pc_p2_bigtreasure_visual_clip(name)) {
                continue;
            }
            const p2retail::Motion* motion = pc_p2_bigtreasure_visual_clip_motion(name);
            require(motion != nullptr, "motion clip table entry");
            motionName = name;
            motionExpected.clear();
            motionClipLoop = false;
            motionLoopFrames = 0;
            for (const p2retail::Event& event : motion->events) {
                motionExpected.push_back(event);
                if (event.type == 1) {
                    motionClipLoop = true;
                    motionLoopFrames = event.frame + 1;
                    break;
                }
            }
            if (!motionClipLoop) {
                motionExpected.push_back(p2retail::Event{ motion->duration, 1000 });
            }
            motionFrames = 0;
            return true;
        }
        return false;
    }

    void stepMotion()
    {
        require(pc_p2_bigtreasure_visual_update(1.0f) >= 0, "motion update");
        ++motionFrames;
        int count = 0;
        const P2BigTreasureVisualEvent* log = pc_p2_bigtreasure_visual_events(&count);
        // A loop's authored (type-1) marker is the fixed window: the retail
        // player dispatches it once per wrap, so stop at the first one seen.
        bool loopSeen = false;
        if (motionClipLoop) {
            for (int i = motionBase; i < count; ++i) {
                if (log[i].type == 1) {
                    loopSeen = true;
                    break;
                }
            }
        }
        const bool done = motionClipLoop ? loopSeen : pc_p2_bigtreasure_visual_completed();
        // Bounded safety net: one-shot clips complete inside their own length
        // and loops stop at the first loop marker, both far under 240 frames.
        if (!done && motionFrames < 240) {
            return;
        }
        count = 0;
        log = pc_p2_bigtreasure_visual_events(&count);
        require(std::strcmp(pc_p2_bigtreasure_visual_active_clip(), motionName) == 0,
                "motion active clip");
        if (!motionClipLoop) {
            require(pc_p2_bigtreasure_visual_completed(), "one-shot clip completes");
        }
        const int dispatched = count - motionBase;
        if (dispatched != static_cast<int>(motionExpected.size())) {
            std::printf("P2_BIGTREASURE_MOTION_EVENT_MISMATCH clip=%s dispatched=%d expected=%d "
                        "frames=%d loop=%d window=%d\n",
                        motionName, dispatched, static_cast<int>(motionExpected.size()),
                        motionFrames, motionClipLoop ? 1 : 0, motionLoopFrames);
            for (int i = 0; i < dispatched; ++i) {
                const p2retail::Event want = i < static_cast<int>(motionExpected.size())
                                                 ? motionExpected[i]
                                                 : p2retail::Event{ -1, -1 };
                std::printf("P2_BIGTREASURE_MOTION_EVENT_DETAIL i=%d got=%d/%d want=%d/%d\n", i,
                            log[motionBase + i].frame, log[motionBase + i].type, want.frame,
                            want.type);
            }
            std::fflush(stdout);
        }
        require(dispatched == static_cast<int>(motionExpected.size()),
                "motion authored event count");
        for (int i = 0; i < dispatched; ++i) {
            require(std::strcmp(log[motionBase + i].clip, motionName) == 0,
                    "motion authored event clip");
            require(log[motionBase + i].frame == motionExpected[i].frame
                        && log[motionBase + i].type == motionExpected[i].type,
                    "motion authored event order");
        }
        motionEvents += dispatched;
        ++motionClips;
        motionBase = count;
        if (!beginMotionClip()) {
            finishMotion();
        }
    }

    void finishMotion()
    {
        require(motionClips >= 16, "full motion clip advances");
        require(motionClips == pc_p2_bigtreasure_visual_clip_count() - 2,
                "every staged clip advanced");
        std::printf("P2_BIGTREASURE_MOTION_PASS clips=%d events=%d\n", motionClips,
                    motionEvents);
        std::printf("P2_BIGTREASURE_MOTION_FULL_PASS clips=%d events=%d advanced=%d\n",
                    motionClips, motionEvents, motionClips);
        phase = 5;
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
    require(pc_window_init("BigTreasure host-seam runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new BigTreasureApp());
    return 0;
}
