// Isolated fixtures for pc_p2_skewer.h (#1020).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_skewer_test.cpp -o p2_skewer_test
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include "pc_p2_skewer.h"

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_skewer_test: %s\n", what);
        std::_Exit(1);
    }
}
static bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }
static float dot(const float* a, const float* b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

int main()
{
    using namespace p2skewer;
    const float dirs[][3] = {{0, 0, 100}, {50, 10, 30}, {-20, -5, 80}, {0, 100, 0}, {0, -1, 0}, {3, 0, 0}};
    for (const auto& d : dirs) {
        const Basis b = along(d, 0.0f);
        require(near(dot(b.x, b.x), 1.0f) && near(dot(b.y, b.y), 1.0f) && near(dot(b.z, b.z), 1.0f), "unit columns");
        require(near(dot(b.x, b.y), 0.0f) && near(dot(b.x, b.z), 0.0f) && near(dot(b.y, b.z), 0.0f), "orthogonal");
        const float len = std::sqrt(dot(d, d));
        // the Pikmin's up axis is -X and must follow the spear direction
        require(near(-b.x[0], d[0] / len) && near(-b.x[1], d[1] / len) && near(-b.x[2], d[2] / len), "head along dir");
    }
    // degenerate direction falls back to the facing yaw
    const float zero[3] = {0, 0, 0};
    const Basis f = along(zero, 1.5707963f);
    require(near(-f.x[0], 1.0f) && near(f.x[1], 0.0f), "zero dir uses the fallback yaw");
    // tangent: central difference inside, one-sided at the ends
    const float p[4][3] = {{0, 0, 0}, {10, 0, 0}, {30, 0, 0}, {60, 0, 0}};
    float t[3];
    tangent(p, 4, 0, t);
    require(near(t[0], 10.0f), "start tangent");
    tangent(p, 4, 1, t);
    require(near(t[0], 30.0f), "inner tangent");
    tangent(p, 4, 3, t);
    require(near(t[0], 30.0f), "end tangent");
    // joint rotation tables (P2 poses the Pikmin with the slot joint's own matrix)
    const float ident[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};
    const Basis i0 = fromRotation(ident, 0.0f);
    require(near(i0.x[0], 1.0f) && near(i0.y[1], 1.0f) && near(i0.z[2], 1.0f), "identity rotation, yaw 0");
    const Basis i90 = fromRotation(ident, 1.5707963f);
    require(near(i90.x[0], 0.0f) && near(i90.x[2], -1.0f) && near(i90.z[0], 1.0f), "yaw 90 turns model +x to world -z");
    float rot[9];
    require(armorRotation("attack2", 22.0f, rot), "armor attack2 tabled");
    require(near(rot[0] * rot[0] + rot[3] * rot[3] + rot[6] * rot[6], 1.0f), "armor column is normalised");
    require(!armorRotation("nope", 0.0f, rot), "unknown clip refused");
    require(umiRotation("attack1", 40.0f, 3, rot) && umiRotation("eat1", 10.0f, 6, rot), "umi attack1/eat1 tabled");
    require(!umiRotation("run1", 0.0f, 0, rot) && !umiRotation("attack1", 0.0f, 7, rot), "umi other clips/slots refused");
    std::printf("p2_skewer_test OK (%d checks)\n", gChecks);
    return 0;
}
