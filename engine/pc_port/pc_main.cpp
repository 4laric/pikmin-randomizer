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
#include "pc_fatal_log.h"
#include "pc_gpu_preference.h"
#include "pc_dev_console.h"
#include "netplay/pc_netplay_det.h"
// Netplay M3 lockstep (issue #880): weak-linked argv capture. Strong-defined
// by pc_port/netplay/pc_netplay_session.cpp in netplay builds only; null in
// the default build, so no session TU is linked there.
__attribute__((weak)) void pc_netplay_session_notify_argv(int argc, char** argv);
#if PIKI_NETPLAY_BUILD
// Netplay launch lane (issue #887): the one-command launcher's pre-init stage
// and settings hook. PIKI_NETPLAY_BUILD is defined for the game exe of
// netplay builds only, so the default exe has no reference to either.
#include "netplay/pc_netplay_launch.h"
#endif
#include "netplay/pc_coop_switch.h"
#include "netplay/pc_input_log.h"
#include "netplay/pc_state_hash.h"
#include "gl/pc_gfx.h"
#include "gl/pc_texpack.h"
#ifdef __ANDROID__
#include "android/pc_android.h"
#endif
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
    if (pc_pikipelago_room_preview() || pc_pikipelago_surface_course()) {
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
    // Every death the process can observe leaves a reason in native.log (and an
    // orderly exit leaves its own marker); see pc_fatal_log.h.
    pc_fatal_log_install();

#if PIKI_NETPLAY_BUILD
    // In-exe self-tests for ctest (settings adoption/persistence, input
    // ownership); they need the game's own settings and window code.
    if (argc >= 2 && std::strcmp(argv[1], "--netplay-launch-selftest") == 0)
        return pc_netplay_launch_selftest(argc, argv);
    // Netplay launch lane (issue #887, B1/B2/M1): the whole session setup is
    // known before engine init on both sides (the host's bootstrap, the
    // joiner's offer code), so it is resolved here, first: private run dir,
    // run bootstrap (appended to argv as --randomizer-seed, the ordinary seed
    // path), private save root, joiner seed, input device. Inert without a
    // launcher switch (it then only validates --netplay-input).
    pc_netplay_launch_preinit(&argc, &argv);
#endif

    // Deterministic netplay mode (M1): parses --netplay-deterministic and the
    // PIKMIN_NETPLAY_* env vars. Must run before the game starts.
    pc_netplay_det_init(argc, argv);

#ifdef __ANDROID__
    // Logcat, carpeta del juego y ruta de guardado: antes de que nada abra un
    // fichero o escriba un mensaje. Sin carpeta no hay assets, y sin assets el
    // juego no arranca: mejor decirlo que caer más adelante sin explicación.
    if (!pc_android_init()) {
        printf("[PC Port Fatal Error] Android storage unavailable\n");
        return 1;
    }
#endif

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
    // Netplay M3/M5a (issues #880 #887): stores argv for --netplay-host /
    // --netplay-join / --netplay-ice-host / --netplay-ice-join /
    // --randomizer-seed.
    // Netplay M4 fix round 1 (M4): the session must see argv before
    // pc_bbft_init runs pc_randomizer_init->update, so the boot-time poll
    // already takes the stream-only path on the client (never reading
    // state.txt) and the publish path on the host. Inert without a netplay
    // switch (and a no-op null check in the default build).
    if (pc_netplay_session_notify_argv != nullptr) pc_netplay_session_notify_argv(argc, argv);
    pc_bbft_init(argc, argv);
    // #942 dev console: inert unless PIKMIN_DEV_CONSOLE=1; refuses under netplay.
    pc_dev_console_init(argc, argv);
    // Netplay harness switches (--input-record/--input-replay and friends).
    // Env vars are read lazily on the first tick; argv wins when both name a
    // path. No-ops unless those switches are set.
    pc_input_log_notify_argv(argc, argv);
    pc_state_hash_notify_argv(argc, argv);
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--dump-texture-names") == 0)
            pc_gfx_set_dump_texture_names(1);
        // PLAN_TEXTURAS_HD: hasta que exista el ajuste del menú (fase 2), la
        // línea de comandos es la única puerta al pack.
        if (std::strcmp(argv[i], "--texture-pack") == 0)
            pc_texpack_request_enable();
    }
    // Netplay M0: direct-boot co-op switch (--coop / PIKMIN_COOP=1, with
    // --coop-captains= / PIKMIN_COOP_CAPTAINS=). Arms pending co-op before
    // any GameCoreSection is constructed; the randomizer direct-boot path
    // never resets pending, so the switch wins there and stays on for
    // every day of the run.
    pc_coop_switch_apply(pc_coop_switch_parse(argc, argv));
    (void)argc;
    (void)argv;

    printf("╔══════════════════════════════════════════╗\n");
    printf("║   Pikmin - Native Linux PC Port          ║\n");
#if PIKI_USE_GLES
    printf("║   OpenGL ES 3.0 Rendering Backend        ║\n");
#else
    printf("║   OpenGL Rendering Backend               ║\n");
#endif
    printf("╚══════════════════════════════════════════╝\n\n");
    fflush(stdout);

    // Initialize SDL2 Window and OpenGL Context FIRST
    printf("[PC Port] Initializing SDL2 window and GL context...\n");
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
#if PIKI_NETPLAY_BUILD
    // Launch lane: settings session guard (both peers) and the joiner's
    // session-only adoption of the host's sim settings, before anything
    // reads a sim setting.
    pc_netplay_launch_post_settings();
#endif
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
#if PIKI_USE_GLES
    printf("[PC Port] Native GX/OpenGL ES, SDL input and persistent save backends active.\n");
#else
    printf("[PC Port] Native GX/OpenGL, SDL input and persistent save backends active.\n");
#endif
    printf("[PC Port] Audio and movie playback are still under development.\n\n");

    gsys->run(new PlugPikiApp());

    printf("[PC Port] Game exited normally.\n");
    return 0;
}
