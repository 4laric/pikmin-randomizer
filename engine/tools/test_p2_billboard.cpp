// Standalone probe for the camera-facing billboard rotation (#429, parent #128).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_billboard.cpp -o p2_billboard.exe
//
// The renderer replaces a flagged mesh's draw matrix with one whose rotation is
// `scale * active.rotation^T`, keeping the joint pivot translation. This proves
// that `active * billboard` is screen-aligned with the joint scale, the pivot
// lands where the active matrix puts it, and degenerate bases are rejected.
#include "../pc_port/pc_p2_billboard.h"

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

void matmul(float out[3][3], const float a[3][3], const float b[3][3]) {
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            out[i][j] = a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j];
        }
    }
}

void ident(float m[3][3]) {
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            m[i][j] = (i == j) ? 1.f : 0.f;
        }
    }
}

void rotY(float m[3][3], float a) {
    ident(m);
    m[0][0] = std::cos(a);
    m[0][2] = std::sin(a);
    m[2][0] = -std::sin(a);
    m[2][2] = std::cos(a);
}

bool isScaledIdentity(const float m[3][3], float scale) {
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            if (!near(m[i][j], (i == j) ? scale : 0.f)) {
                return false;
            }
        }
    }
    return true;
}

void testIdentityActive() {
    float active[3][3], out[3][3];
    ident(active);
    check(p2billboard::screenRotation(out, active, 1.0f), "identity active accepted");
    check(isScaledIdentity(out, 1.0f), "identity active -> identity rotation");
}

void testRotationCancelled() {
    float active[3][3], out[3][3], product[3][3];
    rotY(active, 0.7f);
    check(p2billboard::screenRotation(out, active, 2.0f), "rotated active accepted");
    matmul(product, active, out);
    check(isScaledIdentity(product, 2.0f), "active * rotation is scaled identity");
}

void testDegenerateRejected() {
    float active[3][3], out[3][3];
    ident(active);
    active[0][1] = active[1][1] = active[2][1] = 0.f;  // collapse a column
    check(!p2billboard::screenRotation(out, active, 1.0f), "degenerate active rejected");
}

// Full 4x4 composition: final = active * billboard(joint, active) must be
// screen-aligned and place the joint pivot at active * pivot.
void testPivotComposition() {
    float active3[3][3], rot[3][3];
    rotY(active3, 0.6f);
    const float s = 0.8f;
    const float px = -4.f, py = 46.f, pz = 0.f;

    check(p2billboard::screenRotation(rot, active3, s), "composition rotation");

    // billboard = T(p) * rot
    float billboard[4][4];
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
            billboard[i][j] = (i == j) ? 1.f : 0.f;
        }
    }
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            billboard[i][j] = rot[i][j];
        }
    }
    billboard[0][3] = px;
    billboard[1][3] = py;
    billboard[2][3] = pz;

    // active = rotation with zero translation
    float active[4][4];
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
            active[i][j] = (i == j) ? 1.f : 0.f;
        }
    }
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            active[i][j] = active3[i][j];
        }
    }

    float final[4][4];
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
            float sum = 0.f;
            for (int k = 0; k < 4; ++k) {
                sum += active[i][k] * billboard[k][j];
            }
            final[i][j] = sum;
        }
    }

    float final3[3][3];
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            final3[i][j] = final[i][j];
        }
    }
    check(isScaledIdentity(final3, s), "active*billboard is screen-aligned with joint scale");
    for (int i = 0; i < 3; ++i) {
        const float want = active3[i][0] * px + active3[i][1] * py + active3[i][2] * pz;
        check(near(final[i][3], want), "billboard pivot placed by the active matrix");
    }
}

}  // namespace

int main() {
    testIdentityActive();
    testRotationCancelled();
    testDegenerateRejected();
    testPivotComposition();
    if (failures == 0) {
        std::printf("PASS p2_billboard\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_billboard: %d failures\n", failures);
    return 1;
}
