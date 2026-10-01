// Engine-free checks for pc_p2_billboard_groups.h (#1027, Dirigibug balloons).
#include "pc_p2_billboard_groups.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <vector>

static int failures = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); ++failures; } } while (0)
static bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }

using namespace p2billboardgroups;

// Model-to-view part of a yaw rotation by `a` about Y, times `s`.
static void yaw(float a, float s, float rot[3][3]) {
    const float c = std::cos(a) * s, n = std::sin(a) * s;
    const float m[3][3] = {{c, 0, n}, {0, s, 0}, {-n, 0, c}};
    for (int r = 0; r < 3; ++r)
        for (int k = 0; k < 3; ++k) rot[r][k] = m[r][k];
}

int main() {
    // parse
    {
        std::istringstream in("P2_BOMBSARAI_BILLBOARD_1 2\n218 22 217 22\n240 22 239 22\n");
        std::vector<Range> g;
        std::string e;
        CHECK(parse(in, "P2_BOMBSARAI_BILLBOARD_1", g, e));
        CHECK(g.size() == 2 && g[1].firstPosition == 240 && g[1].normals == 22);
        std::istringstream bad("P2_BOMBSARAI_BILLBOARD_1 1\n0 0 0 0\n");
        CHECK(!parse(bad, "P2_BOMBSARAI_BILLBOARD_1", g, e) && g.empty());
        std::istringstream extra("P2_BOMBSARAI_BILLBOARD_1 1\n0 3 0 1\njunk\n");
        CHECK(!parse(extra, "P2_BOMBSARAI_BILLBOARD_1", g, e));
        std::istringstream header("OTHER 1\n0 3 0 1\n");
        CHECK(!parse(header, "P2_BOMBSARAI_BILLBOARD_1", g, e));
    }
    // One group of three vertices around (10, 5, 0) plus an untouched vertex.
    const std::vector<Range> groups = {Range{1, 3, 1, 1}};
    const float base[4][3] = {{100, 100, 100}, {11, 5, 0}, {9, 5, 0}, {10, 6, 1}};
    const float c[3] = {10.0f, 16.0f / 3.0f, 1.0f / 3.0f};
    // Identity view: unchanged.
    {
        float p[4][3], n[2][3] = {{0, 1, 0}, {0, 0, 1}};
        std::copy(&base[0][0], &base[0][0] + 12, &p[0][0]);
        float rot[3][3];
        yaw(0.0f, 1.0f, rot);
        CHECK(faceCamera(groups, rot, &p[0][0], 4, &n[0][0], 2));
        for (int i = 0; i < 4; ++i)
            for (int k = 0; k < 3; ++k) CHECK(near(p[i][k], base[i][k]));
        CHECK(near(n[1][2], 1.0f));
    }
    // Camera yawed 90 degrees (and a uniform 2x model scale): rotating the
    // rewritten offsets by R gives s times the baked offset; the centroid and the
    // vertex outside the group do not move; the group normal faces the camera.
    {
        float p[4][3], n[2][3] = {{0, 1, 0}, {0, 0, 1}};
        std::copy(&base[0][0], &base[0][0] + 12, &p[0][0]);
        float rot[3][3];
        yaw(1.5707963f, 2.0f, rot);
        CHECK(faceCamera(groups, rot, &p[0][0], 4, &n[0][0], 2));
        for (int k = 0; k < 3; ++k) CHECK(near(p[0][k], 100.0f));
        float cc[3] = {0, 0, 0};
        for (int i = 1; i < 4; ++i)
            for (int k = 0; k < 3; ++k) cc[k] += p[i][k] / 3.0f;
        for (int k = 0; k < 3; ++k) CHECK(near(cc[k], c[k]));
        for (int i = 1; i < 4; ++i) {
            const float o[3] = {p[i][0] - c[0], p[i][1] - c[1], p[i][2] - c[2]};
            for (int r = 0; r < 3; ++r) {
                const float view = rot[r][0] * o[0] + rot[r][1] * o[1] + rot[r][2] * o[2];
                CHECK(near(view, 2.0f * (base[i][r] - c[r])));
            }
        }
        const float nv[3] = {rot[0][0] * n[1][0] + rot[0][1] * n[1][1] + rot[0][2] * n[1][2],
                             rot[1][0] * n[1][0] + rot[1][1] * n[1][1] + rot[1][2] * n[1][2],
                             rot[2][0] * n[1][0] + rot[2][1] * n[1][1] + rot[2][2] * n[1][2]};
        CHECK(near(nv[2], 2.0f) && near(nv[0], 0.0f));  // +Z in view (toward the camera), scaled by R
        CHECK(near(n[0][1], 1.0f));                       // normal outside the group untouched
    }
    // Out of range / degenerate: nothing written.
    {
        float p[4][3], n[2][3] = {};
        std::copy(&base[0][0], &base[0][0] + 12, &p[0][0]);
        float rot[3][3];
        yaw(0.7f, 1.0f, rot);
        CHECK(!faceCamera({Range{2, 3, 0, 0}}, rot, &p[0][0], 4, &n[0][0], 2));
        float zero[3][3] = {};
        CHECK(!faceCamera(groups, zero, &p[0][0], 4, &n[0][0], 2));
        for (int i = 0; i < 4; ++i)
            for (int k = 0; k < 3; ++k) CHECK(near(p[i][k], base[i][k]));
    }
    if (failures) {
        std::printf("p2_billboard_groups_test: %d failures\n", failures);
        return 1;
    }
    std::printf("p2_billboard_groups_test: ok\n");
    return 0;
}
