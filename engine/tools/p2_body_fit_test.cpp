// Unit test for the P2 body-collision fit (pc_p2_body_fit.h).
#include "pc_p2_body_fit.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

using p2bodyfit::V3;

static std::vector<V3> shell(float cx, float cy, float cz, float rx, float ry, float rz)
{
    std::vector<V3> v;
    const float pi = 3.14159265f;
    for (int i = 0; i <= 24; ++i) {
        const float a = pi * float(i) / 24.0f;
        for (int j = 0; j < 48; ++j) {
            const float b = 2.0f * pi * float(j) / 48.0f;
            v.push_back(V3{cx + rx * std::sin(a) * std::cos(b), cy + ry * std::cos(a), cz + rz * std::sin(a) * std::sin(b)});
        }
    }
    return v;
}

int main()
{
    // A compact body: one stickable sphere on the surface.
    {
        const auto v = shell(0, 60, 0, 50, 50, 50);
        p2bodyfit::Table t;
        assert(p2bodyfit::fit(v.size(), [&](std::size_t i) { return v[i]; }, t));
        assert(t.count == 2);
        assert(std::fabs(t.spheres[1].radius - 50.0f) < 1.0f);
        assert(std::fabs(t.spheres[1].offset.y - 60.0f) < 1.0f);
        assert(t.spheres[1].code[0] == 's' && t.spheres[0].code[0] == '_');
        assert(t.maxGap < 1.0f);
        // A Pikmin standing on the top of the body is 0 from its surface.
        const p2flyer::Vec3 root{100.0f, 0.0f, -40.0f};
        const p2flyer::Vec3 top{100.0f, 110.0f, -40.0f};
        assert(std::fabs(p2bodyfit::surfaceGap(t, 1, root, 0.7f, top)) < 1.5f);
        // The root bounding sphere encloses the body sphere.
        assert(t.spheres[0].radius >= t.spheres[1].radius - 0.01f);
    }
    // A long body gets a chain along its length, every sphere inside the body
    // extents, and the drawn surface stays within a bounded gap of the spheres.
    {
        const auto v = shell(0, 40, 0, 40, 40, 160);
        p2bodyfit::Table t;
        assert(p2bodyfit::fit(v.size(), [&](std::size_t i) { return v[i]; }, t));
        assert(t.count >= 4);
        for (int i = 1; i < t.count; ++i) {
            assert(std::fabs(t.spheres[i].offset.x) < 1.0f);
            assert(std::fabs(t.spheres[i].offset.z) <= 160.0f);
            assert(t.spheres[i].radius > 5.0f && t.spheres[i].radius <= 120.0f);
        }
        assert(t.meanGap < 25.0f);
    }
    // Yaw rotates the body with the actor: the offset follows +z forward.
    {
        const auto v = shell(0, 40, 0, 30, 30, 120);
        p2bodyfit::Table t;
        assert(p2bodyfit::fit(v.size(), [&](std::size_t i) { return v[i]; }, t));
        const p2flyer::Vec3 root{0, 0, 0};
        float bestZ = -1.0e9f;
        int front = 1;
        for (int i = 1; i < t.count; ++i)
            if (t.spheres[i].offset.z > bestZ) { bestZ = t.spheres[i].offset.z; front = i; }
        const float yaw = 3.14159265f * 0.5f;  // +z forward -> +x
        const p2flyer::Vec3 c = p2flyer::sphereCentre(t.spheres, t.count, front, root, yaw, p2flyer::Vec3{});
        assert(c.x > 10.0f && std::fabs(c.z) < 1.0f);
    }
    // Rejections: non-finite, too few, degenerate.
    {
        std::vector<V3> bad(10, V3{1, 2, 3});
        p2bodyfit::Table t;
        assert(!p2bodyfit::fit(bad.size(), [&](std::size_t i) { return bad[i]; }, t));
        bad[3].y = NAN;
        assert(!p2bodyfit::fit(bad.size(), [&](std::size_t i) { return bad[i]; }, t));
        bad[3].y = 1.0e9f;
        assert(!p2bodyfit::fit(bad.size(), [&](std::size_t i) { return bad[i]; }, t));
        assert(!p2bodyfit::fit(2, [&](std::size_t i) { return bad[i]; }, t));
        assert(t.count == 0);
    }
    // Determinism.
    {
        const auto v = shell(5, 30, -8, 60, 25, 45);
        p2bodyfit::Table a, b;
        assert(p2bodyfit::fit(v.size(), [&](std::size_t i) { return v[i]; }, a));
        assert(p2bodyfit::fit(v.size(), [&](std::size_t i) { return v[i]; }, b));
        assert(a.count == b.count);
        for (int i = 0; i < a.count; ++i)
            assert(a.spheres[i].radius == b.spheres[i].radius && a.spheres[i].offset.x == b.spheres[i].offset.x);
    }
    std::puts("p2_body_fit_test OK");
    return 0;
}
