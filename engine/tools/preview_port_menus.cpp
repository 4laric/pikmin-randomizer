// Standalone visual fixture. Includes the menu implementation to set page
// state without adding debug controls to the game or touching a save/config.
// The wrapper omits the production pc_settings.cpp object when linking.
#include <SDL.h>
#include <GL/gl.h>
#include <algorithm>
#include <iterator>
#include "settings/pc_settings.cpp"

static bool sameNonGraphicsSettings(const PcConfig& a, const PcConfig& b)
{
    return a.windowWidth == b.windowWidth && a.windowHeight == b.windowHeight &&
           a.displayMode == b.displayMode && a.refreshRate == b.refreshRate &&
           a.vsync == b.vsync && a.renderScale == b.renderScale &&
           a.aspectRatioMode == b.aspectRatioMode && a.fpsMode == b.fpsMode &&
           a.controlMode == b.controlMode && a.mouseSensitivity == b.mouseSensitivity &&
           a.stickDeadZone == b.stickDeadZone && a.stickInvert == b.stickInvert &&
           a.cStickInvert == b.cStickInvert && a.chainActions == b.chainActions &&
           a.mouseWheelAction == b.mouseWheelAction && a.pikiLimit == b.pikiLimit &&
           a.dayMinutes == b.dayMinutes && a.debugKeys == b.debugKeys &&
           std::equal(std::begin(a.keyboardBindings), std::end(a.keyboardBindings),
                      std::begin(b.keyboardBindings)) &&
           std::equal(std::begin(a.gamepadBindings), std::end(a.gamepadBindings),
                      std::begin(b.gamepadBindings));
}

static int assertGraphicsPresets()
{
    sConfig.applyDefaults();
    sConfig.windowWidth = 1920;
    sConfig.windowHeight = 1080;
    sConfig.fpsMode = 2;
    sConfig.pikiLimit = 500;
    const PcConfig baseline = sConfig;

    sPending = sConfig;
    applyGraphicsPreset(sPending, GRAPHICS_PRESET_ORIGINAL);
    if (graphicsPresetFor(sPending) != GRAPHICS_PRESET_ORIGINAL ||
        sPending.antialiasing != 0 || sPending.fog != 1 || sPending.bloom != 0 ||
        sPending.ssao != 0 || sPending.dof != 0 || sPending.anisotropy != 0 ||
        sPending.colourGrading != 0 || sPending.gamma != 1.0f ||
        sPending.brightness != 0.0f || sPending.saturation != 1.0f ||
        !sameNonGraphicsSettings(sPending, baseline)) return 5;

    applyGraphicsPreset(sPending, GRAPHICS_PRESET_ENHANCED);
    if (graphicsPresetFor(sPending) != GRAPHICS_PRESET_ENHANCED ||
        sPending.antialiasing != 1 || sPending.fog != 1 || sPending.bloom != 1 ||
        sPending.ssao != 0 || sPending.dof != 0 || sPending.anisotropy != 8 ||
        sPending.colourGrading != 0 || sPending.gamma != 1.0f ||
        sPending.brightness != 0.0f || sPending.saturation != 1.0f ||
        !sameNonGraphicsSettings(sPending, baseline)) return 6;

    sPending.bloom = 2;
    if (graphicsPresetFor(sPending) != GRAPHICS_PRESET_CUSTOM) return 7;
    return 0;
}

int main(int argc, char** argv)
{
    if (argc != 4) return 2;
    SDL_SetMainReady();
    if (!pc_window_init("Port menu verification", std::atoi(argv[2]), std::atoi(argv[3]))) return 2;
    gsys->Initialise();
    pc_settings_p2d_init();
    const int assertionResult = assertGraphicsPresets();
    if (assertionResult != 0) return assertionResult;
    sConfig.applyDefaults();
    rebuildResolutionList();

    for (int page = 0; page < 20; ++page) {
        sPending = sConfig;
        sMenuOpen = page != 15;
        sSelection = ROW_DISPLAY_MODE;
        sControlSelection = sGamepadSelection = sModsSelection = 0;
        sWaitingForKey = sWaitingForButton = sNewGamePromptOpen = false;
        sInControlsSubmenu = page == 1;
        sInGamepadSubmenu = page == 2;
        sInAdvancedSubmenu = page == 3;
        sInResolutionSubmenu = page == 4;
        sInModsSubmenu = page == 5;
        sInGraphicsSubmenu = page >= 17;
        sVideoConfirmActive = page == 6;
        sVideoConfirmStartMs = SDL_GetTicks();
        if (page == 4) openResolutionSubmenu();
        if (page == 9) {
            sSelection = ROW_FPS_MODE;
            sPending.fpsMode = 2;
        }
        if (page == 10) {
            sInControlsSubmenu = true;
            sControlSelection = PC_KEY_ACT_COUNT - 1;
        }
        if (page == 11) {
            sInModsSubmenu = true;
            sModsSelection = 3;
            sPending.pikiLimit = 500;
        }
        if (page == 12) {
            sInControlsSubmenu = true;
            sWaitingForKey = true;
        }
        if (page == 13) {
            sInGamepadSubmenu = true;
            sWaitingForButton = true;
        }
        if (page == 14) sSelection = ROW_SAVE;
        if (page == 17) applyGraphicsPreset(sPending, GRAPHICS_PRESET_ORIGINAL);
        if (page == 18) applyGraphicsPreset(sPending, GRAPHICS_PRESET_ENHANCED);
        if (page == 19) {
            sPending.bloom = 2;
            sPending.anisotropy = 16;
            sGraphicsSelection = kGraphicsRowCount - 1;
        }

        pc_gfx_begin_frame();
        glClearColor(0.15f, 0.25f, 0.4f, 1);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        if (page == 7 || page == 8) {
            sNewGamePromptOpen = true;
            sNewGamePromptChoice = page - 7;
            pc_newgame_prompt_draw();
        } else {
            pc_settings_draw();
        }
        pc_gfx_flush_batch();
        glFinish();
        GLint viewport[4];
        glGetIntegerv(GL_VIEWPORT, viewport);
        const int w = viewport[2], h = viewport[3];
        std::vector<unsigned char> pixels(w * h * 3);
        glPixelStorei(GL_PACK_ALIGNMENT, 1);
        glReadPixels(viewport[0], viewport[1], w, h, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
        char basename[32];
        std::snprintf(basename, sizeof(basename), "/page-%02d.ppm", page);
        const std::string name = std::string(argv[1]) + basename;
        FILE* file = std::fopen(name.c_str(), "wb");
        if (!file) return 3;
        std::fprintf(file, "P6\n%d %d\n255\n", w, h);
        for (int y = h - 1; y >= 0; --y) {
            if (std::fwrite(pixels.data() + y * w * 3, 1, w * 3, file) != size_t(w * 3)) return 4;
        }
        std::fclose(file);
    }
    // The standalone fixture does not run the game's application teardown.
    std::_Exit(0);
}
