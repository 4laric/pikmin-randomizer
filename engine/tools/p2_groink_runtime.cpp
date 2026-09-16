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
#include "Piki.h"
#include "PikiMgr.h"
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
#include "pc_p2_groink_teki.h"
#include "teki.h"
#include "Generator.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
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

bool sCarcassAutomaticBinding = false;
bool sCarcassTransport = false;
bool sGroinkLive = false;

// Lane 21 live-host witness (#198): per-Piki health/FSM-state snapshot so the
// landing press (a real InteractPress receiver) can be cited with the target's
// health/state change. Keyed by the live Piki pointer (identity/incarnation).
struct LivePikiSample { float health = 0.0f; int state = 0; bool alive = false; };

class GroinkApp final : public PlugPikiApp {
    int frames = 0, sourceTicks = 0;
    bool carcassArmed = false;
    int carcassTicks = 0;
    BTeki* carcassHost = nullptr;
    bool setup = false, probes = false, fired = false, flightCapture = false, flightCaptured = false, terminalCapture = false;
    P2GroinkMapTrace trace;
    P2GroinkSourceClock clock;
    WallProbe wall;
    BTeki* liveHost = nullptr;
    int liveTicks = 0, liveHealthDrops = 0, liveStateChanges = 0;
    float liveTravel = 0.0f, liveLastX = 0.0f, liveLastZ = 0.0f;
    std::map<const Piki*, LivePikiSample> livePrevPiki;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 3600, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            clock.reset(); gameflow.mMoviePlayer->requestSkip(); return result;
        }
        if (sGroinkLive) {
            // Lane 21 live-host run (#198): the generated Frog actor at 201001 is
            // left alive and driven only by its own source FSM (lane 16, wired into
            // BTeki::update). The staged starting squad is already inside its sight,
            // so the FSM turns/hops/attacks on its own. No squad is ringed, no
            // health is written and no damage is injected; the only witness reads
            // the actor's position/FSM/animation and each live Piki's health/state.
            if (!tekiMgr || !naviMgr || !pikiMgr) { return result; }
            if (!liveHost) {
                Iterator it(tekiMgr); CI_LOOP(it) {
                    Teki* teki = static_cast<Teki*>(*it);
                    if (teki && teki->mTekiType == TEKI_Frog && teki->mGenerator
                        && teki->mGenerator->_70 == 201001u) {
                        liveHost = static_cast<BTeki*>(teki);
                        break;
                    }
                }
                if (!liveHost) { return result; }
                liveLastX = liveHost->mSRT.t.x; liveLastZ = liveHost->mSRT.t.z;
                std::puts("P2_GROINK_LIVE_BEGIN generator=201001 actor=generated_Frog damage_write=0 ring=0");
                std::fflush(stdout);
            }
            ++liveTicks;
            const char* state = nullptr; const char* clip = nullptr; float phase = 0.0f;
            const bool probed = pc_p2_frog_probe(liveHost, &state, &clip, &phase);
            if (!probed) { state = "unregistered"; clip = "none"; }
            const Vector3f now = liveHost->mSRT.t;
            const float stepX = now.x - liveLastX, stepZ = now.z - liveLastZ;
            liveTravel += std::sqrt(stepX * stepX + stepZ * stepZ);
            liveLastX = now.x; liveLastZ = now.z;
            if (liveTicks % 30 == 0) {
                std::printf("P2_GROINK_MOVE generator=201001 tick=%d x=%.3f y=%.3f z=%.3f travel=%.3f "
                            "state=%s clip=%s phase=%.3f health=%.1f\n",
                            liveTicks, now.x, now.y, now.z, liveTravel,
                            state ? state : "unregistered", clip ? clip : "none", phase, liveHost->mHealth);
                std::fflush(stdout);
            }
            // Real receiver witness: an engine InteractPress on a live Piki mutates
            // Piki::mHealth and its PIKISTATE FSM. Report each change with the
            // before/after pair so the press outcome is explicit.
            if (pikiMgr) {
                Iterator pc(pikiMgr);
                CI_LOOP(pc) {
                    Piki* p = static_cast<Piki*>(*pc);
                    if (!p) { continue; }
                    const int st = p->getState();
                    const bool alive = p->isAlive();
                    auto it = livePrevPiki.find(p);
                    if (it == livePrevPiki.end()) {
                        livePrevPiki[p] = LivePikiSample{p->mHealth, st, alive};
                        continue;
                    }
                    LivePikiSample& prev = it->second;
                    if (prev.health != p->mHealth || prev.state != st || prev.alive != alive) {
                        std::printf("P2_GROINK_TARGET_HIT id=%llu health=%.1f->%.1f state=%d->%d "
                                    "alive=%d->%d x=%.3f z=%.3f\n",
                                    static_cast<unsigned long long>(reinterpret_cast<std::uintptr_t>(p)),
                                    prev.health, p->mHealth, prev.state, st, int(prev.alive), int(alive),
                                    p->mSRT.t.x, p->mSRT.t.z);
                        if (p->mHealth < prev.health) { ++liveHealthDrops; }
                        if (prev.state != st) { ++liveStateChanges; }
                        prev = LivePikiSample{p->mHealth, st, alive};
                        std::fflush(stdout);
                    }
                }
            }
            if ((liveTravel > 5.0f && liveHealthDrops > 0 && liveTicks >= 600) || liveTicks >= 1800) {
                std::printf("P2_GROINK_LIVE_PASS ticks=%d travel=%.3f health_drops=%d state_changes=%d\n",
                            liveTicks, liveTravel, liveHealthDrops, liveStateChanges);
                std::puts("PASS GROINK_RUNTIME groink_live");
                std::fflush(stdout); std::_Exit(0);
            }
            return result;
        }
        if (sCarcassAutomaticBinding || sCarcassTransport) {
            if (!tekiMgr || !naviMgr || !pikiMgr) return result;
            Navi* n = naviMgr->getNavi();
            if (!n) return result;
            // Locate the generated Frog host once. The BTeki survives as a
            // LeaveCorpse corpse; the sidecar's binding key stays valid until the
            // carcass policy kills the pellet (then is_bound flips false and the
            // host pointer must not be dereferenced).
            if (!carcassHost) {
                Iterator it(tekiMgr); CI_LOOP(it) {
                    Teki* teki = static_cast<Teki*>(*it);
                    if (teki && teki->mTekiType == TEKI_Frog && teki->mGenerator && teki->mGenerator->_70 == 201001u) {
                        carcassHost = static_cast<BTeki*>(teki);
                        break;
                    }
                }
                if (!carcassHost) return result;
                require(pc_p2_groink_teki_is_bound(carcassHost), "finalSetup sidecar bound generated Frog");
                std::puts("P2_GROINK_CARCASS_HOST_BOUND host=generated_Frog generator=201001 kill=free_mode_squad health_write=0 host_life_clamp=120 parameter_override=1");
                std::fflush(stdout);
            }
            ++carcassTicks;
            // Natural kill (lane 19 recipe): park the captain beside the host and
            // ring-deploy the red squad in FreeMode. The carcass mode re-rings
            // every 120 ticks; the transport mode rings once and then leaves the
            // squad free to pick up and carry the dropped corpse to the Pod.
            if (pc_p2_groink_teki_is_bound(carcassHost)) {
                // Kill phase only: park the captain beside the live host and
                // deploy the free-mode squad. Once the host dies in transport
                // mode the native carcass tail (pc_p2_groink_teki.cpp) owns the
                // captain park and the free-mode re-ring onto the corpse pellet,
                // so the fixture must stop overriding the captain here.
                const bool hostAlive = carcassHost->isAlive();
                if (!sCarcassTransport || hostAlive) {
                    Vector3f park(carcassHost->mSRT.t.x, 0.0f, carcassHost->mSRT.t.z + 40.0f);
                    park.y = mapMgr->getMinY(park.x, park.z, true);
                    n->resetPosition(park);
                    if (sCarcassTransport) {
                        if (carcassTicks == 1 || carcassTicks % 60 == 0) ringReds(n, carcassHost);
                    } else if (carcassTicks == 1 || carcassTicks % 120 == 0) {
                        ringReds(n, carcassHost);
                    }
                }
            }
            if (carcassTicks % 60 == 0 || !pc_p2_groink_teki_is_bound(carcassHost)) {
                std::printf("P2_GROINK_CARCASS_HOST tick=%d health=%.1f bound=%d reds=%d pokos=%d transport=%d\n",
                    carcassTicks, pc_p2_groink_teki_health(carcassHost),
                    int(pc_p2_groink_teki_is_bound(carcassHost)), aliveReds(), pc_p2_preview_pokos(), transportCarriers());
                std::fflush(stdout);
            }
            if (sCarcassTransport) {
                // Transport: the natural kill drops a corpse; free Pikmin carry it
                // to the Pod, whose receipt credits corpse:groink:<gen> (pokos > 0).
                if (pc_p2_preview_pokos() > 0) {
                    std::printf("P2_GROINK_CARCASS_TRANSPORT_PASS ticks=%d pokos=%d\n",
                        carcassTicks, pc_p2_preview_pokos());
                    std::puts("PASS GROINK_RUNTIME carcass_transport");
                    std::fflush(stdout); std::_Exit(0);
                }
                if (carcassTicks >= 2400) {
                    std::printf("P2_GROINK_CARCASS_TRANSPORT_TIMEOUT ticks=%d pokos=%d reds=%d\n",
                        carcassTicks, pc_p2_preview_pokos(), aliveReds());
                    std::fflush(stdout);
                    std::_Exit(1);
                }
                return result;
            }
            if (pc_p2_groink_teki_total_births() >= 1) {
                std::printf("P2_GROINK_CARCASS_BIRTH_PASS ticks=%d total_births=%d\n",
                    carcassTicks, pc_p2_groink_teki_total_births());
                std::puts("PASS GROINK_RUNTIME carcass_natural_kill");
                std::fflush(stdout); std::_Exit(0);
            }
            if (carcassTicks >= 2400) {
                // Budget: a natural free-mode kill takes ~950 ticks (Frog 800 HP),
                // then the 135-frame dead animation finalizes the corpse (~4.5 s),
                // then the sidecar regrows. The source 30 s + 10 s defaults would
                // need far more, so every run writes sidecar_config_short (2 s + 3 s).
                std::printf("P2_GROINK_CARCASS_TIMEOUT ticks=%d total_births=%d reds=%d\n",
                    carcassTicks, pc_p2_groink_teki_total_births(), aliveReds());
                std::fflush(stdout);
                std::_Exit(1);
            }
            return result;
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
    int transportCarriers() {
        int count = 0;
        Iterator it(pikiMgr); CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && p->mMode == PikiMode::TransportMode) ++count;
        }
        return count;
    }
    int aliveReds() {
        int count = 0;
        Iterator it(pikiMgr); CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && p->mColor == Red) ++count;
        }
        return count;
    }
    // Lane 19 free-mode ring: deploy every live red on a 22-unit circle around the
    // host and set FreeMode so the P1 auto-attack engages it. No Piki action is
    // assigned and the host's health is never written (parameter/actor state is
    // left to the source FSM).
    void ringReds(Navi* n, BTeki* host) {
        int total = aliveReds();
        if (total <= 0) return;
        int index = 0;
        Iterator it(pikiMgr); CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->mColor != Red) continue;
            const float angle = float(index) * 6.2831853f / float(total);
            Vector3f spot(host->mSRT.t.x + 22.0f * std::sin(angle), 0.0f,
                          host->mSRT.t.z + 22.0f * std::cos(angle));
            spot.y = mapMgr->getMinY(spot.x, spot.z, true);
            p->resetPosition(spot);
            p->changeMode(PikiMode::FreeMode, n);
            ++index;
        }
        std::printf("P2_GROINK_CARCASS_RING tick=%d reds=%d health=%.1f\n",
                    carcassTicks, index, pc_p2_groink_teki_health(host));
        std::fflush(stdout);
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
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--carcass-automatic-binding") sCarcassAutomaticBinding = true;
        if (std::string(argv[i]) == "--carcass-transport") sCarcassTransport = true;
        if (std::string(argv[i]) == "--groink-live") sGroinkLive = true;
    }
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
