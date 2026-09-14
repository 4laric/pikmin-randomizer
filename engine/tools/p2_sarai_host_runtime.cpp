#include <SDL2/SDL.h>
#include "App.h"
#include "MoviePlayer.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_sarai_host.h"
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

static const int attackFrames[] = { 10, 13, 16, 17, 30, 49 };

class SaraiHostApp final : public PlugPikiApp {
    P2SaraiHost host;
    int ticks = 0;
    bool ready = false;
public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++ticks < 6000, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_p2_preview_ready()) return result;

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
        return result;
    }
    void draw(Graphics& gfx) override { PlugPikiApp::draw(gfx); if (ready) host.refresh(gfx); }
};

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "room");
    require(pc_window_init("Sarai host fixture", 960, 540), "window");
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
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new SaraiHostApp());
    return 0;
}
