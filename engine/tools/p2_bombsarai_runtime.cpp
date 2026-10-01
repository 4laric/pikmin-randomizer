// Private real-GL BombSarai arena fixture. This file is compiled by the
// isolated fixture build only; it is not part of the game target.
// Requires user-supplied GPVE01 rev 0 assets; it never ships or shares them.
//
// The lane-owned 13-state FSM drives each carrier through the seam; this
// fixture only runs the map probes and feeds source ticks. Five pinned
// scenarios run end-to-end with no harness supply/throw events:
//   approach:   Wait -> Supply -> BombMove -> Release lob -> blast
//   purple:     scripted Purple stick forces Fall -> skyward eject -> blast
//   death:      scripted kill while carrying -> zero-velocity drop -> blast
//   multi:      two carriers, shared pool, per-carrier token attribution,
//               scripted horizontal x/z path (JOINT_FOLLOW travel_xz)
//   deadflight: carrier lobs, dies while the bomb is in flight -> the bomb
//               still resolves the (dead) carrier token, throws exactly once
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
#include "pc_p2_bombsarai_arena.h"
#include "pc_p2_bombsarai_clock.h"
#include "pc_p2_bombsarai_map_trace.h"
#include "pc_p2_bombsarai_terrain.h"
#include "pc_p2_hardlanes.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

namespace {
void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL BOMBSARAI_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

struct WallProbe { bool valid = false; P2BombSaraiVec3 center{}, velocity{}; };

bool carrierAlive(void*, std::uint64_t) { return true; }

const char* kindName(int kind)
{
    return kind == (int)P2BombSaraiThrowKind::Release ? "Release"
        : kind == (int)P2BombSaraiThrowKind::Fall ? "Fall" : "Death";
}

struct Scenario {
    const char* name;
    const char* profile;
    int carriers;
    int expectedBlasts;
    int throws[2];        // expected throw count per carrier (-1 = don't check)
    int throwKind[2];     // expected (last) throw kind per carrier (-1 = none)
    int minHits, maxHits; // total hits summed across all blast records
    bool expectAnyDead;   // at least one carrier must end dead
    bool expectHorizontal; // joint-follow must show horizontal travel (travel_xz > 0)
};

const Scenario kScenarios[] = {
    { "approach", "p2-bombsarai-arena.txt", 1, 1,
      { 1, -1 }, { (int)P2BombSaraiThrowKind::Release, -1 }, 3, 3, false, false },
    { "purple", "p2-bombsarai-arena-purple.txt", 1, 1,
      { 1, -1 }, { (int)P2BombSaraiThrowKind::Fall, -1 }, 0, 8, false, false },
    { "death", "p2-bombsarai-arena-death.txt", 1, 1,
      { 1, -1 }, { (int)P2BombSaraiThrowKind::Death, -1 }, 3, 3, true, false },
    // multi: with finding #2 (captured-only held) and pool=2 each carrier
    // re-supplies and re-throws after its first lob on the long fuse, so an
    // exact throw count is not stable; the gate is per-token blast attribution
    // (two distinct tokens, no cross-attribution).
    { "multi", "p2-bombsarai-arena-multi.txt", 2, 2,
      { -1, -1 }, { (int)P2BombSaraiThrowKind::Release, (int)P2BombSaraiThrowKind::Release },
      2, 8, false, true },
    { "deadflight", "p2-bombsarai-arena-deadflight.txt", 1, 1,
      { 1, -1 }, { (int)P2BombSaraiThrowKind::Release, -1 }, 3, 3, true, false },
};

class BombSaraiApp final : public PlugPikiApp {
    int frames = 0, sourceTicks = 0;
    bool setup = false, probes = false;
    int scenario = -1;
    int scenarioTicks = 0;
    int lastState[2] = { -1, -1 };
    bool wasCarrying[2] = { false, false };
    bool jointTracked[2] = { false, false };
    float jointMinY[2] = {}, jointMaxY[2] = {};
    float horizTravel[2] = {};
    float prevJX[2] = {}, prevJZ[2] = {};
    bool havePrev[2] = {};
    int throwSeen[2] = {};
    int throwKinds[2] = { -1, -1 };
    P2BombSaraiMapBinding binding;
    P2BombSaraiTerrainAdapter adapter;
    P2BombSaraiSourceClock clock;
    WallProbe wall;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 7200, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            clock.reset(); gameflow.mMoviePlayer->requestSkip(); return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) { clock.reset(); return result; }
        Navi* n = naviMgr->getNavi();
        if (!setup) {
            // The private room preview runs pc_p2_hardlanes_setup() and, on the
            // authored p2-bombsarai-arena.txt, steps the SAME global arena every
            // frame via gameCoreSection -> pc_p2_hardlanes_update. Release the
            // hardlane's arena ownership so this fixture advances the arena
            // exactly once per source tick (otherwise observe() samples every
            // other tick).
            pc_p2_hardlanes_reset();
            n->resetPosition(Vector3f(0, 0, -250)); n->mFaceDirection = 0; n->mSRT.r.set(0, 0, 0);
            binding.reset(mapMgr);
            adapter.reset(P2BombSaraiMapBinding::traceMove, &binding,
                          P2BombSaraiMapBinding::getMinY, &binding);
            setup = true;
        }
        if (!probes) { runProbes(); probes = true; std::puts("P2_BOMBSARAI_MAP_PROBES_PASS"); }
        if (scenario < 0) { startScenario(0); }
        const Scenario& s = kScenarios[scenario];
        const int ticks = clock.step(gsys->getFrameTime(), true);
        for (int i = 0; i < ticks; ++i) {
            ++sourceTicks; ++scenarioTicks;
            require(pc_p2_bombsarai_arena_update(P2BombSaraiBomb::kSourceDelta,
                                                 P2BombSaraiTerrainAdapter::trace, &adapter,
                                                 carrierAlive, nullptr), "arena update");
            observe();
            if (pc_p2_bombsarai_arena_blast_record_count() >= s.expectedBlasts) {
                finishScenario(); break;
            }
            require(scenarioTicks < 1200, "scenario timeout");
        }
        return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if (scenario >= 0) pc_p2_bombsarai_arena_draw(gfx);
    }
private:
    void startScenario(int index) {
        scenario = index;
        scenarioTicks = 0;
        for (int c = 0; c < 2; ++c) {
            lastState[c] = -1;
            wasCarrying[c] = false;
            jointTracked[c] = false;
            horizTravel[c] = 0.0f;
            havePrev[c] = false;
            throwSeen[c] = 0;
            throwKinds[c] = -1;
        }
        binding.reset(mapMgr); // fresh trace counters per scenario
        const Scenario& s = kScenarios[scenario];
        require(pc_p2_bombsarai_arena_setup(s.profile), "arena setup");
        std::printf("P2_BOMBSARAI_SCENARIO_BEGIN scenario=%s\n", s.name);
    }
    void observe() {
        const Scenario& s = kScenarios[scenario];
        for (int c = 0; c < s.carriers; ++c) {
            const int state = pc_p2_bombsarai_arena_state(c);
            if (state != lastState[c]) {
                std::printf("P2_BOMBSARAI_FSM_ENTER scenario=%s carrier=%d state=%s tick=%d\n",
                            s.name, c, pc_p2_bombsarai_arena_state_name(c), scenarioTicks);
                lastState[c] = state;
            }
            const bool carrying = pc_p2_bombsarai_arena_carrying(c);
            if (carrying && !wasCarrying[c]) {
                std::printf("P2_BOMBSARAI_FSM_SUPPLY scenario=%s carrier=%d tick=%d\n",
                            s.name, c, scenarioTicks);
                jointTracked[c] = false;
                horizTravel[c] = 0.0f;
                havePrev[c] = false;
            }
            // Animated capture joint: the captured payload must ride the moving
            // carrier (hover bob and, when scripted, horizontal x/z path).
            if (carrying) {
                P2BombSaraiVec3 joint;
                if (pc_p2_bombsarai_arena_captured_position(c, joint)) {
                    if (!jointTracked[c]) {
                        jointTracked[c] = true;
                        jointMinY[c] = jointMaxY[c] = joint.y;
                        havePrev[c] = false;
                    } else {
                        if (joint.y < jointMinY[c]) jointMinY[c] = joint.y;
                        if (joint.y > jointMaxY[c]) jointMaxY[c] = joint.y;
                        if (havePrev[c]) {
                            const float dx = joint.x - prevJX[c], dz = joint.z - prevJZ[c];
                            horizTravel[c] += std::sqrt(dx * dx + dz * dz);
                        }
                        prevJX[c] = joint.x; prevJZ[c] = joint.z; havePrev[c] = true;
                    }
                }
            }
            if (!carrying && wasCarrying[c]
                && pc_p2_bombsarai_arena_blast_record_count() < s.expectedBlasts) {
                if (jointTracked[c]) {
                    std::printf("P2_BOMBSARAI_JOINT_FOLLOW scenario=%s carrier=%d "
                                "travel_y=%.3f travel_xz=%.3f min=%.3f max=%.3f\n",
                                s.name, c, jointMaxY[c] - jointMinY[c], horizTravel[c],
                                jointMinY[c], jointMaxY[c]);
                    require(jointMaxY[c] - jointMinY[c] > 0.01f,
                            "captured joint did not follow the carrier");
                    if (s.expectHorizontal) {
                        require(horizTravel[c] > 0.5f, "captured joint did not follow horizontally");
                    }
                }
                throwSeen[c] += 1;
                throwKinds[c] = pc_p2_bombsarai_arena_last_throw_kind(c);
                std::printf("P2_BOMBSARAI_FSM_THROW scenario=%s carrier=%d kind=%s tick=%d\n",
                            s.name, c, kindName(throwKinds[c]),
                            pc_p2_bombsarai_arena_last_throw_tick(c));
            }
            wasCarrying[c] = carrying;
        }
    }
    void finishScenario() {
        const Scenario& s = kScenarios[scenario];
        const int records = pc_p2_bombsarai_arena_blast_record_count();
        const P2BombSaraiBlastRecord* recs = pc_p2_bombsarai_arena_blast_records();
        require(records == s.expectedBlasts, "blast record count mismatch");
        int totalHits = 0;
        int distinctTokens = 0;
        std::uint64_t seen[2] = { 0, 0 };
        for (int b = 0; b < records; ++b) {
            const P2BombSaraiBlastRecord& r = recs[b];
            totalHits += r.hitCount;
            if (distinctTokens < 2) {
                bool known = false;
                for (int d = 0; d < distinctTokens; ++d) {
                    if (seen[d] == r.carrierToken) { known = true; break; }
                }
                if (!known) seen[distinctTokens++] = r.carrierToken;
            }
            std::printf("P2_BOMBSARAI_BLAST scenario=%s carrier=%d token=%llu carrier_valid=%d "
                        "ticks=%d traces=%llu floors=%llu walls=%llu hits=%d carrier_dead=%d\n",
                        s.name, r.carrier, (unsigned long long)r.carrierToken,
                        r.carrierValid ? 1 : 0, r.tick,
                        (unsigned long long)binding.calls(),
                        (unsigned long long)binding.floors(),
                        (unsigned long long)binding.walls(), r.hitCount,
                        pc_p2_bombsarai_arena_carrier_dead(r.carrier) ? 1 : 0);
            for (int i = 0; i < r.hitCount; ++i) {
                std::printf("P2_BOMBSARAI_HIT scenario=%s id=%llu kind=%d damage=%.3f self=%d "
                            "token=%llu\n", s.name, (unsigned long long)r.hits[i].receiverId,
                            (int)r.hits[i].kind, r.hits[i].damage,
                            r.hits[i].attributeToSelf ? 1 : 0,
                            (unsigned long long)r.hits[i].attackerToken);
                if (r.hits[i].kind != P2BombSaraiReceiverKind::Teki) {
                    if (r.carrierValid) { // live carrier: navi/piki attributed to its token
                        require(r.hits[i].attackerToken == r.carrierToken
                                && !r.hits[i].attributeToSelf, "carrier attribution");
                    } else { // dead carrier: fall back to bomb-self (:167-172)
                        require(r.hits[i].attributeToSelf && r.hits[i].attackerToken == 0,
                                "dead-carrier attribution");
                    }
                }
            }
        }
        require(totalHits >= s.minHits && totalHits <= s.maxHits, "blast hit count out of range");
        if (s.carriers == 2) {
            // Multi-carrier: two distinct carrier tokens, no cross-attribution.
            require(distinctTokens == 2, "expected two distinct carrier tokens");
        }
        for (int c = 0; c < s.carriers; ++c) {
            if (s.throws[c] >= 0) require(throwSeen[c] == s.throws[c], "throw count mismatch");
            if (s.throwKind[c] >= 0) require(throwKinds[c] == s.throwKind[c], "throw kind mismatch");
        }
        if (s.expectAnyDead) {
            bool any = false;
            for (int c = 0; c < s.carriers; ++c) any |= pc_p2_bombsarai_arena_carrier_dead(c);
            require(any, "expected at least one dead carrier");
        }
        std::printf("P2_BOMBSARAI_SCENARIO_PASS scenario=%s\n", s.name);
        if (scenario + 1 < (int)(sizeof(kScenarios) / sizeof(kScenarios[0]))) {
            startScenario(scenario + 1);
        } else {
            std::puts("PASS BOMBSARAI_RUNTIME"); std::fflush(stdout); std::_Exit(0);
        }
    }
    void runProbes() {
        require(mapMgr && mapMgr->mMapModel, "map unavailable");
        float ground = 0.0f;
        require(P2BombSaraiTerrainAdapter::getMinY(&adapter, 0, 0, ground), "center ground unavailable");
        P2BombSaraiTraceResult result{};
        // Flat-floor probe: downward trace lands, center rests at ground+radius.
        const float radius = 5.0f;
        // Travel must exceed the start gap (10 = 15 - radius at 30Hz with 300
        // units/s lands exactly tangent, registering no collision): use 600.
        require(P2BombSaraiTerrainAdapter::trace(&adapter, { 0, ground + 15, 0 }, { 0, -600, 0 },
                                                 P2BombSaraiBomb::kSourceDelta, radius, result),
                "center trace");
        std::printf("P2_BOMBSARAI_FLOOR_PROBE ground=%.6f center=%.6f floor=%d\n",
                    ground, result.position.y, result.floor ? 1 : 0);
        require(result.floor && result.hasGroundY, "center floor classification");
        require(std::fabs(result.position.y - ground) <= radius + 0.25f,
                "center floor conversion");
        // Free trace: no contact, no groundY sample needed.
        require(P2BombSaraiTerrainAdapter::trace(&adapter, { 0, ground + 100, 0 }, { 0, 0, 0 },
                                                 P2BombSaraiBomb::kSourceDelta, radius, result),
                "free trace");
        require(!result.floor && !result.wall, "free center collision");
        // Wall probe: find a vertical triangle away from the floor and hit it.
        Shape* model = mapMgr->mMapModel;
        for (int i = 0; i < model->mTriCount && !wall.valid; ++i) {
            const CollTriInfo& tri = model->mTriList[i];
            const Vector3f& a = model->mVertexList[tri.mVertexIndices[0]];
            const Vector3f& b = model->mVertexList[tri.mVertexIndices[1]];
            const Vector3f& c = model->mVertexList[tri.mVertexIndices[2]];
            Vector3f center((a.x + b.x + c.x) / 3.0f, (a.y + b.y + c.y) / 3.0f,
                            (a.z + b.z + c.z) / 3.0f);
            const Vector3f normal = tri.mTriangle.mNormal;
            float mapGround = 0.0f;
            if (!P2BombSaraiTerrainAdapter::getMinY(&adapter, center.x, center.z, mapGround)) continue;
            if (std::fabs(normal.y) < 0.05f && center.y > mapGround + 15) {
                wall = { true, { center.x + normal.x * 15, center.y + normal.y * 15,
                                 center.z + normal.z * 15 },
                         // 600 units/s: same tangent-landing avoidance as above.
                         { -normal.x * 600, -normal.y * 600, -normal.z * 600 } };
            }
        }
        require(wall.valid, "no wall probe candidate");
        require(P2BombSaraiTerrainAdapter::trace(&adapter, wall.center, wall.velocity,
                                                 P2BombSaraiBomb::kSourceDelta, radius, result),
                "wall trace");
        require(result.wall, "wall probe did not hit");
        require(result.hasGroundY, "wall probe missing ground sample");
        std::puts("P2_BOMBSARAI_WALL_PROBE_PASS");
    }
};
}

int main(int argc, char** argv) {
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    // Equivalent replacement-main startup: a small centred 960x540 windowed
    // preview (PIKMIN_P2_ROOM_WINDOW=WxH overrides; off/0 keeps defaults),
    // matching pc_main.cpp's experimental-room startup without its main object.
    int windowWidth = 960, windowHeight = 540;
    const char* windowEnv = std::getenv("PIKMIN_P2_ROOM_WINDOW");
    if (windowEnv && std::strcmp(windowEnv, "off") && std::strcmp(windowEnv, "0")) {
        int w = 0, h = 0;
        if (std::sscanf(windowEnv, "%dx%d", &w, &h) == 2 && w >= 320 && h >= 240) {
            windowWidth = w; windowHeight = h;
        }
    }
    require(pc_window_init("BombSarai arena runtime fixture", windowWidth, windowHeight),
            "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(windowWidth, windowHeight);
    pc_window_center();
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new BombSaraiApp()); return 0;
}
