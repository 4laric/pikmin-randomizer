// Infrastructure-only GL isolation probe; no game acceptance evidence.
#define SDL_MAIN_HANDLED
#include <SDL2/SDL.h>
#include <windows.h>
#include <GL/gl.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
int main(int argc, char** argv) {
    bool hidden = argc > 1 && !std::strcmp(argv[1], "hidden");
    int seconds = argc > 2 ? std::atoi(argv[2]) : 4;
    HWND initial = GetForegroundWindow();
    SDL_SetMainReady();
    if(SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER)) return 2;
    auto* window=SDL_CreateWindow("GL lane isolation probe", SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,960,540,SDL_WINDOW_OPENGL | (hidden?SDL_WINDOW_HIDDEN:SDL_WINDOW_SHOWN));
    if(!window) return 3;
    auto context=SDL_GL_CreateContext(window);
    if(!context) return 4;
    SDL_GL_SetSwapInterval(0);
    unsigned frames=0;
    Uint32 start=SDL_GetTicks();
    bool correct=true, focus=true;
    while(SDL_GetTicks()-start < unsigned(seconds*1000)) {
        // No event pumping, keyboard, mouse, gamepad or desktop input injection.
        glClearColor(hidden?0.25f:0.75f,0.5f,0.0f,1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        unsigned char pixel[4]{};
        glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
        correct &= pixel[0] >= (hidden?62:189) && pixel[0] <= (hidden?66:193);
        correct &= glGetError()==GL_NO_ERROR;
        if(hidden) focus &= GetForegroundWindow()==initial;
        SDL_GL_SwapWindow(window);
        ++frames; SDL_Delay(16);
    }
    std::printf("GL_SMOKE hidden=%d frames=%u pixels=%d focus_unchanged=%d renderer=%s\n",
        hidden,frames,correct,focus,glGetString(GL_RENDERER));
    SDL_GL_DeleteContext(context); SDL_DestroyWindow(window); SDL_Quit();
    return correct && focus && frames>0 ? 0:5;
}
