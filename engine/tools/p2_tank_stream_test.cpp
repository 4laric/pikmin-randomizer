// Watery Blowhog stream layout (engine-free). Checks reach, ordering and determinism.
#include "pc_p2_tank_stream.h"
#include <cmath>
#include <cstdio>
using namespace p2tankstream;
static int failures = 0;
#define CHECK(c) do { if (!(c)) { std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #c); ++failures; } } while (0)
int main() {
    Point a[MAX_POINTS], b[MAX_POINTS];
    CHECK(layout(0, 0, 0, 0, 1, 0.0f, 0, a) == 0);   // not yet out of the nose
    CHECK(layout(0, 0, 0, 0, 1, 5.0f, 0, a) == 0);
    const int n = layout(10, 6, 20, 1, 0, 100.0f, 0, a);
    CHECK(n == MAX_POINTS);
    CHECK(a[0].kind == Kind::Muzzle && a[0].x == 10 && a[0].z == 20);
    float prev = 0;
    for (int i = 1; i < n; ++i) { CHECK(a[i].x - 10 >= prev - 1e-4f); prev = a[i].x - 10; CHECK(a[i].x - 10 <= 100.0f + 1e-3f); CHECK(std::fabs(a[i].z - 20) < 1e-4f); CHECK(a[i].y <= 6.0f + 1e-4f); }
    CHECK(a[n - 1].kind == Kind::Tip && std::fabs(a[n - 1].x - 110.0f) < 1e-3f);
    // Deterministic: same inputs, same output; tick parity only shifts the drops.
    CHECK(layout(10, 6, 20, 1, 0, 100.0f, 0, b) == n);
    for (int i = 0; i < n; ++i) CHECK(a[i].x == b[i].x && a[i].y == b[i].y && a[i].z == b[i].z);
    layout(10, 6, 20, 1, 0, 100.0f, 1, b);
    CHECK(b[1].x > a[1].x);
    // Reach never exceeds the range even when it is growing.
    for (float r = 12; r < 120; r += 7) { const int m = layout(0, 0, 0, 0, 1, r, 3, a); for (int i = 0; i < m; ++i) CHECK(a[i].z <= r + 1e-3f); }
    if (failures) return 1;
    std::puts("p2_tank_stream_test: ok");
    return 0;
}
