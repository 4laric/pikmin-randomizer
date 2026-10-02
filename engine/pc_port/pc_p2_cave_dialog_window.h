#ifndef PC_P2_CAVE_DIALOG_WINDOW_H
#define PC_P2_CAVE_DIALOG_WINDOW_H

struct SDL_Window;

// Scalar-only boundary: engine translation units never include SDK/Xlib types.
struct PcP2CaveDialogWindow {
    bool available = false;
    int subsystem = -1;
    unsigned long x11Window = 0;
};

PcP2CaveDialogWindow pc_p2_cave_dialog_window(SDL_Window* window);

#endif
