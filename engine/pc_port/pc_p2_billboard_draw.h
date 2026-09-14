#pragma once
// Engine-side billboard draw helpers (#429, parent #128).
//
// The PC port renders shapes through the OGL/DGX backends, not Joint::render.
// A flagged mesh's per-dependency draw matrix keeps the joint's pivot
// translation and uniform scale but takes a screen-aligned rotation derived
// from the matrix the GPU will apply, so the pivot-centred billboard geometry
// faces the camera. The alignment helpers feed a counter the private GL fixture
// reads to prove the path ran.
#include "Matrix4f.h"
#include "pc_p2_billboard.h"

#include <cmath>

namespace p2billboard {

// `out` = `joint` with its 3x3 replaced by scale * active.rotation^T, so
// `active * out` is screen-aligned (rotation = scale * I) and keeps the joint's
// pivot translation. False leaves `out` untouched.
inline bool billboardFromJoint(Matrix4f& out, const Matrix4f& joint, const Matrix4f& active) {
    float scale = 0.f;
    for (int j = 0; j < 3; ++j) {
        const float norm = std::sqrt(joint.mMtx[0][j] * joint.mMtx[0][j]
                                     + joint.mMtx[1][j] * joint.mMtx[1][j]
                                     + joint.mMtx[2][j] * joint.mMtx[2][j]);
        if (!(norm > 1e-6f)) {
            return false;
        }
        scale += norm;
    }
    scale /= 3.f;

    float active3[3][3];
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            active3[i][j] = active.mMtx[i][j];
        }
    }
    float rotation[3][3];
    if (!screenRotation(rotation, active3, scale)) {
        return false;
    }
    out = joint;
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            out.mMtx[i][j] = rotation[i][j];
        }
    }
    return true;
}

// Max off-diagonal magnitude of the column-normalised rotation of `active*mesh`.
// ~0 means the mesh is screen-aligned; used as the GL-fixture assertion.
inline float offDiagonal(const Matrix4f& active, const Matrix4f& mesh) {
    Matrix4f final;
    active.multiplyTo(mesh, final);
    float column[3][3];
    for (int j = 0; j < 3; ++j) {
        const float norm = std::sqrt(final.mMtx[0][j] * final.mMtx[0][j]
                                     + final.mMtx[1][j] * final.mMtx[1][j]
                                     + final.mMtx[2][j] * final.mMtx[2][j]);
        if (norm < 1e-9f) {
            return 1e9f;
        }
        for (int i = 0; i < 3; ++i) {
            column[i][j] = final.mMtx[i][j] / norm;
        }
    }
    float worst = 0.f;
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            if (i != j && std::fabs(column[i][j]) > worst) {
                worst = std::fabs(column[i][j]);
            }
        }
    }
    return worst;
}

struct Stats {
    unsigned long long draws = 0;
    float max_offdiagonal = 0.f;
};

inline Stats& stats() {
    static Stats value;
    return value;
}

}  // namespace p2billboard
