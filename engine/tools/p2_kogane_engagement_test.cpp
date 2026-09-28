// rd-p2-kogane-engagement (#835): engine-free engagement contract test.
//
// Kogane is a finite flip/drop/escape species, not a kill/corpse enemy. This
// binary pins the production call-path facts a normal player-directed contact
// depends on and the family-local finite contract, without booting the engine:
//
//   * a FreeMode squad acquires a grounded organic beetle (piki.cpp:951);
//   * ActAttack holds a stuck/grounded target (aiAttack.cpp:297);
//   * direct collision in FormationMode switches to AttackMode (piki.cpp:2079);
//   * the InteractAttack receiver flips a registered beetle with no attack
//     damage and falls through for unregistered actors (tekiinteraction.cpp:46);
//   * contact flips only when settled; recovery/drop windows swallow; the
//     third flip escapes with no corpse and no further receipt
//     (pc_p2_kogane.cpp:199-212,398-405; setup restore :296-309);
//   * the Onion receipt key is exactly-once per (seed, enemy:id, generator,
//     flip1..3); a fourth contact has no encounter key (pc_p2_kogane.cpp:174);
//   * restart keeps the maximum flip count per generator, so drops cannot be
//     farmed across reset+setup cycles (pc_p2_kogane.cpp:96-100,215,296-299).
//
// The mirrored predicates live in the owned header
// pc_port/pc_p2_kogane_policy.h (namespace p2kogane::engagement) and cite the
// production lines they pin. Exit 0 only if every check passes; any failure
// prints FAIL and exits 1. `--guard-negative-test` exercises the exact #632
// interruption call and exits 86 with P2_FIXTURE_CAPTAIN_DOWN and no PASS.
#include "pc_p2_kogane_policy.h"

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

#include <cmath>
#include <cstring>

namespace {

using p2kogane::engagement::AcquisitionFacts;
using p2kogane::engagement::CollisionFacts;
using p2kogane::engagement::ContactOutcome;
using p2kogane::engagement::FlipState;

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

bool near(float got, float want) { return std::fabs(got - want) < 1.0e-4f; }

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
            std::printf("FAIL KOGANE_ENGAGEMENT_GUARD row=%d got=%d want=%d\n",
                        int(i), int(down), int(rows[i].expectDown));
            return 1;
        }
    }
    std::printf("P2_KOGANE_ENGAGEMENT_GUARD_SELFTEST rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    using namespace p2kogane::engagement;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--guard-self-test")) return guardSelfTest();
        if (!std::strcmp(argv[i], "--guard-negative-test")) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL KOGANE_ENGAGEMENT_GUARD negative test did not trip\n");
            return 1;
        }
    }

    // Source identity: only 9/10/11 are beetles (policy::karada covers the same set).
    CHECK(isSourceId(9), "source-id-kogane");
    CHECK(isSourceId(10), "source-id-wealthy");
    CHECK(isSourceId(11), "source-id-fart");
    CHECK(!isSourceId(8), "source-id-rejects-8");
    CHECK(!isSourceId(12), "source-id-rejects-12");
    CHECK(!isSourceId(-1), "source-id-rejects-unbound");

    // Frame-timed drop contract: source damage clip is 50 frames, the
    // createItem event fires at frame 7, the host runs at 30 Hz.
    CHECK(kMaxFlips == 3, "finite-cap-3");
    CHECK(kDropFrame == 7, "drop-frame-7");
    CHECK(kDamageClipFrames == 50, "damage-clip-50");
    CHECK(near(kDropDelaySec, 7.0f / 50.0f * (50.0f / 30.0f)), "drop-delay-sec");
    CHECK(near(kRecoverSec, 50.0f / 30.0f), "recover-sec");

    // Free-squad graspSituation truth table (piki.cpp:951). The registered
    // beetle is a grounded organic Chappy proxy, so the ordinary row holds:
    // normal contact needs no injection.
    CHECK(freeSquadAcquires(AcquisitionFacts{true, true, false, true, false}),
          "acquire-ordinary-beetle");
    CHECK(!freeSquadAcquires(AcquisitionFacts{true, true, true, true, false}),
          "skip-flying");
    CHECK(!freeSquadAcquires(AcquisitionFacts{true, true, false, false, false}),
          "skip-inorganic");
    CHECK(!freeSquadAcquires(AcquisitionFacts{false, true, false, true, false}),
          "skip-invisible");
    CHECK(!freeSquadAcquires(AcquisitionFacts{true, false, false, true, false}),
          "skip-dead");
    CHECK(!freeSquadAcquires(AcquisitionFacts{true, true, false, true, true}),
          "skip-target-stuck");

    // ActAttack airborne hold truth table (aiAttack.cpp:297).
    CHECK(attackHolds(true, true, true), "attack-holds-stuck-airborne");
    CHECK(!attackHolds(false, true, true), "attack-abandons-airborne");
    CHECK(attackHolds(false, false, true), "attack-holds-grounded");
    CHECK(!attackHolds(false, false, false), "attack-abandons-invisible");

    // Direct-collision attack branch truth table (piki.cpp:2079).
    const CollisionFacts thrown{true, true, true, true, false};
    CHECK(collisionAttacks(thrown), "collision-attack-thrown-contact");
    CHECK(!collisionAttacks(CollisionFacts{false, true, true, true, false}),
          "collision-no-attack-when-cstick-off");
    CHECK(!collisionAttacks(CollisionFacts{true, false, true, true, false}),
          "collision-no-attack-when-not-teki");
    CHECK(!collisionAttacks(CollisionFacts{true, true, false, true, false}),
          "collision-no-attack-when-inorganic");
    CHECK(!collisionAttacks(CollisionFacts{true, true, true, false, false}),
          "collision-no-attack-when-not-formation");
    CHECK(!collisionAttacks(CollisionFacts{true, true, true, true, true}),
          "collision-no-attack-when-pressed");

    // Ordinary binding: first controller-driven contact on a settled
    // registered beetle flips (tekiinteraction.cpp:46 -> doFlip).
    FlipState ordinary;
    ordinary.registered = true;
    CHECK(contactOutcome(ordinary) == ContactOutcome::Flip, "ordinary-first-contact-flips");

    // Dynamic binding: any generator/source pair behaves identically once
    // registered; a settled second flip also flips (recovery gating is time,
    // not identity, based).
    FlipState dynamic;
    dynamic.registered = true;
    dynamic.flips = 1;
    CHECK(contactOutcome(dynamic) == ContactOutcome::Flip, "dynamic-second-contact-flips");
    FlipState wealthy;
    wealthy.registered = true;
    wealthy.flips = 2;
    CHECK(contactOutcome(wealthy) == ContactOutcome::Flip, "dynamic-third-contact-flips");

    // Recovery gating: contacts inside the damage-clip window or while a drop
    // is pending are swallowed, never double-counted (doFlip:199).
    FlipState recovering;
    recovering.registered = true;
    recovering.flips = 1;
    recovering.recovering = true;
    CHECK(contactOutcome(recovering) == ContactOutcome::SwallowedRecovering,
          "recovering-contact-swallowed");
    FlipState pending;
    pending.registered = true;
    pending.dropPending = true;
    CHECK(contactOutcome(pending) == ContactOutcome::SwallowedDropPending,
          "drop-pending-contact-swallowed");

    // Finite cap: the third flip's drop escapes with no corpse and no further
    // receipt; restored-at-cap beetles reconstruct escape on setup.
    FlipState capped;
    capped.registered = true;
    capped.flips = 3;
    CHECK(contactOutcome(capped) == ContactOutcome::TerminalEscaped,
          "fourth-contact-terminal");
    FlipState escaped;
    escaped.registered = true;
    escaped.flips = 3;
    escaped.escaped = true;
    CHECK(contactOutcome(escaped) == ContactOutcome::TerminalEscaped,
          "escaped-contact-terminal");

    // Unbound actor (never registered, setup-rejected identity, or torn down
    // via forget/reset): falls through to the host damage path, never flips.
    FlipState unbound;
    CHECK(contactOutcome(unbound) == ContactOutcome::HostDamagePath,
          "unbound-falls-through");
    FlipState tornDown;
    tornDown.flips = 2; // stale press count without registration grants nothing
    CHECK(contactOutcome(tornDown) == ContactOutcome::HostDamagePath,
          "teardown-falls-through");

    // Dead actor: swallowed, no flip and no damage accounting change.
    FlipState dead;
    dead.registered = true;
    dead.dead = true;
    CHECK(contactOutcome(dead) == ContactOutcome::DeadNoEffect, "dead-no-effect");

    // Exactly-once receipt key: one distinct encounter per flip, bounded to
    // the cap; there is no fourth encounter to grant.
    CHECK(receiptIdentity(9) == "enemy:9", "receipt-identity");
    CHECK(receiptEncounter(1) == "flip1", "receipt-encounter-1");
    CHECK(receiptEncounter(2) == "flip2", "receipt-encounter-2");
    CHECK(receiptEncounter(3) == "flip3", "receipt-encounter-3");
    CHECK(receiptEncounterValid(1) && receiptEncounterValid(2) && receiptEncounterValid(3),
          "receipt-encounters-valid");
    CHECK(!receiptEncounterValid(0) && !receiptEncounterValid(4), "receipt-no-fourth-encounter");

    // Restart durability: reset+setup keeps the maximum flip count per
    // generator, so a second process can never farm granted drops.
    CHECK(mergeRestoredFlips(0, 0) == 0, "restart-merge-empty");
    CHECK(mergeRestoredFlips(2, 1) == 2, "restart-merge-keeps-live-max");
    CHECK(mergeRestoredFlips(1, 3) == 3, "restart-merge-adopts-disk-max");
    CHECK(mergeRestoredFlips(3, 3) == 3, "restart-merge-cap-stable");

    // Guard source is adopted and tested alongside the audit.
    if (guardSelfTest() != 0) ++failures;

    if (failures == 0) {
        std::puts("PASS P2_KOGANE_ENGAGEMENT flips3 escape1 receipt_once receiver=flip");
    } else {
        std::printf("P2_KOGANE_ENGAGEMENT pass=0 failures=%d\n", failures);
    }
    std::fflush(stdout);
    return failures == 0 ? 0 : 1;
}
