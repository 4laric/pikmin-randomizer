// Standalone engine-free fixture for the private projectile proxy receiver
// (pc_port/pc_p2_projectile_receiver.h/.cpp), lane 20. It links the Stone and
// Rock policies only to compare proxy application against the documented
// contact rules; no engine headers are involved. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_projectile_receiver_test.cpp pc_port/pc_p2_projectile_receiver.cpp pc_port/pc_p2_cannon_stone.cpp pc_port/pc_p2_rock_hazard.cpp -o <private-output>/p2_projectile_receiver_test.exe

#include "pc_p2_projectile_receiver.h"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>

namespace {
constexpr std::uint64_t kNaviToken = 0x1001ULL;
constexpr std::uint64_t kTekiToken = 0x2002ULL;
constexpr std::uint64_t kSourceToken = 0x3003ULL;
constexpr std::uint64_t kSelfToken = 0x4004ULL;

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

P2CannonStoneConfig stoneConfig(float attackDamage)
{
    P2CannonStoneConfig config;
    config.variant = P2CannonStoneVariant::Stone;
    config.moveSpeed = 250.0f;
    config.searchRumbleSpeed = 100.0f;
    config.turnSpeed = 1.0f;
    config.maxTurnAngle = 180.0f;
    config.attackDamage = attackDamage;
    config.sightRadius = 550.0f;
    config.collisionRadius = 40.0f;
    config.health = 99999.0f;
    return config;
}

P2RockHazardConfig rockConfig(float attackDamage)
{
    P2RockHazardConfig config;
    config.fallSpeed = 500.0f;
    config.fallOffset = 100.0f;
    config.scaleUpRate = 5.0f;
    config.sightRadius = 350.0f;
    config.attackDamage = attackDamage;
    config.collisionRadius = 40.0f;
    config.health = 100.0f;
    return config;
}

P2CannonStone makeStone(float attackDamage, std::uint64_t source, std::uint64_t self)
{
    P2CannonStone stone;
    stone.reset(stoneConfig(attackDamage));
    assert(stone.birth({ 0.0f, 50.0f, 0.0f }, 0.0f, false, source, self));
    return stone;
}

// Drop-group onInit -> DropWait -> Fall keeps atari on with a live FSM so the
// contact rules can be exercised directly.
P2RockHazard makeDropRock(float attackDamage, std::uint64_t source, std::uint64_t self)
{
    P2RockHazard rock;
    rock.reset(rockConfig(attackDamage));
    P2RockHazardInit init;
    init.position = { 0.0f, 100.0f, 0.0f };
    init.dropGroupNone = false;
    init.sourceToken = source;
    init.selfToken = self;
    assert(rock.onInit(init));
    assert(rock.update(P2RockHazard::kSourceDelta, P2RockHazardDetection{}));
    assert(rock.phase() == P2RockHazardPhase::Fall);
    return rock;
}

void testDamageMath()
{
    P2ProjectileReceiver receiver(1, 100.0f);
    assert(receiver.alive());
    assert(near(receiver.maxHealth(), 100.0f) && near(receiver.health(), 100.0f));

    assert(near(receiver.applyDamage(30.0f), 30.0f));
    assert(near(receiver.health(), 70.0f) && receiver.alive());

    // Non-positive damage removes nothing.
    assert(near(receiver.applyDamage(0.0f), 0.0f));
    assert(near(receiver.applyDamage(-5.0f), 0.0f));
    assert(near(receiver.health(), 70.0f));

    assert(near(receiver.applyDamage(25.0f), 25.0f));
    assert(near(receiver.health(), 45.0f));

    // Clamp at zero and clear alive exactly once; later strikes remove nothing.
    assert(near(receiver.applyDamage(100.0f), 45.0f));
    assert(near(receiver.health(), 0.0f) && !receiver.alive());
    assert(near(receiver.applyDamage(100.0f), 0.0f));
    assert(near(receiver.health(), 0.0f) && !receiver.alive());
}

void testRegistryStrikeDeathOnce()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 100.0f));
    assert(registry.add(kTekiToken, 250.0f));
    assert(registry.count() == 2 && registry.aliveCount() == 2);

    const P2ProjectileReceiverHit first = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::InteractPress, 60.0f, kNaviToken, kSourceToken);
    assert(first.known && first.applied && !first.died);
    assert(first.kind == P2ProjectileReceiverStrikeKind::InteractPress);
    assert(near(first.damage, 60.0f) && near(first.appliedDamage, 60.0f));
    assert(near(first.health, 40.0f));
    assert(first.targetToken == kNaviToken && first.attributedToken == kSourceToken);

    const P2ProjectileReceiverHit killing = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::InteractAttack, 250.0f, kNaviToken, kSelfToken);
    assert(killing.known && killing.applied && killing.died);
    assert(near(killing.appliedDamage, 40.0f)); // clamped to remaining health
    assert(near(killing.health, 0.0f));
    assert(killing.kind == P2ProjectileReceiverStrikeKind::InteractAttack);
    assert(killing.attributedToken == kSelfToken);
    assert(registry.aliveCount() == 1);

    const P2ProjectileReceiverHit after = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::InteractAttack, 250.0f, kNaviToken, kSelfToken);
    assert(after.known && !after.applied && !after.died);
    assert(near(after.health, 0.0f));
}

void testUnknownTokenAndKindNoOp()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 100.0f));

    const P2ProjectileReceiverHit unknown = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::InteractAttack, 250.0f, kTekiToken, 0);
    assert(!unknown.known && !unknown.applied && !unknown.died);
    assert(near(unknown.health, 0.0f));

    const P2ProjectileReceiverHit none = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::None, 50.0f, kNaviToken, kSourceToken);
    assert(none.known && !none.applied && !none.died);
    assert(near(registry.find(kNaviToken)->health(), 100.0f));
}

void testRegistryValidationAndReset()
{
    P2ProjectileReceiverRegistry registry;
    assert(!registry.add(0, 100.0f));
    assert(!registry.add(kNaviToken, 0.0f));
    assert(!registry.add(kNaviToken, -1.0f));
    assert(!registry.add(kNaviToken, std::numeric_limits<float>::quiet_NaN()));
    assert(registry.add(kNaviToken, 100.0f));
    assert(!registry.add(kNaviToken, 100.0f)); // duplicate token
    assert(registry.count() == 1);

    // Fill to capacity; one more is refused with no partial state.
    for (int i = 1; i < P2ProjectileReceiverRegistry::kMaxReceivers; ++i) {
        assert(registry.add(kNaviToken + static_cast<std::uint64_t>(i), 10.0f));
    }
    assert(registry.count() == P2ProjectileReceiverRegistry::kMaxReceivers);
    assert(!registry.add(0xffffULL, 10.0f));
    assert(registry.count() == P2ProjectileReceiverRegistry::kMaxReceivers);

    registry.reset();
    assert(registry.count() == 0 && registry.aliveCount() == 0);
    assert(registry.find(kNaviToken) == nullptr);
}

// Direct comparison against the documented Stone contact rules:
//   grounded Navi/Piki -> InteractPress(configured attackDamage), attributed to
//   the source when set and to the Stone otherwise; Teki -> fixed 250
//   InteractAttack attributed to the Stone; airborne Navi/Piki -> no strike.
void testStoneContractComparison()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 100.0f));
    assert(registry.add(kTekiToken, 1000.0f));

    P2CannonStone stone = makeStone(10.0f, kSourceToken, kSelfToken);
    const P2CannonStoneContactResult press =
        stone.contact(P2CannonStoneContactKind::NaviPiki, true, false, kNaviToken);
    assert(press.strikeEmitted && press.strike.kind == P2CannonStoneStrikeKind::Press);
    const P2ProjectileReceiverHit pressHit = registry.applyStrike(press);
    assert(pressHit.kind == P2ProjectileReceiverStrikeKind::InteractPress);
    assert(near(pressHit.appliedDamage, press.strike.damage));
    assert(near(pressHit.health, 100.0f - press.strike.damage));
    assert(pressHit.attributedToken == kSourceToken);

    P2CannonStone tekiStone = makeStone(10.0f, kSourceToken, kSelfToken);
    const P2CannonStoneContactResult teki =
        tekiStone.contact(P2CannonStoneContactKind::Teki, true, false, kTekiToken);
    assert(teki.strikeEmitted && teki.strike.kind == P2CannonStoneStrikeKind::Attack);
    assert(near(teki.strike.damage, P2CannonStone::kTekiAttackDamage));
    const P2ProjectileReceiverHit tekiHit = registry.applyStrike(teki);
    assert(tekiHit.kind == P2ProjectileReceiverStrikeKind::InteractAttack);
    assert(near(tekiHit.appliedDamage, 250.0f));
    assert(near(tekiHit.health, 750.0f));
    assert(tekiHit.attributedToken == kSelfToken);

    // No source enemy: Press falls back to the Stone's self token.
    P2ProjectileReceiverRegistry selfRegistry;
    assert(selfRegistry.add(kNaviToken, 100.0f));
    P2CannonStone selfStone = makeStone(10.0f, 0, kSelfToken);
    const P2CannonStoneContactResult selfPress =
        selfStone.contact(P2CannonStoneContactKind::NaviPiki, true, false, kNaviToken);
    assert(selfPress.strikeEmitted && !selfPress.strike.attributedToSource);
    assert(selfRegistry.applyStrike(selfPress).attributedToken == kSelfToken);

    // An airborne Navi/Piki emits no strike, so the proxy never changes.
    P2CannonStone airStone = makeStone(10.0f, kSourceToken, kSelfToken);
    const P2CannonStoneContactResult air =
        airStone.contact(P2CannonStoneContactKind::NaviPiki, false, false, kNaviToken);
    assert(!air.strikeEmitted);
    const P2ProjectileReceiverHit airHit = registry.applyStrike(air);
    assert(!airHit.known && !airHit.applied);
    assert(near(registry.find(kNaviToken)->health(), 100.0f - 10.0f));
}

// Same comparison for the falling-Rock contact rules.
void testRockContractComparison()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.add(kNaviToken, 100.0f));
    assert(registry.add(kTekiToken, 1000.0f));

    P2RockHazard rock = makeDropRock(10.0f, kSourceToken, kSelfToken);
    const P2RockHazardContactResult press =
        rock.contact(P2RockHazardContactKind::NaviPiki, true, false, kNaviToken);
    assert(press.strikeEmitted && press.strike.kind == P2RockHazardStrikeKind::Press);
    const P2ProjectileReceiverHit pressHit = registry.applyStrike(press);
    assert(pressHit.kind == P2ProjectileReceiverStrikeKind::InteractPress);
    assert(near(pressHit.appliedDamage, press.strike.damage));
    assert(near(pressHit.health, 100.0f - press.strike.damage));
    assert(pressHit.attributedToken == kSourceToken);

    P2RockHazard tekiRock = makeDropRock(10.0f, kSourceToken, kSelfToken);
    const P2RockHazardContactResult teki =
        tekiRock.contact(P2RockHazardContactKind::Teki, true, false, kTekiToken);
    assert(teki.strikeEmitted && teki.strike.kind == P2RockHazardStrikeKind::Attack);
    assert(near(teki.strike.damage, P2RockHazard::kTekiAttackDamage));
    const P2ProjectileReceiverHit tekiHit = registry.applyStrike(teki);
    assert(tekiHit.kind == P2ProjectileReceiverStrikeKind::InteractAttack);
    assert(near(tekiHit.appliedDamage, 250.0f));
    assert(near(tekiHit.health, 750.0f));
    assert(tekiHit.attributedToken == kSelfToken);

    // Other (non-Navi/Piki, non-Teki) contacts zero the projectile health but
    // emit no strike, so the proxy is a no-op.
    P2RockHazard otherRock = makeDropRock(10.0f, kSourceToken, kSelfToken);
    const P2RockHazardContactResult other =
        otherRock.contact(P2RockHazardContactKind::Other, true, false, kNaviToken);
    assert(!other.strikeEmitted && other.healthZeroed);
    assert(!registry.applyStrike(other).known);
    assert(near(registry.find(kNaviToken)->health(), 100.0f - 10.0f));
}

// The wildcard sink lets a real run apply strikes to a proxy even though engine
// creature tokens are runtime pointers an arena config cannot name.
void testAnyReceiverSink()
{
    P2ProjectileReceiverRegistry registry;
    assert(registry.addAny(100.0f));
    assert(!registry.addAny(50.0f)); // only one wildcard is allowed
    assert(registry.aliveCount() == 1);

    const P2ProjectileReceiverHit wildcard = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::InteractPress, 60.0f, kTekiToken, kSourceToken);
    assert(wildcard.known && wildcard.applied && !wildcard.died);
    assert(wildcard.targetToken == kTekiToken); // reported token is the creature's
    assert(near(wildcard.health, 40.0f));

    // An exact receiver still takes precedence over the wildcard.
    assert(registry.add(kNaviToken, 10.0f));
    const P2ProjectileReceiverHit exact = registry.applyStrike(
        P2ProjectileReceiverStrikeKind::InteractAttack, 250.0f, kNaviToken, kSelfToken);
    assert(exact.applied && exact.died && near(exact.appliedDamage, 10.0f));
    assert(near(registry.find(kNaviToken)->health(), 0.0f));
    assert(registry.find(kTekiToken) == nullptr); // no exact kTeki receiver

    registry.reset();
    assert(!registry.addAny(0.0f) && !registry.addAny(-1.0f));
    assert(registry.count() == 0 && registry.aliveCount() == 0);
    assert(!registry.applyStrike(P2ProjectileReceiverStrikeKind::InteractPress, 5.0f,
                                 kTekiToken, 0).known);
}
} // namespace

int main()
{
    testDamageMath();
    testRegistryStrikeDeathOnce();
    testUnknownTokenAndKindNoOp();
    testRegistryValidationAndReset();
    testStoneContractComparison();
    testRockContractComparison();
    testAnyReceiverSink();
    return 0;
}
