// Engine-free fixtures for pc_p2_demon_anchor.h (#215 latch fix): the retail
// Demon collision tree the anchor wears, the body offset measured from the
// rest mesh, the CF_IsFlying mirror and the Lock-On peak pin.
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_demon_anchor_test.cpp -o p2_demon_anchor_test.exe
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "pc_p2_demon_anchor.h"

using namespace p2demonanchor;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_demon_anchor_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b, float eps = 0.01f) { return std::fabs(a - b) <= eps; }

int main()
{
    // --- retail tree: enemy/data/Demon enemycoll.txt ---
    {
        const CollSphere* s = spheres();
        require(kSphereCount == 3, "three retail spheres");
        require(s[0].parent == -1 && s[1].parent == 0 && s[2].parent == 0, "two children under the bounding sphere");
        require(near(s[0].radius, 30.0f) && std::strcmp(s[0].code, "____") == 0, "root is the radius-30 '____' bounding sphere");
        require(std::strcmp(s[1].code, "st__") == 0 && std::strcmp(s[2].code, "st__") == 0, "children are 'st__' stickable");
        require(near(s[1].radius, 13.0f) && near(s[1].offset.x, -6.0f) && near(s[1].offset.y, 7.0f), "st_1 = 13 @ (-6,7,0)");
        require(near(s[2].radius, 12.5f) && near(s[2].offset.y, 4.0f), "st_2 = 12.5 @ (0,4,0)");
        require(std::strcmp(s[0].id, s[1].id) != 0 && std::strcmp(s[1].id, s[2].id) != 0, "part ids are unique for getSphere");
    }

    // --- body offset from the rest mesh, fallback otherwise ---
    {
        std::vector<Vec3> cloud = {{-24.0f, -17.0f, -9.0f}, {24.0f, 49.0f, 17.0f}, {0.0f, 16.0f, 4.0f}};
        Vec3 body = defaultBodyOffset();
        require(near(body.y, 16.0f) && near(body.z, 3.0f), "fallback body offset is the measured demon_wait1_0000 centroid");
        require(bodyOffsetFromMesh(cloud.size(), [&](std::size_t i) { return cloud[i]; }, body), "centroid of a finite cloud");
        require(near(body.x, 0.0f) && near(body.y, 16.0f) && near(body.z, 4.0f), "centroid value");
        Vec3 untouched{1.0f, 2.0f, 3.0f};
        require(!bodyOffsetFromMesh(0, [&](std::size_t i) { return cloud[i]; }, untouched), "empty cloud keeps fallback");
        require(near(untouched.y, 2.0f), "empty cloud leaves the output untouched");
        std::vector<Vec3> bad = {{0.0f, std::nanf(""), 0.0f}};
        require(!bodyOffsetFromMesh(bad.size(), [&](std::size_t i) { return bad[i]; }, untouched), "non-finite cloud keeps fallback");
    }

    // --- sphere centres follow the host root and yaw; body rides above the root ---
    {
        const Vec3 root{100.0f, 85.0f, -40.0f};
        const Vec3 body = defaultBodyOffset();
        const Vec3 c0 = sphereCentre(0, root, 0.0f, body);
        require(near(c0.x, 100.0f) && near(c0.y, 101.0f) && near(c0.z, -37.0f), "root sphere at root + body offset (yaw 0)");
        const Vec3 c1 = sphereCentre(1, root, 0.0f, body);
        require(near(c1.x, 94.0f) && near(c1.y, 108.0f), "st_1 offset applied (yaw 0)");
        // yaw pi/2: local +x -> world -z, local +z -> world +x (P1 facing = (sin, cos)).
        const Vec3 y1 = sphereCentre(1, root, float(M_PI) / 2.0f, body);
        require(near(y1.x, 100.0f + 3.0f, 0.05f) && near(y1.z, -40.0f + 6.0f, 0.05f) && near(y1.y, 108.0f),
                "yaw rotates the local offsets about the root");
        require(sphereCentre(-1, root, 0.0f, body).y == c0.y && sphereCentre(9, root, 0.0f, body).y == sphereCentre(2, root, 0.0f, body).y,
                "index clamps");
        // Hovering at fp01 = 85 the stickable bottom sits at 85 + 16 + 4 - 12.5 = 92.5:
        // a max-hold P1 throw (peak 100) or a Yellow reaches it; a locked
        // throw pinned on the target XZ (32..72 on the way down) never did.
        require(near(stickableBottom(body), 7.5f), "stickable bottom = 7.5 above the root");
        require(root.y + stickableBottom(body) > 72.0f && root.y + stickableBottom(body) < 100.0f,
                "hovering stick spheres sit between the pinned-cursor pass height and the peak");
    }

    // --- CF_IsFlying mirror ---
    {
        require(anchorFlying(true, false), "untargetable hover flies");
        require(!anchorFlying(true, true), "Fall/Damage/Dead never fly even while flagged");
        require(!anchorFlying(false, false), "targetable never flies");
    }

    // --- Lock-On pin: peak over a flying target, plain pin otherwise ---
    {
        require(near(lockPinScale(false), 1.0f), "grounded target keeps the plain pin");
        require(near(lockPinScale(true), 2.0f), "flying target pins the cursor at twice the offset");
        // P1 throwPiki: hSpeed = dist / flightTime, vertical peak at flightTime / 2:
        // the peak's XZ is half the cursor distance, i.e. the target itself.
        const float flightTime = 1.0f, dist = 60.0f * lockPinScale(true);
        const float hSpeed = dist / flightTime;
        require(near(hSpeed * (flightTime * 0.5f), 60.0f), "peak lands on the target XZ");
    }

    std::printf("p2_demon_anchor_test: %d checks passed\n", gChecks);
    return 0;
}
