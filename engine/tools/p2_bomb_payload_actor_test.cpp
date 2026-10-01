// Standalone engine-free test for the Bomb payload actor provider (#577).
//
// Compiles with -Ipc_port ONLY (no engine headers: the engine-free policy
// boundary is enforced by the build itself) and links the shared blast
// routing translation unit so routing/attribution run through the REAL
// p2_bombsarai_route_blast, never a reimplementation:
//
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port
//       tools/p2_bomb_payload_actor_test.cpp
//       pc_port/pc_p2_bomb_payload_actor.cpp
//       pc_port/pc_p2_bombsarai_blast.cpp
//       -o p2_bomb_payload_actor_test && ./p2_bomb_payload_actor_test
//
// A policy token or printed ATTACH alone cannot pass: every behavior below
// executes the provider lifecycle plus shared routing and asserts outcomes.
#include <cmath>
#include <cstdio>
#include <string>

#include "pc_p2_bomb_payload_actor.h"
#include "pc_p2_bombsarai_blast.h"

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const char* name)
{
    ++checks;
    if (!condition) {
        ++failures;
        std::printf("FAIL %s\n", name);
    }
}

bool carrierLiveTrue(void*, std::uint64_t token)
{
    return token != 0;
}

bool carrierLiveFalse(void*, std::uint64_t)
{
    return false;
}

P2BombSaraiVec3 joint(float x, float y, float z)
{
    P2BombSaraiVec3 v;
    v.x = x;
    v.y = y;
    v.z = z;
    return v;
}

P2BombPayloadConfig defaults()
{
    return P2BombPayloadConfig{};
}

} // namespace

int main()
{
    // 1. Birth, liveness, duplicate/zero/non-finite refusal, exhaustion.
    {
        P2BombPayloadPool pool(1);
        P2BombPayloadHandle bad = pool.birth(0, joint(0, 0, 0), defaults());
        check(!p2_bomb_payload_handle_valid(bad), "zero-carrier-refused");
        P2BombSaraiVec3 nan = joint(0, 0, 0);
        nan.x = std::nanf("");
        bad = pool.birth(7, nan, defaults());
        check(!p2_bomb_payload_handle_valid(bad), "nonfinite-joint-refused");
        P2BombPayloadConfig badConfig = defaults();
        badConfig.blastRadius = 0.0f;
        bad = pool.birth(7, joint(0, 0, 0), badConfig);
        check(!p2_bomb_payload_handle_valid(bad), "bad-config-refused");
        P2BombPayloadHandle h = pool.birth(7, joint(1, 2, 3), defaults());
        check(p2_bomb_payload_handle_valid(h), "birth-valid");
        check(pool.isLive(h), "birth-live");
        check(pool.phase(h) == P2BombPayloadPhase::Carried, "birth-carried");
        check(pool.carrierToken(h) == 7, "birth-carrier");
        check(pool.activeCount() == 1, "birth-active-count");
        P2BombPayloadHandle dup = pool.birth(7, joint(4, 5, 6), defaults());
        check(!p2_bomb_payload_handle_valid(dup), "duplicate-carrier-refused");
        P2BombPayloadHandle full = pool.birth(8, joint(4, 5, 6), defaults());
        check(!p2_bomb_payload_handle_valid(full), "exhaustion-refused");
    }

    // 2. Joint follow while carried; rejection otherwise.
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(11, joint(0, 10, 0), defaults());
        check(pool.followJoint(h, joint(5, 11, 5)), "follow-ok");
        P2BombSaraiVec3 at = pool.position(h);
        check(at.x == 5.0f && at.y == 11.0f && at.z == 5.0f, "follow-moved");
        P2BombSaraiVec3 nan = joint(0, 0, 0);
        nan.z = std::nanf("");
        check(!pool.followJoint(h, nan), "follow-nonfinite-rejected");
        at = pool.position(h);
        check(at.x == 5.0f, "follow-unchanged-after-reject");
        P2BombPayloadHandle invalid;
        check(!pool.followJoint(invalid, joint(0, 0, 0)), "follow-invalid-handle");
    }

    // 3. Stale handle after reset; recycled slot gets a new generation.
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(21, joint(0, 0, 0), defaults());
        pool.reset();
        check(!pool.isLive(h), "reset-kills-live");
        check(pool.phase(h) == P2BombPayloadPhase::Free, "reset-frees");
        check(!pool.detonate(h, P2BombPayloadTrigger::Contact, carrierLiveTrue, nullptr),
              "reset-detonate-suppressed");
        P2BombPayloadHandle h2 = pool.birth(21, joint(1, 1, 1), defaults());
        check(p2_bomb_payload_handle_valid(h2), "rebirth-valid");
        check(h2.generation != h.generation, "rebirth-new-generation");
        check(pool.isLive(h2) && !pool.isLive(h), "rebirth-liveness-split");
        check(!pool.followJoint(h, joint(9, 9, 9)), "stale-follow-rejected");
    }

    // 4. Payload lost: no blast, record released, second call refused.
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(31, joint(0, 5, 0), defaults());
        check(pool.onPayloadLost(h), "lost-ok");
        check(!pool.isLive(h), "lost-not-live");
        check(pool.phase(h) == P2BombPayloadPhase::Lost, "lost-phase");
        check(!pool.hasBlast(h), "lost-no-blast");
        check(!pool.onPayloadLost(h), "lost-twice-refused");
        check(!pool.detonate(h, P2BombPayloadTrigger::Contact, carrierLiveTrue, nullptr),
              "lost-detonate-suppressed");
        // The carrier token is free for a later birth (host re-arms).
        P2BombPayloadHandle h2 = pool.birth(31, joint(0, 5, 0), defaults());
        check(pool.isLive(h2), "rebirth-after-loss");
    }

    // 5. Carrier death detonates exactly once; duplicates suppressed.
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(41, joint(2, 3, 4), defaults());
        check(pool.onCarrierDeath(h, carrierLiveTrue, nullptr), "death-detonates");
        check(pool.hasBlast(h), "death-blast-recorded");
        check(!pool.isLive(h), "death-not-live");
        check(!pool.onCarrierDeath(h, carrierLiveTrue, nullptr), "death-twice-suppressed");
        check(!pool.detonate(h, P2BombPayloadTrigger::Death, carrierLiveTrue, nullptr),
              "death-then-manual-suppressed");
        check(pool.blastCount() == 1, "death-exactly-once");
    }

    // 6. Duplicate manual detonation: one blast, suppression counted.
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(51, joint(6, 7, 8), defaults());
        const int suppressedBefore = pool.suppressedCount();
        check(pool.detonate(h, P2BombPayloadTrigger::Press, carrierLiveTrue, nullptr),
              "first-detonate");
        check(!pool.detonate(h, P2BombPayloadTrigger::Press, carrierLiveTrue, nullptr),
              "second-suppressed");
        check(!pool.detonate(h, P2BombPayloadTrigger::Contact, carrierLiveTrue, nullptr),
              "third-suppressed");
        check(pool.blastCount() == 1, "manual-exactly-once");
        check(pool.suppressedCount() == suppressedBefore + 2, "suppressed-counted");
        check(pool.hasBlast(h), "blast-queryable");
        pool.clearBlast(h);
        check(!pool.hasBlast(h), "blast-cleared");
    }

    // 7. Missing carrier/joint: every op on an invalid handle is a no-op.
    {
        P2BombPayloadPool pool(1);
        P2BombPayloadHandle invalid;
        check(!pool.isLive(invalid), "invalid-not-live");
        check(pool.phase(invalid) == P2BombPayloadPhase::Free, "invalid-free");
        check(pool.carrierToken(invalid) == 0, "invalid-no-carrier");
        check(!pool.hasBlast(invalid), "invalid-no-blast");
        check(!pool.onPayloadLost(invalid), "invalid-lost");
        check(!pool.onCarrierDeath(invalid, carrierLiveTrue, nullptr), "invalid-death");
        pool.clearBlast(invalid);
        P2BombPayloadHandle forged{0, 999};
        check(!pool.isLive(forged), "forged-generation-rejected");
        check(!pool.detonate(forged, P2BombPayloadTrigger::Contact, carrierLiveTrue, nullptr),
              "forged-detonate-rejected");
    }

    // 8. Routing + attribution through the REAL shared blast router.
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(61, joint(0, 0, 0), defaults());
        check(pool.detonate(h, P2BombPayloadTrigger::Contact, carrierLiveTrue, nullptr),
              "route-detonate");
        const P2BombSaraiBlastEvent& blast = pool.lastBlast(h);
        check(blast.radius == 90.0f && blast.tekiDamage == 500.0f
                  && blast.naviPikiDamage == 10.0f && blast.halfHeight == 50.0f,
              "route-pinned-defaults");
        check(blast.hasCarrier && blast.carrierValid && blast.carrierToken == 61,
              "route-carrier-valid");
        P2BombSaraiReceiver receivers[3];
        receivers[0].id = 0;
        receivers[0].position = joint(10, 0, 0);
        receivers[0].kind = P2BombSaraiReceiverKind::Teki;
        receivers[1].id = 1;
        receivers[1].position = joint(-20, 0, 5);
        receivers[1].kind = P2BombSaraiReceiverKind::Piki;
        receivers[2].id = 2;
        receivers[2].position = joint(500, 0, 0);
        receivers[2].kind = P2BombSaraiReceiverKind::Teki;
        P2BombSaraiRoutedHit hits[3];
        const int routed = p2_bombsarai_route_blast(blast, receivers, 3, hits, 3);
        check(routed == 2, "route-two-in-volume");
        bool tekiHit = false, pikiHit = false;
        for (int i = 0; i < routed; ++i) {
            if (hits[i].receiverId == 0) {
                tekiHit = true;
                check(hits[i].damage == 500.0f, "route-teki-damage");
                check(hits[i].attributeToSelf && hits[i].attackerToken == 0,
                      "route-teki-self");
            }
            if (hits[i].receiverId == 1) {
                pikiHit = true;
                check(hits[i].damage == 10.0f, "route-piki-damage");
                check(!hits[i].attributeToSelf && hits[i].attackerToken == 61,
                      "route-piki-carrier");
            }
        }
        check(tekiHit && pikiHit, "route-both-kinds");
    }

    // 9. Unconfirmed carrier falls back to bomb-self attribution (source
    // mCarrier==nullptr fallback, bombState.cpp:170-172).
    {
        P2BombPayloadPool pool(2);
        P2BombPayloadHandle h = pool.birth(71, joint(0, 0, 0), defaults());
        check(pool.detonate(h, P2BombPayloadTrigger::Earthquake, carrierLiveFalse, nullptr),
              "fallback-detonate");
        const P2BombSaraiBlastEvent& blast = pool.lastBlast(h);
        check(blast.hasCarrier && !blast.carrierValid, "fallback-invalid");
        P2BombSaraiReceiver receiver;
        receiver.id = 0;
        receiver.position = joint(5, 0, 0);
        receiver.kind = P2BombSaraiReceiverKind::Navi;
        P2BombSaraiRoutedHit hit;
        check(p2_bombsarai_route_blast(blast, &receiver, 1, &hit, 1) == 1,
              "fallback-routed");
        check(hit.attributeToSelf && hit.attackerToken == 0, "fallback-self");
    }

    // 10. Trigger names for consumer markers.
    {
        check(std::string(p2_bomb_payload_trigger_name(P2BombPayloadTrigger::Contact)) == "contact",
              "trigger-contact");
        check(std::string(p2_bomb_payload_trigger_name(P2BombPayloadTrigger::Death)) == "death",
              "trigger-death");
    }

    if (failures == 0) {
        std::printf("PASS P2_BOMB_PAYLOAD_ACTOR checks=%d\n", checks);
        return 0;
    }
    std::printf("FAIL P2_BOMB_PAYLOAD_ACTOR failures=%d checks=%d\n", failures, checks);
    return 1;
}
