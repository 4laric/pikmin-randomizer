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
