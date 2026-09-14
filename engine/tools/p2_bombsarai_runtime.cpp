// Private real-GL BombSarai arena fixture. This file is compiled by the
// isolated fixture build only; it is not part of the game target.
// Requires user-supplied GPVE01 rev 0 assets; it never ships or shares them.
//
// The lane-owned 13-state FSM drives the carrier through the seam; this
// fixture only runs the map probes and feeds source ticks. Three pinned
// scenarios run end-to-end with no harness supply/throw events:
//   approach: Wait -> Supply -> BombMove -> Release lob -> blast
//   purple:   scripted Purple stick forces Fall -> skyward eject -> blast
//   death:    scripted kill while carrying -> zero-velocity drop -> blast
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
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL BOMBSARAI_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

struct WallProbe { bool valid = false; P2BombSaraiVec3 center{}, velocity{}; };

bool carrierAlive(void*, std::uint64_t) { return true; }

struct Scenario {
    const char* name;
    const char* profile;
    int expectedThrowKind; // P2BombSaraiThrowKind as int
    int minHits, maxHits;
    bool expectCarrierDead;
};

const Scenario kScenarios[] = {
    { "approach", "p2-bombsarai-arena.txt", (int)P2BombSaraiThrowKind::Release, 3, 3, false },
    { "purple", "p2-bombsarai-arena-purple.txt", (int)P2BombSaraiThrowKind::Fall, 0, 8, false },
    { "death", "p2-bombsarai-arena-death.txt", (int)P2BombSaraiThrowKind::Death, 3, 3, true },
};

class BombSaraiApp final : public PlugPikiApp {
    int frames = 0, sourceTicks = 0;
    bool setup = false, probes = false;
    int scenario = -1;
    int scenarioTicks = 0;
    int lastState = -1;
    bool wasCarrying = false;
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
            n->resetPosition(Vector3f(0, 0, -250)); n->mFaceDirection = 0; n->mSRT.r.set(0, 0, 0);
            binding.reset(mapMgr);
            adapter.reset(P2BombSaraiMapBinding::traceMove, &binding,
                          P2BombSaraiMapBinding::getMinY, &binding);
            setup = true;
        }
        if (!probes) { runProbes(); probes = true; std::puts("P2_BOMBSARAI_MAP_PROBES_PASS"); }
        if (scenario < 0) { startScenario(0); }
        const int ticks = clock.step(gsys->getFrameTime(), true);
        for (int i = 0; i < ticks; ++i) {
            ++sourceTicks; ++scenarioTicks;
            require(pc_p2_bombsarai_arena_update(P2BombSaraiBomb::kSourceDelta,
                                                 P2BombSaraiTerrainAdapter::trace, &adapter,
                                                 carrierAlive, nullptr), "arena update");
            observe();
            if (pc_p2_bombsarai_arena_blast_fired()) { finishScenario(); break; }
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
        lastState = -1;
        wasCarrying = false;
        binding.reset(mapMgr); // fresh trace counters per scenario
        const Scenario& s = kScenarios[scenario];
        require(pc_p2_bombsarai_arena_setup(s.profile), "arena setup");
        std::printf("P2_BOMBSARAI_SCENARIO_BEGIN scenario=%s\n", s.name);
    }
    void observe() {
        const Scenario& s = kScenarios[scenario];
        const int state = pc_p2_bombsarai_arena_state();
        if (state != lastState) {
            std::printf("P2_BOMBSARAI_FSM_ENTER scenario=%s state=%s tick=%d\n",
                        s.name, pc_p2_bombsarai_arena_state_name(), scenarioTicks);
            lastState = state;
        }
        const bool carrying = pc_p2_bombsarai_arena_carrying();
        if (carrying && !wasCarrying) {
            std::printf("P2_BOMBSARAI_FSM_SUPPLY scenario=%s tick=%d\n", s.name, scenarioTicks);
        }
        if (!carrying && wasCarrying && !pc_p2_bombsarai_arena_blast_fired()) {
            const int kind = pc_p2_bombsarai_arena_last_throw_kind();
            const char* kindName = kind == (int)P2BombSaraiThrowKind::Release ? "Release"
                : kind == (int)P2BombSaraiThrowKind::Fall ? "Fall" : "Death";
            std::printf("P2_BOMBSARAI_FSM_THROW scenario=%s kind=%s tick=%d\n",
                        s.name, kindName, pc_p2_bombsarai_arena_last_throw_tick());
            require(kind == s.expectedThrowKind, "unexpected throw kind");
        }
        wasCarrying = carrying;
    }
    void finishScenario() {
        const Scenario& s = kScenarios[scenario];
        const P2BombSaraiRoutedHit* hits = pc_p2_bombsarai_arena_blast_hits();
        const int count = pc_p2_bombsarai_arena_blast_count();
        std::printf("P2_BOMBSARAI_BLAST scenario=%s ticks=%d traces=%llu floors=%llu "
                    "walls=%llu hits=%d carrier_dead=%d\n", s.name, scenarioTicks,
                    (unsigned long long)binding.calls(), (unsigned long long)binding.floors(),
                    (unsigned long long)binding.walls(), count,
                    pc_p2_bombsarai_arena_carrier_dead() ? 1 : 0);
        for (int i = 0; i < count; ++i) {
            std::printf("P2_BOMBSARAI_HIT scenario=%s id=%llu kind=%d damage=%.3f self=%d "
                        "token=%llu\n", s.name, (unsigned long long)hits[i].receiverId,
                        (int)hits[i].kind, hits[i].damage, hits[i].attributeToSelf ? 1 : 0,
                        (unsigned long long)hits[i].attackerToken);
        }
        require(count >= s.minHits && count <= s.maxHits, "blast hit count out of range");
        require(pc_p2_bombsarai_arena_carrier_dead() == s.expectCarrierDead,
                "carrier liveness mismatch");
        if (s.expectCarrierDead) {
            // The dead carrier's token must fail validation: Navi/Pikmin hits
            // fall back to bomb-self attribution (bombState.cpp:167-172).
            for (int i = 0; i < count; ++i) {
                if (hits[i].kind != P2BombSaraiReceiverKind::Teki) {
                    require(hits[i].attributeToSelf && hits[i].attackerToken == 0,
                            "dead-carrier attribution");
                }
            }
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
    require(pc_window_init("BombSarai arena runtime fixture", 960, 720), "window init");
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new BombSaraiApp()); return 0;
}
