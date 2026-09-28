// rd-p2-kurage-natural (#832): engine-free reachability audit for the
// private-adapter Kurage (source id 57) natural-kill gate.
//
// No engine is booted.  This binary pins the P1 target-acquisition predicates a
// natural (unforced) kill depends on and runs the canonical captain guard
// self-test / negative test, so the lane's blocked finding is a tested claim:
//
//   * a FreeMode P1 squad never acquires an airborne Teki
//     (src/plugPikiKando/piki.cpp:951);
//   * ActAttack abandons an airborne target unless the Pikmin is stuck
//     (src/plugPikiKando/aiAttack.cpp:297);
//   * the InteractAttack receiver accepts source 57 (no Kurage rejection in
//     src/plugPikiNakata/tekiinteraction.cpp:41);
//   * therefore the private-adapter natural chain stalls at target
//     acquisition, because the production binding only grounds the actor with
//     the injected `groundAndSeal` concession.
//
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
// `--guard-negative-test` exercises the exact #632 interruption call and exits
// 86 with P2_FIXTURE_CAPTAIN_DOWN and no PASS.
#include "pc_p2_kurage_natural.h"

#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Vendored tested equivalent of scripts/p2_fixture_captain_guard.h
// (canonical sha256 d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
// Never changes captain health or game state.
#include <cmath>
#include <cstdio>
#include <cstdlib>
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp)
{
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick)
{
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86);
}
#endif

#include <cstring>

namespace {

using p2kurage_natural::AcquisitionFacts;
using p2kurage_natural::Stall;

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

int guardSelfTest()
{
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.5f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {false, true, 100.0f, true},
        {true, false, 100.0f, true},
        {true, true, 0.0f, true},
    };
    for (size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        const bool down = p2_fixture_captain_down(rows[i].orima, rows[i].dead, rows[i].hp);
        if (down != rows[i].expectDown) {
            std::printf("FAIL KURAGE_NATURAL_GUARD row=%d got=%d want=%d\n",
                        int(i), int(down), int(rows[i].expectDown));
            return 1;
        }
    }
    std::printf("P2_KURAGE_NATURAL_GUARD_SELFTEST rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL KURAGE_NATURAL_GUARD negative test did not trip\n");
            return 1;
        }
    }

    // FreeMode graspSituation truth table (piki.cpp:951).
    CHECK(p2kurage_natural::free_squad_acquires(AcquisitionFacts{true, true, true, false, false}),
          "acquire-ground-organic");
    CHECK(!p2kurage_natural::free_squad_acquires(AcquisitionFacts{true, true, true, false, true}),
          "skip-flying");
    CHECK(!p2kurage_natural::free_squad_acquires(AcquisitionFacts{false, true, true, false, false}),
          "skip-dead");
    CHECK(!p2kurage_natural::free_squad_acquires(AcquisitionFacts{true, false, true, false, false}),
          "skip-invisible");
    CHECK(!p2kurage_natural::free_squad_acquires(AcquisitionFacts{true, true, true, true, false}),
          "skip-stuck");

    // ActAttack airborne re-target truth table (aiAttack.cpp:297).
    CHECK(!p2kurage_natural::attack_holds(false, true, true), "attack-abandons-airborne");
    CHECK(p2kurage_natural::attack_holds(true, true, true), "attack-holds-stuck-airborne");
    CHECK(p2kurage_natural::attack_holds(false, false, true), "attack-holds-grounded");
    CHECK(!p2kurage_natural::attack_holds(false, false, false), "attack-abandons-invisible");

    // InteractAttack receiver: source 57 has no family-local rejection.
    CHECK(p2kurage_natural::damage_receiver_accepts(57), "receiver-accepts-57");
    CHECK(!p2kurage_natural::damage_receiver_accepts(28), "receiver-rejects-elecbug");
    CHECK(!p2kurage_natural::damage_receiver_accepts(9), "receiver-rejects-kogane");

    // The private-adapter verdict: airborne unless injected-grounded.
    const p2kurage_natural::Audit adapter =
        p2kurage_natural::audit_private_adapter(true, true);
    CHECK(adapter.damage_receiver_open, "adapter-receiver-open");
    CHECK(!adapter.free_squad_acquires, "adapter-free-squad-cannot-acquire");
    CHECK(adapter.stall == Stall::NoEngagementFreeSquadSkipsFlying, "adapter-stall-engagement");
    CHECK(std::strstr(p2kurage_natural::stall_callsite(adapter.stall), "piki.cpp:951") != nullptr,
          "adapter-stall-callsite");

    // Counterfactual: a grounded adapter is acquirable and does not stall.
    const p2kurage_natural::Audit grounded =
        p2kurage_natural::audit_private_adapter(false, false);
    CHECK(grounded.free_squad_acquires, "grounded-adapter-acquirable");
    CHECK(grounded.stall == Stall::None, "grounded-adapter-no-stall");

    // Natural marker contract used by the future run log checker.
    CHECK(std::strcmp(p2kurage_natural::kNaturalCorpseMarker, "P2_KURAGE57_CORPSE pellet=1") == 0,
          "marker-corpse");
    CHECK(std::strcmp(p2kurage_natural::kNaturalCarryMarker, "P2_KURAGE57_CARRY") == 0,
          "marker-carry");
    CHECK(std::strcmp(p2kurage_natural::kNaturalDeliveredMarker, "P2_KURAGE57_DELIVERED_TO_GOAL") == 0,
          "marker-delivered");

    // Guard source is adopted and tested alongside the audit.
    if (guardSelfTest() != 0) ++failures;

    if (failures == 0) {
        std::printf("PASS P2_KURAGE_NATURAL_AUDIT source=57 receiver=open free_squad_acquires=0 "
                    "stall=%s callsite=%s\n",
                    p2kurage_natural::stall_token(adapter.stall),
                    p2kurage_natural::stall_callsite(adapter.stall));
    } else {
        std::printf("P2_KURAGE_NATURAL_AUDIT pass=0 failures=%d\n", failures);
    }
    std::fflush(stdout);
    return failures == 0 ? 0 : 1;
}
