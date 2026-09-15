// Private Frog renderer acceptance: the corrected specular half-vector
// primitive (pc_port/pc_p2_specular_dir.h -> pc_gfx_init_specular_dir ->
// GL uSpecHalf1) consumed by the ordinary family draw, not a fixture toggle.
//
// Slice 3: boot the room preview (visible, centred 960x540), load the profiled
// Frog material (control 0x93 -> dgxGraphics setLighting GX_COLOR1 GX_AF_SPEC)
// and draw it through the ordinary shape->drawshape batch path with the scene's
// own light (gameCoreSection calcLighting -> setLight(...,7) -> GXInitSpecularDir).
// The renderer's lane-09 counters prove the primitive and the specular channel
// were reached; a byte-compared re-draw gives replay_equal. No light is injected
// and the material state is never forced.
// Never install this fixture as the player executable.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include <cstdio>
#include <cstdlib>
#include <vector>

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
    unsigned control = 0;
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
            control = model->mMaterialCount ? model->mMaterialList[0].mLightingInfo.mCtrlFlag : 0u;
            // EnableSpecular (bit 1) selects the COLOR1 GX_AF_SPEC channel in
            // dgxGraphics::setLighting; refuse to run if the staged material lacks it.
            require((control & u32(LightingControlFlags::EnableSpecular)) != 0, "profiled Frog material has no specular channel");
            int pikmin = 0;
            if (pikiMgr) { Iterator it(pikiMgr); CI_LOOP(it) { Piki* p = static_cast<Piki*>(*it); if (p && p->isAlive()) ++pikmin; } }
            std::printf("FROG_SPECULAR_READY materials=%d control=0x%x\n", model->mMaterialCount, control);
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
        // Ordinary batch draw, exactly what the family draw hook (pc_p2_frog_draw)
        // performs: updateAnim + drawshape. The scene's own calcLighting supplies
        // the specular light 7; nothing is injected and the material is untouched.
        auto renderOrdinary = [&](const char* path) {
            pc_gfx_flush_batch(); glClearColor(0, 0, 0, 1); glDepthMask(GL_TRUE);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
            model->updateAnim(gfx, view, nullptr, nullptr);
            model->drawshape(gfx, *gfx.mCamera, nullptr);
            return capture(path);
        };
        auto first = renderOrdinary("frog-ordinary0.ppm");
        auto again = renderOrdinary("frog-ordinary0-repeat.ppm");
        require(first == again, "same-frame replay changed pixels");
        GLint viewport[4]; glGetIntegerv(GL_VIEWPORT, viewport);
        std::printf("FROG_SPECULAR_RENDER viewport_w=%d viewport_h=%d control=0x%x specular_dir_calls=%u specular_channel_draws=%u replay_equal=1\n",
                    viewport[2], viewport[3], control, pc_gfx_specular_dir_calls(), pc_gfx_specular_channel_draws());
        require(pc_gfx_specular_dir_calls() >= 1, "ordinary draw did not reach pc_gfx_init_specular_dir");
        require(pc_gfx_specular_channel_draws() >= 1, "ordinary draw did not activate the specular channel");
        std::puts("PASS FROG_SPECULAR_RENDER");
        std::fflush(nullptr); std::_Exit(0);
    }
};

int main(int argc, char** argv) {
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires room preview");
    if (!pc_window_init("Frog specular fixture", 960, 540)) return 3;
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    const Uint32 flags = SDL_GetWindowFlags(SDL_GL_GetCurrentWindow());
    std::printf("FROG_SPECULAR_WINDOW w=%d h=%d flags=%s centered=1\n",
                pc_window_get_width(), pc_window_get_height(),
                (flags & SDL_WINDOW_HIDDEN) ? "HIDDEN" : "SHOWN");
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new MaterialApp()); return 0;
}
