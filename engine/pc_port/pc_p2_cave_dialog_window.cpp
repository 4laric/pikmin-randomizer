#include "pc_p2_cave_dialog_window.h"
#include <SDL2/SDL.h>
#if defined(__linux__) && defined(SDL_VIDEO_DRIVER_X11)
#include <SDL2/SDL_syswm.h>
#endif

// This translation unit intentionally has no engine includes: Xlib's Font and
// the Windows SDK's HWND must not enter the engine's global type namespace.
PcP2CaveDialogWindow pc_p2_cave_dialog_window(SDL_Window* window) {
    PcP2CaveDialogWindow result;
#if defined(__linux__) && defined(SDL_VIDEO_DRIVER_X11)
    SDL_SysWMinfo wm{};
    SDL_VERSION(&wm.version);
    result.available = window && SDL_GetWindowWMInfo(window, &wm) == SDL_TRUE;
    if (result.available) {
        result.subsystem = static_cast<int>(wm.subsystem);
        if (wm.subsystem == SDL_SYSWM_X11)
            result.x11Window = static_cast<unsigned long>(wm.info.x11.window);
    }
#else
    (void)window;
#endif
    return result;
}
