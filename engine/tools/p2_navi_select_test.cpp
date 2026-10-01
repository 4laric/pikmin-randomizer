// Engine-free gate for the co-op captain selection the P2 enemy modules use
// (pc_port/pc_p2_navi_select.h, #888 WP3). Fake captains stand in for Navi.
#define P2_NAVI_SELECT_NO_ENGINE
#include "pc_p2_navi_select.h"

#include <cstdio>

namespace {

struct FakeNavi {
    int id;
    float x, z;
    bool alive;
    float range = 0.0f; // unused by the selector; lets the area test carry data
    int hits = 0;
};

using Roster = p2navisel::Roster<FakeNavi>;

int failures = 0;
#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);        \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

bool alive(FakeNavi* n) { return n->alive; }
void where(FakeNavi* n, float& x, float& z) { x = n->x; z = n->z; }

Roster rosterOf(FakeNavi* a, FakeNavi* b = nullptr)
{
    Roster r;
    r.add(a);
    r.add(b);
    return r;
}

FakeNavi* nearest(const Roster& r, float x, float z) { return p2navisel::nearest(r, x, z, alive, where); }

// The shape every converted area-effect site uses (flick/attack/press/blast):
// walk the roster and apply to each captain that passes the site's own test.
int areaHit(const Roster& r, float cx, float cz, float radius)
{
    int hit = 0;
    for (FakeNavi* n : r) {
        if (!n->alive) continue;
        const float dx = n->x - cx, dz = n->z - cz;
        if (dx * dx + dz * dz < radius * radius) {
            ++n->hits;
            ++hit;
        }
    }
    return hit;
}

} // namespace

int main()
{
    // Roster keeps manager (index) order; slot 0 is what getNavi() returns.
    {
        FakeNavi p1{1, 0, 0, true}, p2{2, 10, 0, true};
        const Roster r = rosterOf(&p1, &p2);
        CHECK(r.size() == 2);
        CHECK(r.first() == &p1);
        int order[2] = {0, 0}, i = 0;
        for (FakeNavi* n : r) order[i++] = n->id;
        CHECK(order[0] == 1 && order[1] == 2);
        Roster withNull;
        withNull.add(nullptr);
        CHECK(withNull.empty() && withNull.first() == nullptr);
    }

    // Two captains: the nearer SECOND captain is selected.
    {
        FakeNavi p1{1, 100, 0, true}, p2{2, 5, 5, true};
        const Roster r = rosterOf(&p1, &p2);
        CHECK(nearest(r, 0, 0) == &p2);
        CHECK(p2navisel::nearestIndex(r, 0.0f, 0.0f, alive, where) == 1);
        // ...and captain 1 when it is the nearer one.
        CHECK(nearest(r, 90, 0) == &p1);
        // Ties keep the lower index (strict '<', source getNearestNavi).
        FakeNavi t1{1, 3, 0, true}, t2{2, -3, 0, true};
        CHECK(nearest(rosterOf(&t1, &t2), 0, 0) == &t1);
    }

    // A dead second captain is ignored even when it is nearer.
    {
        FakeNavi p1{1, 100, 0, true}, p2{2, 1, 0, false};
        const Roster r = rosterOf(&p1, &p2);
        CHECK(nearest(r, 0, 0) == &p1);
        CHECK(p2navisel::nearestIndex(r, 0.0f, 0.0f, alive, where) == 0);
        // All dead: fall back to captain 1 (NaviMgr::getNearestNavi contract),
        // so a caller's own alive check rejects it exactly as with getNavi().
        p1.alive = false;
        CHECK(nearest(r, 0, 0) == &p1);
        CHECK(p2navisel::nearestIndex(r, 0.0f, 0.0f, alive, where) == -1);
    }

    // Single captain: every selector returns it, alive or not (unchanged).
    {
        FakeNavi p1{1, 500, 500, true};
        const Roster r = rosterOf(&p1);
        CHECK(r.size() == 1);
        CHECK(nearest(r, 0, 0) == &p1);
        CHECK(p2navisel::sourceActive(r, true, (FakeNavi*)nullptr, 0.0f, 0.0f, alive, where) == &p1);
        CHECK(p2navisel::sourceActive(r, false, (FakeNavi*)nullptr, 0.0f, 0.0f, alive, where) == &p1);
        p1.alive = false;
        CHECK(nearest(r, 0, 0) == &p1);
        CHECK(p2navisel::sourceActive(r, true, (FakeNavi*)nullptr, 0.0f, 0.0f, alive, where) == &p1);
        // Area effect with one captain: identical to the old single test.
        p1.alive = true;
        CHECK(areaHit(r, 500, 500, 10) == 1 && p1.hits == 1);
        CHECK(areaHit(r, 0, 0, 10) == 0 && p1.hits == 1);
        const Roster none;
        CHECK(nearest(none, 0, 0) == nullptr);
        CHECK(areaHit(none, 0, 0, 10) == 0);
    }

    // Area effects hit BOTH captains in range; out-of-range and dead are skipped.
    {
        FakeNavi p1{1, 2, 0, true}, p2{2, -3, 1, true};
        const Roster r = rosterOf(&p1, &p2);
        CHECK(areaHit(r, 0, 0, 10) == 2);
        CHECK(p1.hits == 1 && p2.hits == 1);
        p2.x = 50;
        CHECK(areaHit(r, 0, 0, 10) == 1 && p1.hits == 2 && p2.hits == 1);
        p2.x = 1;
        p2.alive = false;
        CHECK(areaHit(r, 0, 0, 10) == 1 && p1.hits == 3 && p2.hits == 1);
        // Second captain alone in range is still hit.
        p2.alive = true;
        p1.x = 50;
        CHECK(areaHit(r, 0, 0, 10) == 1 && p1.hits == 3 && p2.hits == 2);
    }

    // Source getActiveNavi replacement (umiMushi.cpp:849-853).
    {
        FakeNavi p1{1, 100, 0, true}, p2{2, 5, 0, true};
        const Roster r = rosterOf(&p1, &p2);
        // Two-player: the nearest alive captain.
        CHECK(p2navisel::sourceActive(r, true, &p1, 0.0f, 0.0f, alive, where) == &p2);
        p2.alive = false;
        CHECK(p2navisel::sourceActive(r, true, &p1, 0.0f, 0.0f, alive, where) == &p1);
        p2.alive = true;
        // One player, two captains (lane-12 swap): the controlled captain.
        CHECK(p2navisel::sourceActive(r, false, &p1, 0.0f, 0.0f, alive, where) == &p1);
        CHECK(p2navisel::sourceActive(r, false, &p2, 99.0f, 0.0f, alive, where) == &p2);
        CHECK(p2navisel::sourceActive(r, false, (FakeNavi*)nullptr, 0.0f, 0.0f, alive, where) == &p1);
    }

    // First-match loops (Demon::getAttackableTarget) keep index order.
    {
        FakeNavi p1{1, 0, 0, false}, p2{2, 0, 0, true};
        const Roster r = rosterOf(&p1, &p2);
        CHECK(p2navisel::firstIndex(r, alive) == 1);
        p1.alive = true;
        CHECK(p2navisel::firstIndex(r, alive) == 0);
        p1.alive = p2.alive = false;
        CHECK(p2navisel::firstIndex(r, alive) == -1);
    }

    // Capacity is bounded and deterministic (no allocation).
    {
        FakeNavi n[p2navisel::kMaxNavis + 2];
        Roster r;
        for (int i = 0; i < p2navisel::kMaxNavis + 2; ++i) {
            n[i] = FakeNavi{i, float(i), 0, true};
            r.add(&n[i]);
        }
        CHECK(r.size() == p2navisel::kMaxNavis);
        CHECK(r.first() == &n[0]);
    }

    if (failures) {
        std::printf("p2_navi_select_test: %d FAILED\n", failures);
        return 1;
    }
    std::printf("p2_navi_select_test: all checks passed\n");
    return 0;
}
