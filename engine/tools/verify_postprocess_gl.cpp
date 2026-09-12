// Real-GL regression fixture for the post-process colour-write mask.
//
// This translation unit includes the renderer implementation so it can call
// the private post_apply() path. The production pc_gfx.cpp object must be
// omitted from the fixture link; pc_window.cpp and the remaining native
// support objects are linked as usual.
#include <SDL.h>
#include <GL/gl.h>

#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "../pc_port/pc_window.h"
#include "../pc_port/gl/pc_gfx.cpp"

namespace {

struct Pixel {
    GLubyte r, g, b, a;
};

Pixel read_pixel(GLuint fbo, int x, int y)
{
    Pixel p{0, 0, 0, 0};
    glBindFramebuffer_ptr(GL_FRAMEBUFFER, fbo);
    glReadPixels(x, y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, &p);
    return p;
}

bool same(Pixel a, Pixel b)
{
    return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a;
}

bool check_no_error(const char* phase)
{
    const GLenum error = glGetError();
    if (error == GL_NO_ERROR) return true;
    std::printf("FAIL %s: GL error 0x%04x\n", phase, unsigned(error));
    return false;
}

bool check_mask(const std::array<GLboolean, 4>& expected, const char* phase)
{
    GLboolean actual[4] = {GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE};
    glGetBooleanv(GL_COLOR_WRITEMASK, actual);
    if (actual[0] == expected[0] && actual[1] == expected[1]
        && actual[2] == expected[2] && actual[3] == expected[3]) return true;
    std::printf("FAIL %s: mask is [%d %d %d %d], expected [%d %d %d %d]\n",
                phase, actual[0], actual[1], actual[2], actual[3],
                expected[0], expected[1], expected[2], expected[3]);
    return false;
}

void poison_post_targets()
{
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    const GLuint targets[] = {
        sPostFramebuffer, sBloomFbo[0], sBloomFbo[1],
        sAoFbo[0], sAoFbo[1], sDofFbo[0], sDofFbo[1],
    };
    for (GLuint target : targets) {
        if (!target) continue;
        glBindFramebuffer_ptr(GL_FRAMEBUFFER, target);
        glClearColor(0.91f, 0.07f, 0.19f, 0.37f);
        glClear(GL_COLOR_BUFFER_BIT);
    }
}

Pixel run_case(const std::array<GLboolean, 4>& mask, Pixel& input, bool& resultOk)
{
    glBindFramebuffer_ptr(GL_FRAMEBUFFER, sNativeFramebuffer);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    // Bright input exercises the bloom chain as well as the grading pass.
    glClearColor(0.93f, 0.81f, 0.69f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    input = read_pixel(sNativeFramebuffer, sRenderWidth / 2, sRenderHeight / 2);
    poison_post_targets();
    glColorMask(mask[0], mask[1], mask[2], mask[3]);
    const GLuint result = post_apply(true);
    glFinish();
    resultOk = result == sPostFramebuffer;
    if (!resultOk)
        std::printf("FAIL post_apply returned native framebuffer (%u)\n", result);
    return read_pixel(result, sRenderWidth / 2, sRenderHeight / 2);
}

} // namespace

int main(int argc, char** argv)
{
    const int width = argc > 1 ? std::atoi(argv[1]) : 320;
    const int height = argc > 2 ? std::atoi(argv[2]) : 240;
    SDL_SetMainReady();
    if (!pc_window_init("Post-process GL verification", width, height)) return 2;
    if (SDL_Window* window = SDL_GL_GetCurrentWindow()) SDL_HideWindow(window);
    pc_gfx_init();
    // Apply the drawable-size path as production does; this also guarantees
    // the native target is current before the fixture seeds it.
    pc_gfx_begin_frame();
    pc_gfx_flush_batch();
    if (!sNativeFramebufferReady || !sNativeFramebuffer || !glBindFramebuffer_ptr) {
        std::printf("FAIL native framebuffer unavailable\n");
        pc_window_shutdown();
        return 3;
    }

    sPostEffects = PcPostEffects{};
    sPostEffects.fxaa = true;
    sPostEffects.bloom = true;
    sPostEffects.bloomThreshold = 0.5f;
    sPostEffects.bloomIntensity = 0.35f;
    sPostEffects.colourGrading = true;
    sPostEffects.gamma = 1.7f;
    sPostEffects.brightness = 0.04f;
    sPostEffects.saturation = 0.85f;

    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glDisable(GL_CULL_FACE);
    // Allocate all effect targets once, then poison them before every case.
    // This prevents a previous successful composite from hiding a write-mask
    // regression when an unfixed pass fails to update its destination.
    if (!post_ensure_target() || !post_ensure_program() || !bloom_ensure_targets()) {
        std::printf("FAIL post-process targets/program unavailable\n");
        pc_window_shutdown();
        return 4;
    }
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    Pixel input{0, 0, 0, 0};
    bool resultOk = false;
    const Pixel reference = run_case({GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE}, input, resultOk);
    bool ok = check_no_error("all-enabled reference");
    ok = resultOk && ok;
    if (same(reference, input)) {
        std::printf("FAIL post output did not differ from graded/bloom input\n");
        ok = false;
    }

    const std::array<std::array<GLboolean, 4>, 4> masks = {{
        {{GL_FALSE, GL_TRUE, GL_TRUE, GL_TRUE}},
        {{GL_TRUE, GL_FALSE, GL_TRUE, GL_TRUE}},
        {{GL_TRUE, GL_TRUE, GL_TRUE, GL_FALSE}},
        {{GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE}},
    }};
    for (const auto& mask : masks) {
        Pixel caseInput{0, 0, 0, 0};
        resultOk = false;
        const Pixel actual = run_case(mask, caseInput, resultOk);
        if (!resultOk) ok = false;
        const char* label = (mask[0] == GL_FALSE && mask[1] == GL_FALSE)
                                ? "all-disabled" : "mixed-mask";
        const std::array<GLboolean, 4> expected = mask;
        if (!same(actual, reference)) {
            std::printf("FAIL %s: output differs (%u,%u,%u,%u) vs reference (%u,%u,%u,%u)\n",
                        label, actual.r, actual.g, actual.b, actual.a,
                        reference.r, reference.g, reference.b, reference.a);
            ok = false;
        }
        if (same(actual, caseInput)) {
            std::printf("FAIL %s: output equals untreated input\n", label);
            ok = false;
        }
        if (!check_mask(expected, label)) ok = false;
        if (!check_no_error(label)) ok = false;
    }

    std::printf("postprocess GL mask regression: %s (reference=%u,%u,%u,%u)\n",
                ok ? "PASS" : "FAIL", reference.r, reference.g, reference.b, reference.a);
    pc_window_shutdown();
    return ok ? 0 : 1;
}
