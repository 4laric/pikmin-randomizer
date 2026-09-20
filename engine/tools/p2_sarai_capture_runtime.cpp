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
#include "pc_p2_sarai_capture_bridge.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Traversable.h"
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
    if (!ok) { std::printf("FAIL SARAI_CAPTURE %s\n", what); std::fflush(stdout); std::_Exit(1); }
}

// Rest-pose mouth offsets from the staged sarai-attack-mouths.txt
// (P2_DEMON_MOUTHS_1) first sampled frame translation columns.
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

static Piki* findAlivePiki()
{
    if (!pikiMgr) return nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive()) return p;
    }
    return nullptr;
}

class SaraiCaptureApp final : public PlugPikiApp {
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
        if (ready) return result;

        Vector3f restA, restB;
        require(readRestOffsets("sarai-attack-mouths.txt", restA, restB), "rest mouth offsets");
        require(host.load("courses/pikmin2room/sarai0.mod", restA, restB), "sarai model");
        require(host.preloadPoseMeshes("sarai-attack-poses.txt"), "attack pose meshes");
        require(host.applyPoseFrame(0) && host.renderedPoseFrame() == 0, "initial pose");
        host.setPosition(Vector3f(0, 100, 100));

        CollPart* const mouth0 = host.mouthPart(0);
        CollPart* const mouth1 = host.mouthPart(1);
        require(mouth0 && mouth1 && mouth0 != mouth1, "two distinct live mouth parts");
        require(mouth0->isBouncySphereType() && mouth1->isBouncySphereType(), "mouth parts are bound spheres");
        const std::uint64_t token = host.ownerToken();
        require(token != 0, "host generation token");

        Piki* piki = findAlivePiki();
        require(piki != nullptr, "live starting Pikmin present");
        const Vector3f pikiStart = piki->getPosition();
        std::printf("SARAI_CAPTURE_BEGIN piki=(%.2f,%.2f,%.2f) mouth0=(%.2f,%.2f,%.2f) slots=2 radius=15\n",
            pikiStart.x, pikiStart.y, pikiStart.z,
            host.mouthCentre(0).x, host.mouthCentre(0).y, host.mouthCentre(0).z);
        std::fflush(stdout);

        // --- capture/admission: source eatPikmin against the live mouth slot ---
        piki->resetPosition(host.mouthCentre(0));
        require(host.capturePiki(piki, 0), "mouth capture admission");
        require(piki->isStickToMouth(), "captured Pikmin marked stuck to mouth");
        require(piki->getStickObject() == static_cast<Creature*>(&host), "stick owner is exact host");
        require(piki->getStickPart() == mouth0, "stick part is exact mouth slot 0");
        require(pc_p2_sarai_piki_bound(piki), "bridge binding live");
        require(pc_p2_sarai_piki_owned_by(piki, &host), "bridge owner is exact host");
        require(pc_p2_sarai_piki_slot(piki) == 0, "bridge slot index 0");
        require(host.carriedCount() == 1, "one carried Pikmin");
        std::puts("SARAI_CAPTURE_LIVE link owner=exact part=exact");
        std::fflush(stdout);

        // --- moving attachment: the carried Pikmin stays linked to the moving mouth ---
        host.mSRT.r.set(0.0f, 0.7f, 0.0f);
        host.mSRT.s.set(1.2f, 0.8f, 1.1f);
        host.setPosition(Vector3f(25, 100, 100));
        require(host.applyPoseFrame(17) && host.renderedPoseFrame() == 17, "move through sampled pose");
        const Vector3f moved = host.mouthCentre(0);
        require(piki->getStickPart() == mouth0 && (mouth0->mCentre - moved).squaredLength() < 0.0001f,
            "captive link follows moving mouth part");
        std::puts("SARAI_CAPTURE_LIVE follow moving_mouth=1");
        std::fflush(stdout);

        // --- drop (fallMeckGround): InteractFallMeck damage + downward velocity ---
        const float healthBefore = piki->mHealth;
        require(host.dropOwned(10.0f, 200.0f) == 1, "fallmeck releases one captive");
        require(!piki->isStickToMouth() && !piki->isStickTo(), "dropped Pikmin detached from mouth");
        require(piki->getStickObject() == nullptr && piki->getStickPart() == nullptr, "dropped Pikmin cleared stick pointers");
        require(!pc_p2_sarai_piki_bound(piki), "dropped Pikmin bridge authority revoked");
        require(host.carriedCount() == 0, "no carried Pikmin after drop");
        require(piki->isAlive(), "Pikmin alive after drop");
        require(std::fabs(piki->mHealth - (healthBefore - 10.0f)) < 0.01f, "fallmeck damage applied");
        require(piki->mVelocity.y == -200.0f, "fallmeck downward velocity");
        std::puts("SARAI_CAPTURE_LIVE drop detached=1 damage=10 vel=-200");
        std::fflush(stdout);

        // --- escape (flickStickTarget): harmless detach + knockback, no damage ---
        piki->resetPosition(host.mouthCentre(1));
        require(host.capturePiki(piki, 1), "second capture into slot 1");
        require(pc_p2_sarai_piki_slot(piki) == 1, "bridge slot index 1");
        const float healthAfterDrop = piki->mHealth;
        require(host.flickOwned() == 1, "flick detaches one captive");
        require(!piki->isStickTo() && !piki->isStickToMouth(), "flick detaches mouth held captive");
        require(!pc_p2_sarai_piki_bound(piki), "flick revokes bridge authority");
        require(std::fabs(piki->mHealth - healthAfterDrop) < 0.01f, "flick applies no damage");
        std::puts("SARAI_CAPTURE_LIVE flick detached=1 damage=0");
        std::fflush(stdout);

        // --- teardown: owner_lost + sceneExit detach the captive, keep it alive ---
        piki->resetPosition(host.mouthCentre(0));
        require(host.capturePiki(piki, 0), "third capture before teardown");
        require(pc_p2_sarai_piki_bound(piki) && host.carriedCount() == 1, "carried before teardown");
        host.sceneExit();
        require(!piki->isStickTo() && !piki->isStickToMouth(), "teardown detaches captive");
        require(piki->getStickObject() == nullptr && piki->getStickPart() == nullptr, "teardown cleared stick pointers");
        require(!pc_p2_sarai_piki_bound(piki), "teardown revokes bridge authority");
        require(piki->isAlive(), "Pikmin alive after teardown");
        require(host.mouthPart(0) == mouth0 && host.mouthPart(1) == mouth1, "teardown preserves live mouth parts");
        pc_p2_sarai_scene_exit();
        require(!piki->isStickTo(), "scene exit stays detached");
        std::puts("PASS SARAI_CAPTURE live_pikmin_capture_drop_flick_teardown");
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
    require(pc_window_init("Sarai capture fixture", 960, 540), "window");
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
        std::printf("P2_SARAI_CAPTURE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
            width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new SaraiCaptureApp());
    return 0;
}
