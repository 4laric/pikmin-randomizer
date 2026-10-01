#pragma once
// Camera-facing billboard math for flagged MOD meshes (#429, parent #128).
//
// The PC port renders a shape's vertices on the CPU through its per-joint
// matrices and then applies the "active" matrix (the matrix last passed to
// Graphics::useMatrix) on the GPU. Callers differ: some bake lookAt*model into
// the joint matrices and use an identity active matrix, others keep model-space
// joints and apply lookAt*model on the GPU. Both reduce to one rule:
//
//     final = active * joint;   we want final's rotation to be screen-aligned.
//
// So the flagged mesh's draw matrix keeps the joint's pivot translation and
// uniform scale but takes the rotation `scale * active.rotation^T`.
//
// This header is engine-independent (plain 3x3 floats) so the standalone probe
// shares the exact same rotation math as the renderer.
#include <cmath>

namespace p2billboard {

// out = scale * normalised(active).rotation^T. Returns false (leaving `out`
// untouched) when an active basis column degenerates; the caller then keeps the
// plain joint matrix.
inline bool screenRotation(float out[3][3], const float active[3][3], float scale) {
    float basis[3][3];
    for (int j = 0; j < 3; ++j) {
        const float norm = active[0][j] * active[0][j]
                         + active[1][j] * active[1][j]
                         + active[2][j] * active[2][j];
        if (norm < 1e-12f) {
            return false;
        }
        const float inv = 1.0f / std::sqrt(norm);
        for (int i = 0; i < 3; ++i) {
            basis[i][j] = active[i][j] * inv;
        }
    }
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            out[i][j] = scale * basis[j][i];
        }
    }
    return true;
}

}  // namespace p2billboard
