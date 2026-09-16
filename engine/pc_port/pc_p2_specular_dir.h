#pragma once
// Corrected specular half-vector math for the PC GX backend (#429, parent #128).
//
// The upstream fix `gl: implementar GXInitSpecularDir de verdad` corrected the
// host's specular direction setter, which had been a copy of the diffuse
// direction setter. A specular light is not shaped like a diffuse one: its
// "direction" field holds the half-angle vector between the reversed light
// direction and the eye (0,0,1), and its "position" field encodes the raw
// direction scaled by 1024*1024. Storing the plain direction as the half-vector
// left a negative-Z half-vector pointing away from the camera, so the highlight
// never appeared (the Onions were the obvious casualty).
//
// This header is engine-independent (plain floats) so the standalone probe
// shares the exact arithmetic with pc_gfx_init_specular_dir in pc_gfx.cpp.
#include <cmath>

namespace p2specular {

// dir  <- normalize(-(x,y,z) + (0,0,1));      falls back to (0,0,1) when the
//        light points straight at the eye and the half-vector degenerates.
// pos  <- -(x,y,z) * (1024*1024);              the source direction, scaled.
inline void halfVector(const float x, const float y, const float z,
                       float (&dir)[3], float (&pos)[3]) {
    float vx = -x;
    float vy = -y;
    float vz = -z + 1.0f;
    const float mag = std::sqrt(vx * vx + vy * vy + vz * vz);
    if (mag > 1e-6f) {
        const float inv = 1.0f / mag;
        vx *= inv; vy *= inv; vz *= inv;
    } else {
        vx = 0.0f; vy = 0.0f; vz = 1.0f;
    }
    dir[0] = vx; dir[1] = vy; dir[2] = vz;

    const float kSpecularPosScale = 1024.0f * 1024.0f;
    pos[0] = -x * kSpecularPosScale;
    pos[1] = -y * kSpecularPosScale;
    pos[2] = -z * kSpecularPosScale;
}

}  // namespace p2specular
