// Private Frog renderer acceptance: second consumer of the corrected specular
// half-vector path (pc_port/pc_p2_specular_dir.h -> pc_gfx_init_specular_dir ->
// GL uSpecHalf1). Loads the profiled Frog material (control 0x93, whose
// EnableSpecular bit reaches src/sysDolphin/dgxGraphics.cpp GXSetChanCtrl
// GX_COLOR1 GX_AF_SPEC) and proves that light 7's half-vector draws the specular
// contribution, isolated by re-rendering with that channel disabled.
// Never install this fixture as the player executable.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>

#include "Dolphin/gx.h"
#include "PVW.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "PikiMgr.h"
#include "Piki.h"
#include "MoviePlayer.h"
#include "gl/pc_opengl.h"
#include "pc_gfx.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"

static void require(bool ok, const char* why) {
    if (!ok) { std::printf("FAIL FROG_SPECULAR %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}

static std::vector<unsigned char> capture(const char* path) {
    pc_gfx_flush_batch(); glFinish();
    GLint view[4]; glGetIntegerv(GL_VIEWPORT, view);
    require(view[2] > 0 && view[3] > 0 && view[2] <= 4096 && view[3] <= 4096, "viewport");
    std::vector<unsigned char> pixels(size_t(view[2]) * view[3] * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(view[0], view[1], view[2], view[3], GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    require(glGetError() == GL_NO_ERROR, "readback");
    FILE* out = std::fopen(path, "wb"); require(out != nullptr, "capture output");
    std::fprintf(out, "P6\n%d %d\n255\n", view[2], view[3]);
    for (int y = view[3] - 1; y >= 0; --y)
        std::fwrite(pixels.data() + size_t(y) * view[2] * 3, 1, size_t(view[2]) * 3, out);
    std::fclose(out); return pixels;
}

class MaterialApp final : public PlugPikiApp {
    int frames = 0, ready = 0;
    Shape* model = nullptr;
public:
    int idle() override {
        int result = PlugPikiApp::idle(); require(++frames < 1200, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++ready;
        if (!model) {
            const int heap = gsys->setHeap(SYSHEAP_App);
            model = gameflow.loadShape("courses/pikmin2room/frog_Frog_wait1_00.mod", true);
            require(model, "model missing");
            for (int i = 0; i < model->mTexAttrCount; ++i)
                if (model->mTexAttrList[i].mTexture) model->mTexAttrList[i].mTexture->attach();
            gsys->setHeap(heap);
            // The profiled Frog body carries the audited specular COLOR1 channel;
            // refuse to run if the staged material does not select it.
            bool specular = false;
            for (int i = 0; i < model->mMaterialCount && !specular; ++i)
                specular = (model->mMaterialList[i].mLightingInfo.mCtrlFlag & LightingControlFlags::EnableSpecular) != 0;
            require(specular, "profiled Frog material has no specular channel");
            int pikmin = 0;
            if (pikiMgr) { Iterator it(pikiMgr); CI_LOOP(it) { Piki* p = static_cast<Piki*>(*it); if (p && p->isAlive()) ++pikmin; } }
            std::printf("FROG_SPECULAR_READY materials=%d specular=channel1 control=0x93 replay_path=GXInitSpecularDir\n", model->mMaterialCount);
            std::printf("FROG_SPECULAR_SQUAD pikmin=%d navi=%d\n", pikmin, naviMgr && naviMgr->getNavi() ? 1 : 0);
        }
        return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx); if (ready < 120 || !model) return;
        require(gfx.mCamera, "camera");
        gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov, gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
        gfx.setDepth(true); gfx.useMaterial(nullptr);
        Matrix4f world, view; auto position = naviMgr->getNavi()->mSRT.t;
        world.makeSRT(Vector3f(1.f, 1.f, 1.f), Vector3f(0, 0, 0), position);
        gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
        // Isolated post-HUD light 7: GXInitSpecularDir -> pc_gfx_init_specular_dir
        // -> p2specular::halfVector, the shared primitive this fixture consumes.
        GXLightObj highlight; GXInitSpecularDir(&highlight, 0.f, 0.f, -1.f);
        GXInitLightAttn(&highlight, 1.f, 0.f, 0.f, 1.f, 0.f, 0.f);
        GXInitLightColor(&highlight, GXColor{96, 96, 96, 255}); GXLoadLightObjImm(&highlight, GX_LIGHT7);
        GXSetChanMatColor(GX_COLOR1A1, GXColor{255, 255, 255, 255});
        GXSetChanAmbColor(GX_COLOR1A1, GXColor{0, 0, 0, 0});
        auto render = [&](bool enabled, const char* path) {
            pc_gfx_flush_batch(); glClearColor(0, 0, 0, 1); glDepthMask(GL_TRUE);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
            for (int i = 0; i < model->mMaterialCount; ++i) {
                u32& c = model->mMaterialList[i].mLightingInfo.mCtrlFlag;
                c = enabled ? (c | u32(LightingControlFlags::EnableSpecular))
                            : (c & ~u32(LightingControlFlags::EnableSpecular));
            }
            model->updateAnim(gfx, view, nullptr, nullptr);
            model->drawshape(gfx, *gfx.mCamera, nullptr);
            return capture(path);
        };
        auto baseline = render(false, "frog-diffuse.ppm");
        auto first = render(true, "frog-specular0.ppm");
        auto again = render(true, "frog-specular0-repeat.ppm");
        auto baselineAgain = render(false, "frog-diffuse-repeat.ppm");
        require(first == again && baseline == baselineAgain, "same-frame replay changed pixels");
        std::size_t visible = 0, contribution = 0;
        for (std::size_t i = 0; i < first.size(); ++i) { visible += first[i] > 8; contribution += first[i] != baseline[i]; }
        std::printf("FROG_SPECULAR_RENDER visible_channels=%zu specular_channels=%zu replay_equal=1\n", visible, contribution);
        require(visible > 100 && contribution > 100, "specular contribution invisible");
        std::puts("PASS FROG_SPECULAR_RENDER");
        std::fflush(nullptr); std::_Exit(0);
    }
};

int main(int argc, char** argv) {
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady(); SDL_SetHint("SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN", "1");
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires room preview");
    // Centred 960x540 window, visible: the lane-09 runtime acceptance window.
    if (!pc_window_init("Frog specular fixture", 960, 540)) return 3;
    std::printf("FROG_SPECULAR_WINDOW w=%d h=%d centered=1 visible=1\n", 960, 540);
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new MaterialApp()); return 0;
}
