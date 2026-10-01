#pragma once
#include <cmath>

// The horizontal carry command must climb the contacted plane rather than
// retain a downward velocity from the preceding collision step. Flat/downhill
// travel and upward impulses retain their existing vertical velocity.
inline float pc_p2_cargo_uphill_velocity(float vx, float vz, float vy,
                                        float nx, float ny, float nz)
{
    if (!std::isfinite(vx) || !std::isfinite(vz) || !std::isfinite(vy)
        || !std::isfinite(nx) || !std::isfinite(ny) || !std::isfinite(nz)
        || ny <= 0.6f) return vy;
    const float tangentY = -(nx * vx + nz * vz) / ny;
    return std::isfinite(tangentY) && tangentY > 0.0f && vy < tangentY ? tangentY : vy;
}

// A lifted static-map cargo particle must not treat an overhead layer as floor.
// Keep the legacy body deep-penetration threshold as the upper search bound.
inline bool pc_p2_cargo_bounded_ground(bool imported, bool grounded, bool lifted,
                                      bool crewed, bool staticMap, bool platform)
{
    return imported && grounded && lifted && crewed && staticMap && !platform;
}
inline bool pc_p2_cargo_ground_candidate(float height, float ceiling, float nx, float ny, float nz)
{
    const float norm2=nx*nx+ny*ny+nz*nz;
    return std::isfinite(height) && std::isfinite(ceiling) && std::isfinite(norm2)
        && ny>0.f && norm2>0.99f && norm2<1.01f && height<=ceiling;
}
