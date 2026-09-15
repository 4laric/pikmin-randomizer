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
#include <cstdint>
#include <cstdlib>
#include <vector>
#include <fstream>
#include <sstream>
// Policies link from the pinned integration build; do not embed duplicate implementations.
#include "../pc_port/pc_p2_groink_volley.h"
#include "../pc_port/pc_p2_groink_attack.h"
#include "../pc_port/pc_p2_groink_events.h"
#include "../pc_port/pc_p2_groink_target.h"
// Use the integration build's corrected strike tracker and shared receiver.
#include "../pc_port/pc_p2_groink_strike.h"
#include "../pc_port/pc_p2_groink_hit.h"
#include "../pc_port/pc_p2_projectile_receiver.h"
#include "../pc_port/pc_p2_groink_strike.h"

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

// Per-tick snapshot of an active shell before volley.update, so the moving
// segment (previous -> current) can be classified after the update.
struct ActiveShellSnapshot { std::size_t slot = 0; P2GroinkVec3 position; };

// Source MiniHoudai parameters for the shell sweep. The profile's attack radius
// is 15; the terminal falloff radius is the source attack hit angle (65). The
// proxy health is deliberately small so repeated terminal strikes reach zero.
constexpr float kShellDamage = 10.0f;
constexpr float kShellTerminalRadius = 65.0f;
constexpr float kProxyHealth = 25.0f;

class GroinkAttackApp final : public PlugPikiApp {
    int frames = 0, sourceTicks = 0;
    bool setup = false, probes = false, fired = false, flightCapture = false, flightCaptured = false, terminalCapture = false;
    P2GroinkMapTrace trace;
    P2GroinkSourceClock clock;
    WallProbe wall;
    P2GroinkVolley volley;
    P2GroinkAttack attack;
    P2GroinkGunRotation gun;
    P2GroinkAttackCursor cursor;
    P2GroinkAttackEvent pending = P2GroinkAttackEvent::None;
    bool stopped = false;
    unsigned cycles = 0;
    bool relocated = false, exited = false;
    unsigned acquisitions = 0;
    P2GroinkMuzzle muzzle;
    P2GroinkVec3 owner, target;
    float search = 0, radius = 0, angle = 0;
    unsigned emitted = 0, impacts = 0, primaryImpacts = 0;
    P2ProjectileReceiverRegistry proxy;
    unsigned receiverHits = 0, receiverDeaths = 0;
    bool receiverHealthDecreased = false, strikePlacementPrinted = false;
    float lastReceiverHealth = kProxyHealth;
    // Dedups one shell against one candidate across its whole flight; moving and
    // terminal steps share it so a duplicate position cannot apply twice.
    P2GroinkStrikeTracker flightTracker;
    unsigned flightSteps = 0, flightHits = 0, flightWind = 0;
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
            require(pc_p2_groink_arena_setup("p2-groink-arena.txt"), "arena setup"); loadProfile();
            require(proxy.addAny(kProxyHealth), "proxy receiver");
            require(owner.x==0 && owner.z==0,"target fixture requires center floor stage");
            auto selected=queryNavi();
            require(selected.found,"initial live Navi acquisition");
            target=selected.position; ++acquisitions; beginAttack(); setup = true;
        }
        if (!probes) { runProbes(); probes = true; std::puts("P2_GROINK_MAP_PROBES_PASS"); trace.reset(mapMgr); }
        // Controlled placement: ordinary captain movement/collision can leave
        // the narrow corridor before END. Pin only this private test actor.
        n->resetPosition(Vector3f(relocated?100.0f:0.0f,0,100));
        // The source clock is independent of presentation count; a pause drops debt.
        const int ticks = clock.step(gsys->getFrameTime(), true);
        for (int i = 0; i < ticks; ++i) {
            ++sourceTicks;
            require(sourceTicks < 600, "attack cycles did not finish");
            // Snapshot active shells before the update so each survivor's
            // previous -> current position forms the moving sweep segment. The
            // policy does not record per-step segments itself.
            ActiveShellSnapshot movingSnapshot[P2GroinkVolley::kCapacity];
            std::size_t movingCount = 0;
            for (std::size_t s=0;s<P2GroinkVolley::kCapacity;++s) {
                const P2GroinkShell shell = volley.shell(s);
                if (shell.active) { movingSnapshot[movingCount].slot=s; movingSnapshot[movingCount].position=shell.position; ++movingCount; }
            }
            // Living/common update moves existing shells before FSM emissions.
            require(volley.update(owner,P2GroinkPolicy::kSourceDelta,P2GroinkMapTrace::trace,&trace), "volley update");
            // In-flight creature-hit processing: classify each surviving shell's
            // moving segment against the live Navi, deduped per (slot, token).
            if (movingCount > 0) {
                const Vector3f naviState = n->getPosition();
                const P2GroinkHitCandidate movingCandidate{{naviState.x,naviState.y,naviState.z},
                    P2GroinkCandidateKind::Captain,n->isAlive(),false,radius};
                const std::uint64_t token = reinterpret_cast<std::uint64_t>(n);
                for (std::size_t s=0;s<movingCount;++s) {
                    const P2GroinkShell current = volley.shell(movingSnapshot[s].slot);
                    if (!current.active) continue; // terminal path owns this shell now
                    ++flightSteps;
                    P2GroinkStrikeInput flight;
                    flight.hit.start = movingSnapshot[s].position;
                    flight.hit.end = current.position;
                    flight.hit.radius = radius; flight.hit.terminalRadius = radius;
                    flight.hit.damage = kShellDamage; flight.hit.terminal = false;
                    flight.targetToken = token; flight.attributedToken = token;
                    recordStrike(movingSnapshot[s].slot, flight, movingCandidate, true);
                }
            }
            for (std::size_t j=0;j<volley.terminalCount();++j) {
                const auto& hit = volley.terminals()[j];
                require(hit.step.valid && (hit.step.reason == P2GroinkTerminalReason::Floor || hit.step.reason == P2GroinkTerminalReason::Wall), "non-terrain terminal");
                ++impacts; primaryImpacts += hit.primary;
                std::printf("P2_GROINK_VOLLEY_IMPACT tick=%d slot=%u primary=%d reason=%d xyz=%.3f,%.3f,%.3f\n",sourceTicks,unsigned(hit.slot),hit.primary,int(hit.step.reason),hit.step.end.x,hit.step.end.y,hit.step.end.z);
                // Fixture-pinned placement: this is a placement fixture, not
                // natural pursuit. The live Navi is temporarily put on the
                // retained terminal sweep so the receiver bridge is actually
                // exercised; the canonical targeting pin is restored after.
                const P2GroinkVec3 mid{(hit.step.start.x+hit.step.end.x)*0.5f,
                                       (hit.step.start.y+hit.step.end.y)*0.5f,
                                       (hit.step.start.z+hit.step.end.z)*0.5f};
                n->resetPosition(Vector3f(mid.x,mid.y,mid.z));
                if (!strikePlacementPrinted) {
                    std::puts("P2_GROINK_STRIKE_PLACEMENT fixture_pinned=1 reason=terminal_sweep_midpoint");
                    strikePlacementPrinted = true;
                }
                const Vector3f naviPos = n->getPosition();
                const P2GroinkHitCandidate candidate{{naviPos.x,naviPos.y,naviPos.z},
                    P2GroinkCandidateKind::Captain,n->isAlive(),false,radius};
                P2GroinkStrikeInput strike;
                strike.hit.start = hit.step.start; strike.hit.end = hit.step.end;
                strike.hit.radius = radius; strike.hit.terminalRadius = kShellTerminalRadius;
                strike.hit.damage = kShellDamage; strike.hit.terminal = true;
                const std::uint64_t token = reinterpret_cast<std::uint64_t>(n);
                strike.targetToken = token; strike.attributedToken = token;
                recordStrike(hit.slot, strike, candidate, false);
                // This shell has recycled; forget its flight so a reused pool
                // slot begins a fresh dedup history.
                flightTracker.clearSlot(hit.slot);
                n->resetPosition(Vector3f(relocated?100.0f:0.0f,0,100));
            }
            if (cycles < 2) {
                P2GroinkAttackInput input;
                input.motionStopped = stopped; input.gunRotating = gun.rotating();
                input.gunLocked = gun.locked(); input.event = pending;
                auto commands = attack.step(input,P2GroinkPolicy::kSourceDelta);
                require(commands.valid,"attack commands");
                for (std::size_t j=0;j<commands.count;++j) {
                    using C = P2GroinkAttackCommand;
                    switch(commands.items[j]) {
                    case C::ResumeMotion: stopped=false; break;
                    case C::StopMotion: stopped=true; break;
                    case C::StartAim: gun.start(); break;
                    case C::ReturnGun: gun.finish(); break;
                    case C::EmitVolley: {
                        bool valid=false;
                        auto rotated=p2_groink_rotate_vertical(muzzle,gun.angle(),valid);
                        require(valid && gun.locked() && cursor.frame()==26,"source fire event boundary");
                        auto receipt=volley.emit(rotated,gun.speed(),spread);
                        require(receipt.valid && receipt.count==3,"event-driven volley");
                        emitted+=3; fired=true;
                        std::printf("P2_GROINK_ATTACK_FIRE tick=%d frame=%.1f cycle=%u emitted=%u\n",sourceTicks,cursor.frame(),cycles,emitted);
                        break;
                    }
                    case C::ResolveNextState:
                        ++cycles;
                        std::printf("P2_GROINK_ATTACK_END tick=%d cycles=%u\n",sourceTicks,cycles);
                        {
                            auto selected=queryNavi();
                            P2GroinkAttackEndInput end;
                            end.territoryRadius=100; end.homeRadius=10;
                            end.maxAttackAngleDegrees=45; end.attackable=selected.found;
                            // Fixture owner is at home, path faces forward, no searched
                            // target fallback. This does not execute locomotion.
                            auto decision=p2_groink_attack_end(end);
                            require(decision.valid && decision.useAttackableQuery,"END query decision");
                            std::printf("P2_GROINK_TARGET_END cycle=%u found=%d state=%d\n",cycles,selected.found,int(decision.state));
                            if(cycles==1) {
                                require(decision.state==P2GroinkNextState::Attack,"live target must repeat Attack");
                                target=selected.position; ++acquisitions; beginAttack();
                            } else {
                                require(relocated && decision.state==P2GroinkNextState::WalkPath,"lost target must select path");
                                exited=true; // Preserve stored target on failed query.
                            }
                        }
                        break;
                    default: break; // effects/target acquisition remain host boundaries
                    }
                }
                require(gun.update(muzzle.column3,target,search,radius,P2GroinkPolicy::kSourceDelta),"gun manager update");
                auto step=cursor.animate(stopped?0:1);
                require(step.valid,"attack animation cursor");
                pending=step.event;
            }
            if(emitted==6 && !relocated) {
                // Deliberate test intervention after the second fire event.
                // Subsequent query reads the actual live Navi transform.
                n->resetPosition(Vector3f(100,0,100)); relocated=true;
                std::puts("P2_GROINK_TARGET_RELOCATED x=100 z=100 injected=1");
            }
        }
        if (emitted >= 3 && volley.activeCount() >= 3 && !flightCaptured) flightCapture = true;
        if (impacts == 6 && cycles == 2) terminalCapture = true;
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
            volley.reset(); clock.reset(); flightTracker.reset();
            require(volley.activeCount() == 0 && volley.terminalCount() == 0, "pool reset");
            require(volley.emit(muzzle,100,spread).count == 3, "pool reuse after reset"); volley.reset();
            std::printf("P2_GROINK_VOLLEY_PASS emitted=%u impacts=%u primary=%u reset=1\n",emitted,impacts,primaryImpacts);
            std::puts("P2_GROINK_ATTACK_CYCLES_PASS cycles=2 fire_frame=26 previous_tick_latch=1");
            require(acquisitions==2 && exited,"target acquisition/exit accounting");
            std::puts("P2_GROINK_LIVE_TARGET_PASS acquisitions=2 repeat=1 exit_path=1 single_navi_roster=1 relocation_injected=1 placement_pinned=1");
            require(receiverHits > 0,"no classified receiver strike");
            require(receiverHealthDecreased,"proxy health did not decrease after a Bomb strike");
            require(receiverDeaths == 1,"proxy died marker did not fire exactly once");
            require(flightSteps > 0,"in-flight moving sweep did not execute");
            std::printf("P2_GROINK_FLIGHT_SWEEP_PASS steps=%u hits=%u wind=%u\n",flightSteps,flightHits,flightWind);
            std::printf("P2_GROINK_STRIKE_PASS hits=%u deaths=%u health_start=%.3f health_end=%.3f placement=fixture_pinned\n",
                receiverHits,receiverDeaths,kProxyHealth,lastReceiverHealth);
            std::puts("PASS GROINK_VOLLEY_RUNTIME"); std::fflush(stdout); std::_Exit(0);
        }
    }
private:
    // Classify, dedup per (slot, token), then apply. The bridge stays pure; the
    // tracker is the only mutable state. Moving and terminal steps share it so a
    // duplicate position can never apply twice; recycle via flightTracker.clearSlot.
    void recordStrike(std::size_t slot, const P2GroinkStrikeInput& strike,
                      const P2GroinkHitCandidate& candidate, bool flight) {
        const P2GroinkHitCommand command = p2_groink_classify_hit(strike.hit, candidate);
        if (command.kind == P2GroinkHitKind::None) return;
        if (!flightTracker.firstHit(slot, strike.targetToken)) return;
        const P2GroinkStrikeResult receipt = p2_groink_apply_strike(proxy, strike, candidate);
        const unsigned long long token = (unsigned long long)strike.targetToken;
        const char* kind = command.kind == P2GroinkHitKind::Bomb ? "Bomb" : "Wind";
        if (flight) {
            ++flightHits;
            if (command.kind == P2GroinkHitKind::Wind) ++flightWind;
            std::printf("P2_GROINK_FLIGHT_HIT token=%llu kind=%s damage=%.3f health=%.3f\n",
                token, kind, receipt.damage, receipt.health);
            if (command.kind == P2GroinkHitKind::Wind) {
                std::printf("P2_GROINK_FLIGHT_IMPULSE token=%llu ix=%.3f iy=%.3f iz=%.3f\n",
                    token, receipt.impulse.x, receipt.impulse.y, receipt.impulse.z);
            }
        } else {
            ++receiverHits;
            std::printf("P2_GROINK_RECEIVER_HIT token=%llu kind=%s damage=%.3f health=%.3f\n",
                token, kind, receipt.damage, receipt.health);
        }
        if (receipt.applied && receipt.health < lastReceiverHealth) receiverHealthDecreased = true;
        lastReceiverHealth = receipt.health;
        if (receipt.died) {
            ++receiverDeaths;
            std::printf("P2_GROINK_RECEIVER_DEAD token=%llu\n", token);
        }
    }

    P2GroinkTargetResult queryNavi() {
        Navi* n=naviMgr->getNavi(); require(n!=nullptr,"live Navi missing");
        const Vector3f pos=n->getPosition();
        P2GroinkTargetCandidate c{{pos.x,pos.y,pos.z},n->isAlive(),true,false};
        // The fixed roster is one current Navi. Sphere filtering here is a
        // point approximation, not P2 CellIterator parity.
        const float dx=pos.x-owner.x, dy=pos.y-owner.y, dz=pos.z-owner.z-search*0.5f;
        const bool inSphere=dx*dx+dy*dy+dz*dz<=(search*0.75f)*(search*0.75f);
        auto selected=p2_groink_select_target({muzzle.column3,{0,0,1},search},inSphere?&c:nullptr,inSphere?1:0);
        require(selected.valid,"live target snapshot");
        std::printf("P2_GROINK_TARGET_QUERY tick=%d alive=%d xyz=%.3f,%.3f,%.3f found=%d\n",sourceTicks,c.alive,pos.x,pos.y,pos.z,selected.found);
        return selected;
    }
    void beginAttack() {
        require(cursor.start({44,{11,22,25,32}}),"retail attack event profile");
        attack.begin(); stopped=false; pending=P2GroinkAttackEvent::None;
    }
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
    require(pc_window_init("Groink attack-event runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new GroinkAttackApp()); return 0;
}
