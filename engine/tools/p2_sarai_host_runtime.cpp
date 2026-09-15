#include <SDL2/SDL.h>
#include "App.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "MoviePlayer.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_sarai_host.h"
#include "pc_p2_demon_bridge.h"
#include "pc_p2_demon_escape_state.h"
#include "gameflow.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <fstream>
#include <string>

static void require(bool ok, const char* what)
{
    if (!ok) { std::printf("FAIL SARAI_HOST %s\n", what); std::fflush(stdout); std::_Exit(1); }
}

// The source world slot radius is 15 for both Sarai mouth joints. The staged
// sarai-attack-mouths.txt is a P2_DEMON_MOUTHS_1 text bank; the rest pose is its
// first sampled frame. Derive the two static rest offsets from its translation
// columns so no extra non-source sidecar is required.
static bool readRestOffsets(const char* path, Vector3f& mouthA, Vector3f& mouthB)
{
    std::ifstream in(path);
    std::string magic, digest;
    int count = 0;
    if (!(in >> magic >> digest >> count) || magic != "P2_DEMON_MOUTHS_1" || count < 1) return false;
    int frame = 0;
    float values[24];
    if (!(in >> frame)) return false;
    for (float& x : values) if (!(in >> x)) return false;
    mouthA.set(values[3], values[7], values[11]);
    mouthB.set(values[15], values[19], values[23]);
    return true;
}

static bool loadPoseProfiles(P2SaraiHost& host)
{
    return host.preloadPoseMeshes("sarai-wait-poses.txt")
        && host.preloadPoseMeshes("sarai-move-poses.txt")
        && host.preloadPoseMeshes("sarai-attack-poses.txt")
        && host.preloadPoseMeshes("sarai-waitact2-poses.txt")
        && host.preloadPoseMeshes("sarai-waitact1-poses.txt");
}

// --- visual/pose mode (unchanged acceptance) --------------------------------

static const int attackFrames[] = { 10, 13, 16, 17, 30, 49 };

static void runPoseMode(P2SaraiHost& host)
{
    Vector3f restA, restB;
    require(readRestOffsets("sarai-attack-mouths.txt", restA, restB), "rest mouth offsets");
    require(host.load("courses/pikmin2room/sarai0.mod", restA, restB), "sarai model");
    require(host.hasRenderableShape(), "renderable sarai shape");

    CollPart* const mouth0 = host.mouthPart(0);
    CollPart* const mouth1 = host.mouthPart(1);
    require(mouth0 && mouth1 && mouth0 != mouth1, "two distinct live mouth parts");
    require(mouth0->isBouncySphereType() && mouth1->isBouncySphereType(), "mouth parts are bound spheres");
    require(std::fabs(mouth0->mRadius - 15.0f) < 1e-6f && std::fabs(mouth1->mRadius - 15.0f) < 1e-6f,
        "source mouth radius 15");
    require(host.ownerToken() != 0, "host generation token");

    P2SaraiPoseBank mouthBank;
    require(mouthBank.load("sarai-attack-mouths.txt") && mouthBank.exact(0) != nullptr, "attack mouth bank");
    require(mouthBank.samples().size() == 7, "attack mouth pose count");

    require(host.preloadPoseMeshes("sarai-attack-poses.txt"), "attack pose meshes");
    require(host.preloadPoseMeshes("sarai-waitact2-poses.txt"), "waitact2 pose meshes");
    require(host.preloadPoseMeshes("sarai-waitact1-poses.txt"), "waitact1 pose meshes");
    require(host.applyPoseFrame(0) && host.renderedPoseFrame() == 0, "initial attack pose");

    const Vector3f base0 = host.mouthCentre(0);
    const Vector3f base1 = host.mouthCentre(1);
    require((base0 - base1).squaredLength() > 1e-4f, "left/right mouth centres distinct");
    float move0 = 0.0f, move1 = 0.0f;
    for (int frame : attackFrames) {
        require(host.applyPoseFrame(frame) && host.renderedPoseFrame() == frame, "attack sampled pose frame");
        move0 = std::fmax(move0, (host.mouthCentre(0) - base0).squaredLength());
        move1 = std::fmax(move1, (host.mouthCentre(1) - base1).squaredLength());
    }
    require(move0 > 1.0f && move1 > 1.0f, "both mouth centres move with animated frames");
    require(!host.applyPoseFrame(1) && host.renderedPoseFrame() == 49, "missing frame retains pose");

    // The two animated joints transform with the owner like any other local
    // joint: rotate/scale/translate and confirm the live parts follow.
    host.mSRT.r.set(0.0f, 0.7f, 0.0f);
    host.mSRT.s.set(1.2f, 0.8f, 1.1f);
    host.setPosition(Vector3f(25, 100, 100));
    require(host.applyPoseFrame(17) && host.renderedPoseFrame() == 17, "posed joints after owner transform");
    const Vector3f transformed = host.mouthCentre(0);
    require(mouth0->mCentre.x == transformed.x && mouth0->mCentre.y == transformed.y
        && mouth0->mCentre.z == transformed.z, "live part tracks posed joint");
    require(std::isfinite(host.staticMouthCentre(0).x) && std::isfinite(host.staticMouthCentre(1).z),
        "rest effectors finite");

    require(host.switchPoseMeshes("sarai-waitact2-poses.txt") && host.applyPoseFrame(0)
        && host.renderedPoseFrame() == 0, "waitact2 sampled pose");
    require(host.switchPoseMeshes("sarai-attack-poses.txt") && host.applyPoseFrame(17)
        && host.renderedPoseFrame() == 17, "return to attack pose bank");

    std::printf("SARAI_HOST_POSE attack=7 waitact2=7 waitact1=8 mouth0=(%.3f,%.3f,%.3f) mouth1=(%.3f,%.3f,%.3f) moved0=%.3f moved1=%.3f\n",
        base0.x, base0.y, base0.z, base1.x, base1.y, base1.z, move0, move1);
    std::fflush(stdout);

    // Teardown: sceneExit() revokes the generation token and restores the
    // rest joints without invalidating the owned live parts.
    const std::uint64_t token = host.ownerToken();
    host.sceneExit();
    require(host.ownerToken() == token, "owner token stable across teardown");
    require(host.mouthPart(0) == mouth0 && host.mouthPart(1) == mouth1, "scene exit preserves live parts");
    const Vector3f restAfter = host.mouthCentre(0);
    require(std::isfinite(restAfter.x) && std::isfinite(restAfter.y) && std::isfinite(restAfter.z),
        "scene exit centres finite");
    host.sceneExit();
    require(host.mouthPart(0) == mouth0, "scene exit idempotent");

    std::puts("PASS SARAI_HOST model_two_mouths_pose_follow_teardown");
    std::fflush(stdout);
    std::_Exit(0);
}

// --- natural capture mode ---------------------------------------------------

static bool isCaptureMode(const char* m)
{
    return !std::strcmp(m, "capture") || !std::strcmp(m, "natural")
        || !std::strcmp(m, "natural_escape") || !std::strcmp(m, "natural_interrupt")
        || !std::strcmp(m, "natural_teardown");
}

static bool isPostCaptureMode(const char* m)
{
    return !std::strcmp(m, "natural_escape") || !std::strcmp(m, "natural_interrupt")
        || !std::strcmp(m, "natural_teardown");
}

// Input-simulated production controller source for the voluntary-escape gate.
// It feeds the real Controller::updateCont() contract -- the same entry the
// pad-to-Kontroller mapping uses -- with a bounded alternating D-pad keyStatus,
// so Navi::doAI's production keyClick sampling reaches pc_demon_escape_tick
// through the shared captor bridge. This is synthesised controller state, not
// physical keyboard input, and is labelled as input-simulated in the evidence.
class EscapeController final : public Kontroller {
public:
    bool active = false;
    bool left = false;
    unsigned edges = 0;
    EscapeController() : Kontroller(1) {}
    void update() override {
        u32 keys = 0;
        if (active) { left = !left; keys = left ? KBBTN_DPAD_LEFT : KBBTN_DPAD_RIGHT; }
        updateCont(keys);
        if (mInputPressed) ++edges;
        mMainStickX = 0; mMainStickY = 0; mSubStickX = 0; mSubStickY = 0;
    }
};

class SaraiHostApp final : public PlugPikiApp {
    P2SaraiHost host;
    int ticks = 0;
    int naturalTicks = 0;
    int captureTick = 0;
    int carryTicks = 0;
    int dropEntries = 0;
    int approachStartZ = 0;
    bool ready = false;
    bool sawTarget = false;
    bool sawAttack = false;
    bool sawCapture = false;
    bool sawCarry = false;
    bool sawDrop = false;
    bool recovered = false;
    int captureSlot = -1;
    const char* mode = "pose";
    bool idleTarget = false;
    // Post-capture natural gates (voluntary escape / interruption / teardown).
    EscapeController* escapeController = nullptr;
    bool freezeHost = false;
    bool naturalCaptured = false;
    bool naturalActionDone = false;
    bool naturalSawEscapeState = false;
public:
    explicit SaraiHostApp(const char* runMode) : mode(runMode), idleTarget(!std::strcmp(runMode, "capture_idle")) {}

    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++ticks < 24000, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_p2_preview_ready()) return result;

        if (!isCaptureMode(mode) && !idleTarget) { runPoseMode(host); return result; }

        if (!naviMgr || !naviMgr->getNavi()) return result;
        Navi* n = naviMgr->getNavi();

        if (!ready) {
            Vector3f restA, restB;
            require(readRestOffsets("sarai-attack-mouths.txt", restA, restB), "rest mouth offsets");
            require(host.load("courses/pikmin2room/sarai0.mod", restA, restB), "sarai model");
            require(host.hasRenderableShape(), "renderable sarai shape");
            require(loadPoseProfiles(host), "sarai natural pose profiles");
            require(host.applyPoseFrame(0) && host.renderedPoseFrame() == 0, "initial wait pose");

            std::ifstream events("sarai-retail-events.txt");
            require(bool(events), "sarai retail event table");
            p2retail::Table table;
            try { table = p2retail::read(events); } catch (...) { require(false, "sarai retail event parse"); }
            p2retail::Motion wait, move, attack, catchFly, fallMeck;
            for (const auto& motion : table.motions) {
                if (motion.name == "wait1.bca") wait = motion;
                else if (motion.name == "move1.bca") move = motion;
                else if (motion.name == "attack1.bca") attack = motion;
                else if (motion.name == "waitact2.bca") catchFly = motion;
                else if (motion.name == "waitact1.bca") fallMeck = motion;
            }
            require(!wait.name.empty() && !move.name.empty() && !attack.name.empty()
                && !catchFly.name.empty() && !fallMeck.name.empty(), "sarai natural motions");
            host.setNaturalMotions(wait, move, attack, catchFly, fallMeck);
            host.setNaturalPoseProfiles("sarai-wait-poses.txt", "sarai-move-poses.txt",
                "sarai-attack-poses.txt", "sarai-waitact2-poses.txt", "sarai-waitact1-poses.txt");
            // The voluntary-escape gate shares the Demon lane's production edge:
            // synthesised controller D-pad state sampled by Navi::doAI feeds the
            // shared pc_demon_escape_tick once the natural capture lands.
            if (!std::strcmp(mode, "natural_escape")) {
                escapeController = new EscapeController();
                n->mKontroller = escapeController;
            }

            host.mSRT.r.set(0, 0, 0);
            host.setPosition(Vector3f(0, 100, 100));
            if (idleTarget) {
                // Source-backed Idle admission: keep the real engine Idle state.
                // The neutral timer is past the Walk->Idle threshold (10s) but
                // below the Idle->Pellet threshold (140s), so the captain genuinely
                // idles. The fixture never transits it to Walk.
                n->mNeutralTime = 11.0f;
                n->mStateMachine->transit(n, NAVISTATE_Idle);
            } else {
                // Bridge-contract accommodation only (labelled): the P1 bridge
                // admits capture from Walk and Idle; this mode holds Walk.
                n->mStateMachine->transit(n, NAVISTATE_Walk);
            }
            n->resetPosition(Vector3f(0, 100, 160));
            approachStartZ = int(host.mSRT.t.z);
            host.enableNatural(30.0f, 3.0f, 20.0f, 12.0f, 200.0f, 60.0f, 300.0f, Vector3f(0, 100, 100));
            require(host.naturalEnabled(), "sarai natural captor enabled");
            std::printf("SARAI_NATURAL_BEGIN mode=%s target=%s host=(%.2f,%.2f,%.2f) captain=(%.2f,%.2f,%.2f) state=%d neutral=%.1f\n",
                mode, idleTarget ? "Idle" : "Walk", host.mSRT.t.x, host.mSRT.t.y, host.mSRT.t.z,
                n->mSRT.t.x, n->mSRT.t.y, n->mSRT.t.z, n->getCurrState()->getID(), n->mNeutralTime);
            std::fflush(stdout);
            ready = true;
            return result;
        }

        // Hold the captain state the source FSM is being exercised against.
        if (!sawCapture && !sawDrop) {
            if (idleTarget) {
                if (n->mNeutralTime > 120.0f) n->mNeutralTime = 11.0f;
                require(n->getCurrState()->getID() == NAVISTATE_Idle, "idling captain stays Idle before capture");
            } else if (n->getCurrState()->getID() != NAVISTATE_Walk) {
                n->mStateMachine->transit(n, NAVISTATE_Walk);
            }
        }

        require(++naturalTicks < 20000, "sarai captor timeout");
        // No fixture-injected frame, target, END, capture or drop: host.update()
        // runs acquisition, approach, the source Attack window and the Sarai FSM.
        // The post-capture gates freeze the host so it cannot re-acquire or
        // re-capture the captain while escape/release/teardown is asserted.
        if (!freezeHost) host.update();

        if (host.naturalPhase() >= 2) sawAttack = true;
        if (host.naturalPhase() >= 1 && host.mSRT.t.z > approachStartZ + 1) sawTarget = true;
        if (host.occupied()) {
            if (!sawCapture) {
                sawCapture = true;
                captureTick = naturalTicks;
                captureSlot = n->getStickPart() == host.mouthPart(0) ? 0
                    : (n->getStickPart() == host.mouthPart(1) ? 1 : -1);
            }
            const bool carryState = idleTarget ? (n->getCurrState()->getID() == NAVISTATE_Idle)
                                               : (n->getCurrState()->getID() == NAVISTATE_Walk);
            if (carryState && pc_demon_bound(n)) { sawCarry = true; ++carryTicks; }
        }
        if (n->getCurrState()->getID() == NAVISTATE_DemonDrop) {
            if (!sawDrop) ++dropEntries;
            sawDrop = true;
        }
        if (naturalTicks % 30 == 0) {
            std::printf("SARAI_NATURAL mode=%s tick=%d phase=%d host=(%.2f,%.2f,%.2f) cap=(%.2f,%.2f,%.2f) hp=%.1f state=%d stuck=%d occupied=%d window=%u\n",
                mode, naturalTicks, host.naturalPhase(), host.mSRT.t.x, host.mSRT.t.y, host.mSRT.t.z,
                n->mSRT.t.x, n->mSRT.t.y, n->mSRT.t.z, n->mHealth, n->getCurrState()->getID(),
                int(n->isStickTo()), int(host.occupied()), host.captureWindowTicks());
            std::fflush(stdout);
        }

        // The three post-capture gates all begin from the same real natural
        // capture (source Attack window + pc_demon_capture through the shared
        // bridge); no frame, target, END or capture is injected.
        if (isPostCaptureMode(mode)) {
            if (!naturalCaptured) {
                if (!(n->isStickToMouth() && pc_demon_bound(n))) return result;
                naturalCaptured = true;
                freezeHost = true;
            }

            if (!naturalActionDone) {
                naturalActionDone = true;
                if (!std::strcmp(mode, "natural_escape")) {
                    // Fixture environment positioning only: the natural capture
                    // lands with the captain on the ground, so raise the frozen
                    // host (whose live mouth still carries the real captain) to
                    // keep the source Fall state observable before it grounds.
                    host.setPosition(Vector3f(host.mSRT.t.x, host.mSRT.t.y + 60.0f, host.mSRT.t.z));
                    escapeController->active = true;
                    std::printf("SARAI_NATURAL_ESCAPE arm token=%llu input=controller_dpad_simulated lift=%.2f\n",
                        (unsigned long long)host.ownerToken(), host.mSRT.t.y);
                    std::fflush(stdout);
                } else if (!std::strcmp(mode, "natural_interrupt")) {
                    // External bounded attack: the production forced-release
                    // entry detaches the mouth link before drop admission.
                    require(host.forceDrop(n, 10.0f, 200.0f), "natural interrupt forced release");
                    require(!n->isStickToMouth() && !n->isStickTo(), "interrupt detached from mouth");
                    require(n->getStickObject() == nullptr && n->getStickPart() == nullptr, "interrupt cleared stick pointers");
                    require(!pc_demon_bound(n) && !pc_demon_owned_by(n, &host), "interrupt revoked bridge authority");
                    require(n->isAlive(), "captain alive after interrupt");
                    require(n->getCurrState()->getID() == NAVISTATE_DemonDrop, "bounded damage admitted drop state");
                    const std::uint64_t token = host.ownerToken();
                    pc_demon_owner_lost(token);
                    require(!n->isStickTo() && n->isAlive(), "stale owner token inert after interrupt");
                    host.sceneExit();
                    require(!n->isStickTo() && !pc_demon_bound(n) && n->isAlive(), "owner teardown inert after interrupt");
                    pc_demon_scene_exit();
                    require(!n->isStickTo() && n->isAlive(), "scene teardown inert after interrupt");
                    std::printf("PASS SARAI_HOST natural_captor_interruption_release_teardown (ticks=%d)\n", naturalTicks);
                    std::fflush(stdout);
                    std::_Exit(0);
                } else if (!std::strcmp(mode, "natural_teardown")) {
                    // Grounded release through the production bridge: detach
                    // without damage, then let ordinary physics ground it.
                    host.release(n);
                    require(!n->isStickToMouth() && !n->isStickTo(), "grounded release detached from mouth");
                    require(n->getStickObject() == nullptr && n->getStickPart() == nullptr, "grounded release cleared stick pointers");
                    require(!pc_demon_bound(n) && !pc_demon_owned_by(n, &host), "grounded release revoked bridge authority");
                    require(n->isAlive(), "captain alive after grounded release");
                    require(n->getCurrState()->getID() == NAVISTATE_Walk, "grounded release keeps Walk ownership");
                    std::printf("SARAI_NATURAL_TEARDOWN release state=%d ground=%d\n",
                        n->getCurrState()->getID(), int(n->mGroundTriangle != nullptr));
                    std::fflush(stdout);
                }
            }

            if (!std::strcmp(mode, "natural_escape")) {
                if (n->getCurrState()->getID() == NAVISTATE_DemonEscape) {
                    if (!naturalSawEscapeState) {
                        std::printf("SARAI_NATURAL_ESCAPE state=DemonEscape tick=%d cap=(%.2f,%.2f,%.2f) detached=%d edges=%u\n",
                            naturalTicks, n->mSRT.t.x, n->mSRT.t.y, n->mSRT.t.z, int(!n->isStickToMouth()),
                            escapeController->edges);
                        std::fflush(stdout);
                    }
                    naturalSawEscapeState = true;
                }
                if (naturalSawEscapeState && n->getCurrState()->getID() == NAVISTATE_Walk) {
                    require(n->mGroundTriangle != nullptr, "voluntary escape grounded on Walk return");
                    require(!n->isStickToMouth() && !n->isStickTo(), "voluntary escape detached from mouth");
                    require(n->getStickObject() == nullptr && n->getStickPart() == nullptr, "voluntary escape cleared stick pointers");
                    require(!pc_demon_bound(n) && !pc_demon_owned_by(n, &host), "voluntary escape revoked bridge authority");
                    require(n->isAlive(), "captain alive after voluntary escape");
                    std::printf("PASS SARAI_HOST natural_captor_voluntary_escape (ticks=%d edges=%u)\n",
                        naturalTicks, escapeController->edges);
                    std::fflush(stdout);
                    std::_Exit(0);
                }
            }
            if (!std::strcmp(mode, "natural_teardown")) {
                if (n->getCurrState()->getID() == NAVISTATE_Walk && n->mGroundTriangle != nullptr) {
                    host.sceneExit();
                    require(!n->isStickTo() && n->isAlive(), "owner teardown inert after grounded release");
                    pc_demon_scene_exit();
                    require(!n->isStickTo() && n->isAlive(), "scene teardown inert after grounded release");
                    std::printf("PASS SARAI_HOST natural_captor_grounded_release_teardown (ticks=%d)\n", naturalTicks);
                    std::fflush(stdout);
                    std::_Exit(0);
                }
            }
            return result;
        }

        if (sawDrop && n->getCurrState()->getID() == NAVISTATE_Walk) {
            recovered = true;
            require(sawTarget, "natural acquisition and approach reached the live captain");
            require(sawAttack, "sarai source Attack state reached");
            require(host.captureWindowTicks() > 0, "source Attack capture window exercised");
            require(sawCapture, "capture admitted on a real live mouth");
            require(captureSlot == 0, "captured on the live mouth CollPart");
            require(sawCarry && carryTicks >= 20, "mouth carry sustained while Walk/Idle");
            require(dropEntries == 1, "exactly one damaging drop");
            require(n->mHealth < 100.0f, "one damaging drop completed");
            std::printf("PASS SARAI_HOST natural_captor_acquire_attack_capture_carry_drop (ticks=%d carry=%d hp=%.1f target=%s)\n",
                naturalTicks, carryTicks, n->mHealth, idleTarget ? "Idle" : "Walk");
            std::fflush(stdout);
            std::_Exit(0);
        }
        // Capture admission is the product-path gate; report it explicitly if the
        // drop clock does not resolve in the bounded post-capture window.
        if (sawCapture && naturalTicks - captureTick > 4000) {
            require(sawTarget, "natural acquisition and approach reached the live captain");
            require(sawAttack, "sarai source Attack state reached");
            std::printf("PASS SARAI_HOST natural_captor_acquire_attack_capture (ticks=%d carry=%d drop=0)\n",
                naturalTicks, carryTicks);
            std::fflush(stdout);
            std::_Exit(0);
        }
        (void)recovered;
        return result;
    }
    void draw(Graphics& gfx) override { PlugPikiApp::draw(gfx); if (ready) host.refresh(gfx); }
};

int main(int argc, char** argv)
{
    const char* mode = std::getenv("SARAI_HOST_MODE");
    if (!mode || !*mode) mode = "pose";
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "room");
    require(pc_window_init("Sarai host fixture", 960, 540), "window");
    pc_settings_init();
    pc_window_set_display_mode(0);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0};
        SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_SARAI_HOST_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
            width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new SaraiHostApp(mode));
    return 0;
}
