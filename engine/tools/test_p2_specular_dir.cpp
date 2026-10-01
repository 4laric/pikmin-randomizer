// Standalone probe for the corrected specular half-vector (#429, parent #128).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_specular_dir.cpp -o p2_specular_dir.exe
//
// pc_gfx_init_specular_dir (pc_port/gl/pc_gfx.cpp) delegates its arithmetic to
// p2specular::halfVector (pc_port/pc_p2_specular_dir.h). This proves that the
// half-vector is normalize(-dir + (0,0,1)) -- never a plain reversed direction
// with negative Z -- that the direction is encoded into `pos` scaled by
// 1024*1024, and that the eye-aligned degenerate case falls back to (0,0,1).
#include "../pc_port/pc_p2_specular_dir.h"

#include <cmath>
#include <cstdio>

namespace {

int failures = 0;

bool check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
    return ok;
}

bool near(float a, float b) { return std::fabs(a - b) < 1e-5f; }

const float kScale = 1024.0f * 1024.0f;

void run(const float x, const float y, const float z,
         const float ed[3], const float ep[3]) {
    float dir[3] = {111.0f, 222.0f, 333.0f}, pos[3] = {444.0f, 555.0f, 666.0f};
    p2specular::halfVector(x, y, z, dir, pos);
    for (int i = 0; i < 3; ++i) {
        check(near(dir[i], ed[i]), "half-vector component");
        check(near(pos[i], ep[i]), "scaled direction component");
    }
    // The half-vector must be unit length in every non-degenerate case.
    const float len = std::sqrt(dir[0] * dir[0] + dir[1] * dir[1] + dir[2] * dir[2]);
    check(near(len, 1.0f), "half-vector is unit length");
}

void testBackLight() {
    // Light direction (0,0,-1): half-vector normalize((0,0,1)+(0,0,1)) = (0,0,1).
    const float ed[3] = {0.0f, 0.0f, 1.0f};
    const float ep[3] = {0.0f, 0.0f, 1.0f * kScale};
    run(0.0f, 0.0f, -1.0f, ed, ep);
}

void testSideLight() {
    // Light direction (0,1,0): half-vector normalize((0,-1,0)+(0,0,1)) = (0,-1,1)/sqrt2.
    const float s = 1.0f / std::sqrt(2.0f);
    const float ed[3] = {0.0f, -s, s};
    const float ep[3] = {0.0f, -1.0f * kScale, 0.0f};
    run(0.0f, 1.0f, 0.0f, ed, ep);
}

void testAxisLight() {
    // Light direction (1,0,0): half-vector normalize((-1,0,0)+(0,0,1)) = (-1,0,1)/sqrt2.
    const float s = 1.0f / std::sqrt(2.0f);
    const float ed[3] = {-s, 0.0f, s};
    const float ep[3] = {-1.0f * kScale, 0.0f, 0.0f};
    run(1.0f, 0.0f, 0.0f, ed, ep);
}

void testEyeDegenerate() {
    // Light pointing straight at the eye (0,0,1): the half-vector degenerates and
    // must fall back to (0,0,1); pos still encodes -dir * 1024^2.
    const float ed[3] = {0.0f, 0.0f, 1.0f};
    const float ep[3] = {0.0f, 0.0f, -1.0f * kScale};
    run(0.0f, 0.0f, 1.0f, ed, ep);
}

void testGeneralDirection() {
    // n = (2, -2, 1): -n + e = (-2, 2, 0); mag = sqrt(8) = 2*sqrt(2).
    const float s = 1.0f / (2.0f * std::sqrt(2.0f));
    const float ed[3] = {-2.0f * s, 2.0f * s, 0.0f};
    const float ep[3] = {-2.0f * kScale, 2.0f * kScale, -1.0f * kScale};
    run(2.0f, -2.0f, 1.0f, ed, ep);
}

}  // namespace

int main() {
    testBackLight();
    testSideLight();
    testAxisLight();
    testEyeDegenerate();
    testGeneralDirection();
    if (failures == 0) {
        std::printf("PASS p2_specular_dir\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_specular_dir: %d failures\n", failures);
    return 1;
}
