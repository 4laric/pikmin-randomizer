#pragma once
#include <algorithm>
#include <cmath>

namespace pc_coop_menu {
// Normalized render-target coordinates, with origin at the bottom left.
enum class Mode { Fullscreen, Vertical, Horizontal };
struct Rect { float x0, y0, x1, y1; };
inline Rect view(Mode mode, int side)
{
    if (mode == Mode::Vertical) return side == 0 ? Rect{0,0,.5f,1} : Rect{.5f,0,1,1};
    if (mode == Mode::Horizontal) return side == 0 ? Rect{0,.5f,1,1} : Rect{0,0,1,.5f};
    return {0,0,1,1};
}
inline Rect panel(float targetAspect, Mode mode, int side)
{
    if (!std::isfinite(targetAspect) || targetAspect <= 0) targetAspect = 4.f / 3.f;
    const Rect region = view(mode, side);
    const float rw = region.x1-region.x0, rh = region.y1-region.y0;
    // Split menus shrink 30% linearly; the owner may intentionally cover
    // their own center. Fullscreen corners keep the common center clear.
    // Uniform 640x480 fitting avoids distorting labels and the radar.
    const float maxWidth = mode == Mode::Fullscreen ? .40f : .70f;
    const float maxHeight = mode == Mode::Fullscreen ? .44f : .70f;
    const float height = std::min(maxHeight*rh, maxWidth*rw*targetAspect*.75f);
    const float width = height*(4.f/3.f)/targetAspect;
    const float x = side == 0 ? region.x0+.025f*rw : region.x1-.025f*rw-width;
    const bool bottom = mode == Mode::Horizontal && side == 1;
    const float y = bottom ? region.y0+.025f*rh : region.y1-.025f*rh-height;
    return {x,y,x+width,y+height};
}
}
