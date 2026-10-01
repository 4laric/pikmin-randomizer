// Poisoned-Pikmin purple cloud policy (engine-free): pc_p2_gas_cloud_policy.h.
#include "pc_p2_gas_cloud_policy.h"

#include <cmath>
#include <cstdio>

using namespace p2gascloud;

namespace {
int gFail = 0;
#define CHECK(cond, name)                                                         \
    do {                                                                          \
        if (!(cond)) {                                                            \
            ++gFail;                                                              \
            std::printf("FAIL %s (%s:%d)\n", name, __FILE__, __LINE__);           \
        } else {                                                                  \
            std::printf("ok   %s\n", name);                                       \
        }                                                                         \
    } while (0)
} // namespace

int main() {
    p2attackfx::Point a[PUFFS], b[PUFFS];
    // The cloud sits around the head, not the feet or the ground (mutant: puffs at piki.y).
    {
        const int n = layout(100.0f, 50.0f, -30.0f, 0, 7, a);
        CHECK(n == PUFFS, "each emission puffs PUFFS times");
        bool head = true, near = true;
        for (int i = 0; i < n; ++i) {
            head &= a[i].y > 50.0f + HEAD_HEIGHT - PUFF_RADIUS && a[i].y < 50.0f + HEAD_HEIGHT + PUFF_RADIUS;
            const float dx = a[i].x - 100.0f, dz = a[i].z + 30.0f;
            near &= std::sqrt(dx * dx + dz * dz) <= PUFF_RADIUS + 1e-3f;
        }
        CHECK(head, "puffs are at head height");
        CHECK(near, "puffs stay within the scatter radius of the head");
    }
    // Deterministic per (tick, salt); two Pikmin do not puff in lockstep (mutant: identical clouds).
    {
        layout(0, 0, 0, 3, 9, a);
        layout(0, 0, 0, 3, 9, b);
        bool same = true;
        for (int i = 0; i < PUFFS; ++i) same &= a[i].x == b[i].x && a[i].y == b[i].y && a[i].z == b[i].z;
        CHECK(same, "same tick and Pikmin give the same puffs");
        layout(0, 0, 0, 3, 10, b);
        bool differs = false;
        for (int i = 0; i < PUFFS; ++i) differs |= a[i].x != b[i].x || a[i].z != b[i].z;
        CHECK(differs, "a different Pikmin puffs differently");
    }
    // Cadence and lifetime: a short tail so a missed stop cannot leave an effect behind.
    {
        CHECK(emitsOn(0) && !emitsOn(1) && !emitsOn(2) && emitsOn(3), "puffs every third update, starting at once");
        CHECK(PUFF_LIFE > 0 && PUFF_LIFE <= 30, "puffs are short-lived (under a second)");
        CHECK(EFFECT == p2attackfx::EFF_Kinoko_AttackCloud, "the cloud is the P1 Puffstool poison cloud");
    }
    // Lifecycle: one cloud per gas panic, stopped once on cure or death, nothing outstanding.
    {
        Cloud c;
        CHECK(!c.end(), "stopping an idle cloud is a no-op");
        CHECK(c.begin(), "gas panic starts a cloud");
        CHECK(!c.begin(), "a second begin while running does not restart it (gasInvincible blocks re-entry)");
        CHECK(c.outstanding() == 1, "a running cloud is outstanding");
        CHECK(c.end(), "cure or death stops it");
        CHECK(c.outstanding() == 0, "nothing outstanding after the stop");
        CHECK(!c.end(), "a second stop (death after cleanup) is a no-op");
        CHECK(c.begin() && c.started == 2, "a later poisoning starts a fresh cloud");
    }
    if (gFail) { std::printf("%d failure(s)\n", gFail); return 1; }
    std::puts("p2_gas_cloud_test: ok");
    return 0;
}
