// Bounded live-scene fixture for comparing the PC post-process presets.
// The wrapper includes the settings implementation so it can select presets
// without synthesising menu input. It writes only the three requested PPMs.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "gl/pc_gfx.h"
#include "settings/pc_settings.cpp"

#if defined(_WIN32)
extern "C" {
__declspec(dllexport) unsigned long NvOptimusEnablement                  = 1;
__declspec(dllexport) int           AmdPowerXpressRequestHighPerformance = 1;
}
#endif

namespace {

constexpr int kWarmupFrames = 60;
constexpr int kMeasuredFrames = 60;

void writeFrame(const std::string& path)
{
    // present() restores the native FBO before returning. Read the displayed
    // back buffer explicitly, before doneRender() clears the next frame.
    auto bindFramebuffer = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    GLint previous = 0;
    glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous);
    bindFramebuffer(GL_FRAMEBUFFER, 0);
    int width = 0, height = 0;
    SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &width, &height);
    std::vector<unsigned char> pixels(size_t(width) * size_t(height) * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadBuffer(GL_BACK);
    glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bindFramebuffer(GL_FRAMEBUFFER, previous);
    if (glGetError() != GL_NO_ERROR) std::abort();
    bool nonBlack = false;
    for (unsigned char value : pixels) nonBlack |= value > 8;
    if (!nonBlack) { std::fprintf(stderr, "FAIL empty scene capture\n"); std::abort(); }
    FILE* file = std::fopen(path.c_str(), "wb");
    if (!file) std::abort();
    std::fprintf(file, "P6\n%d %d\n255\n", width, height);
    for (int y = height - 1; y >= 0; --y) {
        if (std::fwrite(pixels.data() + size_t(y) * size_t(width) * 3,
                        1, size_t(width) * 3, file) != size_t(width) * 3) std::abort();
    }
    std::fclose(file);
}

class GraphicsSceneApp final : public PlugPikiApp {
public:
    explicit GraphicsSceneApp(const std::string& output) : mOutput(output) {}

    int idle() override
    {
        const int result = PlugPikiApp::idle();
        ++mObservedFrames;
        if (!mFreeze) {
            if (mObservedFrames > kMaxObservedFrames) {
                printf("[Graphics fixture] gameplay readiness timeout\n");
                std::_Exit(4);
            }
            if (gameflow.mCurrGameSectionID == SECTION_OnePlayer &&
                flowCont.mCurrentStage != nullptr &&
                gameflow.mMoviePlayer != nullptr && !gameflow.mMoviePlayer->mIsActive &&
                !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive && gsys->mPolygonCount > 10000) {
                if (++mAdvanceFrames >= kAdvanceGameplayFrames) {
                    mFreeze = true;
                    mFrames = 0;
                    mElapsed = 0.0;
                    gsys->mTimerState = TS_Off; // Keep diagnostic text out of comparison pixels.
                    printf("[Graphics fixture] scene frozen after %d consecutive gameplay frames (%d total)\n",
                           kAdvanceGameplayFrames, mObservedFrames);
                }
            } else mAdvanceFrames = 0;
        }
        return result;
    }

    void finishSample()
    {
        if (mStage == 0 && mFrames >= kWarmupFrames + kMeasuredFrames) {
            pc_gfx_present();
            glFinish();
            writeFrame(mOutput + "/original.ppm");
            printf("[Graphics fixture] Original: %.3f ms/frame\n", mElapsed / kMeasuredFrames);
            applyGraphicsPreset(sPending, GRAPHICS_PRESET_ENHANCED);
            applyGraphics(sPending);
            mStage = 1;
            mFrames = 0;
            mElapsed = 0.0;
            mFreeze = true;
        } else if (mStage == 1 && mFrames >= kWarmupFrames + kMeasuredFrames) {
            pc_gfx_present();
            glFinish();
            writeFrame(mOutput + "/enhanced.ppm");
            printf("[Graphics fixture] Enhanced: %.3f ms/frame\n", mElapsed / kMeasuredFrames);
            closeMenu();
            mStage = 2;
            mFrames = 0;
            mElapsed = 0.0;
        } else if (mStage == 2 && mFrames >= kWarmupFrames + kMeasuredFrames) {
            pc_gfx_present();
            glFinish();
            writeFrame(mOutput + "/cancelled.ppm");
            printf("[Graphics fixture] Cancelled: %.3f ms/frame\n", mElapsed / kMeasuredFrames);
            std::fflush(stdout);
            std::_Exit(0);
        }
    }

    void draw(Graphics& gfx) override
    {
        // This engine also advances the world clock and child AI from
        // NewPikiGameSection::draw(). Suppressing App::update alone does not
        // freeze the sunlight or actors. Hold both guards during capture.
        const bool wasPaused = gameflow.mPauseAll;
        const float deltaTime = gsys->mDeltaTime;
        if (mFreeze) { gameflow.mPauseAll = true; gsys->mDeltaTime = 0.0f; }
        const auto start = std::chrono::steady_clock::now();
        PlugPikiApp::draw(gfx);
        pc_gfx_flush_batch();
        glFinish();
        const auto end = std::chrono::steady_clock::now();
        if (mFreeze && mFrames >= kWarmupFrames && mFrames < kWarmupFrames + kMeasuredFrames)
            mElapsed += std::chrono::duration<double, std::milli>(end - start).count();
        if (mFreeze) { ++mFrames; finishSample(); }
        gameflow.mPauseAll = wasPaused;
        gsys->mDeltaTime = deltaTime;
    }

    void update() override
    {
        if (!mFreeze) PlugPikiApp::update();
    }

private:
    std::string mOutput;
    static constexpr int kAdvanceGameplayFrames = 90;
    static constexpr int kMaxObservedFrames = 1800;
    int mStage = 0;
    int mFrames = 0;
    int mObservedFrames = 0;
    int mAdvanceFrames = 0;
    double mElapsed = 0.0;
    bool mFreeze = false;
};

} // namespace

int main(int argc, char** argv)
{
    const char* outputEnv = std::getenv("PIKMIN_GRAPHICS_CAPTURE_DIR");
    const char* outputArg = argc >= 2 ? argv[1] : nullptr;
    if (!outputEnv && !outputArg) return 2;
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    // The fixture is intended for unattended capture. pc_window honours this
    // flag while still creating a normal OpenGL context for rendering.
#if defined(_WIN32)
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
#else
    setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1", 1);
#endif
    pc_bbft_init(argc, argv);
    int width = 1280, height = 720;
    if (const char* value = std::getenv("PIKMIN_GRAPHICS_CAPTURE_WIDTH")) width = std::atoi(value);
    if (const char* value = std::getenv("PIKMIN_GRAPHICS_CAPTURE_HEIGHT")) height = std::atoi(value);
    if (!pc_window_init("Graphics scene fixture", width, height)) return 3;
    printf("[Graphics fixture] GL vendor=%s renderer=%s version=%s\n",
           reinterpret_cast<const char*>(glGetString(GL_VENDOR)),
           reinterpret_cast<const char*>(glGetString(GL_RENDERER)),
           reinterpret_cast<const char*>(glGetString(GL_VERSION)));
    pc_settings_init();
    // A user's persisted video mode must not change the fixture dimensions.
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(width, height);
    pc_gfx_set_render_scale(1.0f);
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    sConfig.applyDefaults();
    sPending = sConfig;
    applyGraphicsPreset(sConfig, GRAPHICS_PRESET_ORIGINAL);
    applyGraphics(sConfig);
    gsys->run(new GraphicsSceneApp(outputEnv ? outputEnv : outputArg));
    return 0;
}
