#pragma once
// Camera-facing vertex groups for baked P2 billboard shapes (#1027).
//
// J3D shape matrix type 1 (billboard, e.g. the Careening Dirigibug balloons,
// BombSarai.cpp createBalloonEffect balloon1..5) replaces the joint rotation
// with the view basis: in view space every vertex sits at the joint position
// plus its scaled local offset. The pose converter bakes those shapes with the
// joint's rest rotation, so seen from the side or back they show their edge or
// their open (culled) back. faceCamera() rewrites each group's baked offsets
// about the group centroid so that, under the model-view rotation R, the
// offset shown in view space equals the baked offset: p' = c + R^T o / s
// (s = the uniform scale of R). Normals turn the same way. Engine-free so
// tools/p2_billboard_groups_test.cpp can check it.
#include <cmath>
#include <istream>
#include <string>
#include <vector>

namespace p2billboardgroups {

struct Range {
    int firstPosition = 0, positions = 0, firstNormal = 0, normals = 0;
};

constexpr int kMaxGroups = 16;
constexpr int kMaxGroupVertices = 4096;

// `P2_BOMBSARAI_BILLBOARD_1 <n>` then n rows `<firstPosition> <positions>
// <firstNormal> <normals>` (root experimental/pikmin2_bombsarai_stage.py).
inline bool parse(std::istream& in, const char* header, std::vector<Range>& out, std::string& error) {
    out.clear();
    std::string word;
    int count = 0;
    if (!(in >> word >> count) || word != header || count < 1 || count > kMaxGroups) {
        error = "bad billboard header";
        return false;
    }
    for (int i = 0; i < count; ++i) {
        Range r;
        if (!(in >> r.firstPosition >> r.positions >> r.firstNormal >> r.normals) || r.firstPosition < 0 ||
            r.firstNormal < 0 || r.positions < 1 || r.normals < 0 || r.positions > kMaxGroupVertices ||
            r.normals > kMaxGroupVertices) {
            error = "bad billboard row";
            out.clear();
            return false;
        }
        out.push_back(r);
    }
    if (in >> word) {
        error = "trailing billboard data";
        out.clear();
        return false;
    }
    return true;
}

// True when every group lies inside the vertex/normal arrays.
inline bool fits(const std::vector<Range>& groups, int positionCount, int normalCount) {
    for (const Range& r : groups)
        if (r.firstPosition + r.positions > positionCount || r.firstNormal + r.normals > normalCount) return false;
    return true;
}

// `rot` is the row-major 3x3 model-to-view part of the draw matrix (rotation
// times a uniform scale). positions/normals are packed xyz floats. Returns
// false (nothing written) for a degenerate matrix or a group out of range.
inline bool faceCamera(const std::vector<Range>& groups, const float rot[3][3], float* positions, int positionCount,
                       float* normals, int normalCount) {
    if (groups.empty() || !fits(groups, positionCount, normalCount)) return false;
    float s2 = 0.0f;
    for (int r = 0; r < 3; ++r) s2 += rot[r][0] * rot[r][0] + rot[r][1] * rot[r][1] + rot[r][2] * rot[r][2];
    s2 /= 3.0f;
    if (!(s2 > 1e-12f) || !std::isfinite(s2)) return false;
    const float invScale = 1.0f / std::sqrt(s2);
    // model = R^T view / s
    auto toModel = [&](const float v[3], float out[3]) {
        for (int c = 0; c < 3; ++c) out[c] = (rot[0][c] * v[0] + rot[1][c] * v[1] + rot[2][c] * v[2]) * invScale;
    };
    for (const Range& g : groups) {
        float c[3] = {0.0f, 0.0f, 0.0f};
        for (int i = 0; i < g.positions; ++i)
            for (int k = 0; k < 3; ++k) c[k] += positions[3 * (g.firstPosition + i) + k];
        for (int k = 0; k < 3; ++k) c[k] /= float(g.positions);
        for (int i = 0; i < g.positions; ++i) {
            float* p = positions + 3 * (g.firstPosition + i);
            const float o[3] = {p[0] - c[0], p[1] - c[1], p[2] - c[2]};
            float m[3];
            toModel(o, m);
            for (int k = 0; k < 3; ++k) p[k] = c[k] + m[k];
        }
        for (int i = 0; i < g.normals; ++i) {
            float* n = normals + 3 * (g.firstNormal + i);
            const float v[3] = {n[0], n[1], n[2]};
            float m[3];
            toModel(v, m);
            const float len = std::sqrt(m[0] * m[0] + m[1] * m[1] + m[2] * m[2]);
            if (len > 1e-6f)
                for (int k = 0; k < 3; ++k) n[k] = m[k] / len;
        }
    }
    return true;
}

} // namespace p2billboardgroups
