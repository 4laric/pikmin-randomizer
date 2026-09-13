/**
 * @file pc_main.cpp
 * @brief Native Linux entry point for the Pikmin PC port.
 *
 * Replaces the original sysBootup.cpp main() which called
 * gsys->Initialise() and gsys->run(new PlugPikiApp()).
 *
 * This file will grow in later stages to include SDL2 window creation,
 * OpenGL context setup, and input polling.
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#if PIKI_USE_JAUDIO
int pc_jaudio_integration_test();
#endif

// Game headers
#include "system.h"
#include "App.h"
#include "sysNew.h"

/**
 * @brief Entry point for the Linux PC port.
 *
 * Currently this initializes the game system with stubs and enters
 * the main loop. Since all Dolphin SDK calls are stubbed, this will
 * "run" but produce no visible output yet.
 */
#include <SDL.h>

#ifdef _WIN32
// Laptops with switchable graphics start a process on the integrated GPU unless
// the executable asks otherwise. Both vendors read that request the same way:
// the driver DLL looks up an exported symbol in the process image at load time,
// before any context exists, so this cannot be done from code that runs later.
//
// These have to live in the object that is linked straight into the executable
// -- pc_main.cpp is, see PC_PORT_SOURCES -- because an export from a static
// library reaches the .exe export table only if something already pulled the
// object in. Nothing references either variable, so nothing would.
extern "C" {
__declspec(dllexport) unsigned long NvOptimusEnablement                  = 1;
__declspec(dllexport) int           AmdPowerXpressRequestHighPerformance = 1;
}
#endif

#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"

namespace {
// Small, centered window for the experimental P2 room preview so a wall of test
// runs stays readable and out of the way. Overridable with
// PIKMIN_P2_ROOM_WINDOW=WxH, or =off to keep the persisted/desktop size.
bool pc_test_window_size(int& width, int& height) {
    const char* value = std::getenv("PIKMIN_P2_ROOM_WINDOW");
    if (value && (!std::strcmp(value, "0") || !std::strcmp(value, "off"))) return false;
    if (value) {
        int customWidth = 0, customHeight = 0;
        if (std::sscanf(value, "%dx%d", &customWidth, &customHeight) == 2
                && customWidth >= 320 && customHeight >= 240) {
            width = customWidth;
            height = customHeight;
            return true;
        }
        if (!std::strcmp(value, "1") || !std::strcmp(value, "small")) {
            width = 960;
            height = 540;
            return true;
        }
    }
    if (pc_pikipelago_room_preview()) {
        width = 960;
        height = 540;
        return true;
    }
    return false;
}
}

int main(int argc, char* argv[])
{
    // Disable stdout buffering so we see logs immediately before any crash
    setvbuf(stdout, NULL, _IONBF, 0);

    // SDL_MAIN_HANDLED is defined for this build, which means the application
    // owns main() and SDL2main is not linked. The other half of that contract
    // is telling SDL so before the first SDL_Init. It is close to a no-op on
    // Linux, which is why its absence went unnoticed there, but Windows needs
    // it to set up the instance handle and command line.
    SDL_SetMainReady();

    // Before SDL_Init, and before anything can touch GL: on Linux the vendor
    // is selected by libglvnd the first time it is asked, and by the time a
    // context exists the choice has already been made. No-op elsewhere.
    pc_gpu_preference_apply();

#if PIKI_USE_JAUDIO
    if (argc == 2 && std::strcmp(argv[1], "--audio-self-test") == 0)
        return pc_jaudio_integration_test();
#endif
    pc_bbft_init(argc, argv);

    printf("╔══════════════════════════════════════════╗\n");
    printf("║   Pikmin - Native Linux PC Port          ║\n");
    printf("║   Stage 4: OpenGL Rendering Backend      ║\n");
    printf("╚══════════════════════════════════════════╝\n\n");
    fflush(stdout);

    // Initialize SDL2 Window and OpenGL Context FIRST
    printf("[PC Port] Initializing SDL2 Window and OpenGL...\n");
    fflush(stdout);
    int windowWidth = 1280, windowHeight = 720;
    const bool smallTestWindow = pc_test_window_size(windowWidth, windowHeight);
    if (!pc_window_init("Open Nectar", windowWidth, windowHeight)) {
        printf("[PC Port Fatal Error] Could not initialize window/OpenGL!\n");
        fflush(stdout);
        return 1;
    }

    printf("[PC Port] Loading persisted settings...\n");
    fflush(stdout);
    pc_settings_init();
    if (smallTestWindow) {
        pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
        pc_window_set_window_size(windowWidth, windowHeight);
        pc_window_center();
        printf("[PC Port] Experimental preview window set to %dx%d windowed and centered "
               "(override with PIKMIN_P2_ROOM_WINDOW=WxH or =off).\n", windowWidth, windowHeight);
        fflush(stdout);
    }

    printf("[PC Port] Initializing game system...\n");
    fflush(stdout);
    gsys->Initialise();
    pc_settings_p2d_init();

    printf("[PC Port] Creating node manager...\n");
    nodeMgr = new NodeMgr();

    printf("[PC Port] Starting game application...\n");
    printf("[PC Port] Native GX/OpenGL, SDL input and persistent save backends active.\n");
    printf("[PC Port] Audio and movie playback are still under development.\n\n");

    gsys->run(new PlugPikiApp());

    printf("[PC Port] Game exited normally.\n");
    return 0;
}
