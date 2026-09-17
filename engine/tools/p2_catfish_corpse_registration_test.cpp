#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <map>
#include <string>
#include <vector>

// Standalone contract test for the Catfish26 corpse->receipt registration
// (#652, named by #641). Engine-free model of the exact policy added to
// pc_p2_catfish.cpp: a per-actor corpse registry fed ONLY by the natural
// death edge (health<=0 beside the CATFISH_DEAD transition), guarded by
// generator != 0 and by prior registration, cleared on forget (per-actor)
// and reset (whole registry). The marker grammar asserted here is the exact
// string the module prints.

namespace {

struct FakeActor {
    int id;
};

struct Registry {
    std::map<FakeActor*, unsigned> corpses;
    std::vector<std::string> markers;

    // Mirrors the module death edge: fires only when health<=0 on a live
    // staged actor (generator != 0) that has no prior registration.
    void onDeathEdge(FakeActor* actor, float health, unsigned generator, bool alreadyDead)
    {
        if (alreadyDead) return;
        if (!(health <= 0.0f)) return;
        if (generator == 0u) return;
        if (corpses.find(actor) != corpses.end()) return;
        corpses[actor] = generator;
        char line[160];
        std::snprintf(line, sizeof(line),
                      "P2_CATFISH_CORPSE_READY generator=%u source_id=26 receipt=corpse:catfish:%u",
                      generator, generator);
        markers.push_back(line);
    }

    void forget(FakeActor* actor) { corpses.erase(actor); }
    void reset() { corpses.clear(); }
};

} // namespace

int main()
{
    // Exactly one registration per natural death: repeated death ticks stay dark.
    {
        Registry r;
        FakeActor a{1};
        r.onDeathEdge(&a, 0.0f, 340001u, false);
        r.onDeathEdge(&a, 0.0f, 340001u, true);
        r.onDeathEdge(&a, 0.0f, 340001u, true);
        assert(r.corpses.size() == 1);
        assert(r.markers.size() == 1);
        assert(r.markers[0] == "P2_CATFISH_CORPSE_READY generator=340001 source_id=26 receipt=corpse:catfish:340001");
        std::puts("PASS exactly-once");
    }
    // Negative: no marker while alive, and none for a generator-less actor.
    {
        Registry r;
        FakeActor a{2}, b{3};
        r.onDeathEdge(&a, 1500.0f, 340002u, false);
        r.onDeathEdge(&b, 0.0f, 0u, false);
        assert(r.corpses.empty());
        assert(r.markers.empty());
        std::puts("PASS negative-dark");
    }
    // Forget clears the entry: a rebound actor registers fresh exactly once.
    {
        Registry r;
        FakeActor a{4};
        r.onDeathEdge(&a, 0.0f, 340003u, false);
        assert(r.corpses.size() == 1);
        r.forget(&a);
        assert(r.corpses.empty());
        r.onDeathEdge(&a, 0.0f, 340003u, false);
        assert(r.corpses.size() == 1);
        assert(r.markers.size() == 2);
        std::puts("PASS forget-rebind");
    }
    // Reset clears everything: no stale report survives a stage boundary.
    {
        Registry r;
        FakeActor a{5}, b{6};
        r.onDeathEdge(&a, 0.0f, 340004u, false);
        r.onDeathEdge(&b, 0.0f, 340005u, false);
        assert(r.corpses.size() == 2);
        r.reset();
        assert(r.corpses.empty());
        assert(r.markers.size() == 2);
        std::puts("PASS reset-clears");
    }
    // Address reuse cannot double-report: a stale entry blocks a second emit
    // until forget/reset runs (mirrors the module corpses-set guard).
    {
        Registry r;
        FakeActor a{7};
        r.onDeathEdge(&a, 0.0f, 340006u, false);
        r.onDeathEdge(&a, 0.0f, 340007u, false);
        assert(r.corpses.size() == 1);
        assert(r.corpses[&a] == 340006u);
        assert(r.markers.size() == 1);
        std::puts("PASS no-double-report");
    }
    std::puts("ALL_FIXTURE_PASS");
    return 0;
}
