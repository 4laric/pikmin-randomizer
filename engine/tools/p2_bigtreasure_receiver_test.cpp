// Standalone engine-free fixture for the BigTreasure elemental receiver
// decision (pc_port/pc_p2_bigtreasure_receiver.h/.cpp), issue #246. Proves the
// running element maps a confirmed hit to the source stimulus (fire/gas/water/
// elec), the source damage magnitude (attackDamage passthrough, water zero) and
// the elec zap direction magnitude. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_receiver_test.cpp pc_port/pc_p2_bigtreasure_receiver.cpp -o <private-output>/p2_bigtreasure_receiver_test.exe

#include "pc_p2_bigtreasure_receiver.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace {

const P2BigTreasureVec3 kOrigin{ 0.0f, 0.0f, 0.0f };

void testStimulusMap()
{
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Fire, kOrigin, 10.0f, kOrigin).stimulus
           == P2BigTreasureReceiverStimulus::Fire);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Gas, kOrigin, 10.0f, kOrigin).stimulus
           == P2BigTreasureReceiverStimulus::Gas);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Water, kOrigin, 10.0f, kOrigin).stimulus
           == P2BigTreasureReceiverStimulus::Water);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Elec, kOrigin, 10.0f, kOrigin).stimulus
           == P2BigTreasureReceiverStimulus::Elec);
    assert(p2_bigtreasure_receiver_resolve(-1, kOrigin, 10.0f, kOrigin).stimulus
           == P2BigTreasureReceiverStimulus::None);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Count, kOrigin, 10.0f, kOrigin).stimulus
           == P2BigTreasureReceiverStimulus::None);
    std::puts("PASS receiver_stimulus_map");
}

void testDamageMagnitude()
{
    // fire/gas/elec pass the boss attack damage through; water is 0 (bubble).
    const float atk = 27.5f;
    const P2BigTreasureVec3 target{ 0.0f, 0.0f, 100.0f };
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Fire, kOrigin, atk, target).damage
           == atk);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Gas, kOrigin, atk, target).damage
           == atk);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Elec, kOrigin, atk, target).damage
           == atk);
    assert(p2_bigtreasure_receiver_resolve(P2BTWEAPON_Water, kOrigin, atk, target).damage
           == 0.0f);
    std::puts("PASS receiver_damage");
}

void testElecDirection()
{
    const P2BigTreasureVec3 target{ 0.0f, 0.0f, 100.0f };
    const P2BigTreasureReceiverHit hit =
        p2_bigtreasure_receiver_resolve(P2BTWEAPON_Elec, kOrigin, 10.0f, target);
    const float xz = std::sqrt(hit.direction.x * hit.direction.x
                               + hit.direction.z * hit.direction.z);
    assert(std::fabs(xz - 150.0f) < 1e-3f);
    assert(std::fabs(hit.direction.y - 150.0f) < 1e-3f);
    // A non-elec stimulus carries a zero direction.
    assert(!p2_bigtreasure_receiver_resolve(P2BTWEAPON_Fire, kOrigin, 10.0f, target)
                .direction.z);
    std::puts("PASS receiver_elec_direction");
}

void testNoneStimulus()
{
    const P2BigTreasureReceiverHit none =
        p2_bigtreasure_receiver_resolve(-1, kOrigin, 10.0f, kOrigin);
    assert(none.stimulus == P2BigTreasureReceiverStimulus::None);
    assert(none.damage == 0.0f);
    assert(std::strcmp(p2_bigtreasure_receiver_stimulus_name(P2BigTreasureReceiverStimulus::None),
                       "none")
           == 0);
    assert(std::strcmp(p2_bigtreasure_receiver_stimulus_name(P2BigTreasureReceiverStimulus::Elec),
                       "elec")
           == 0);
    std::puts("PASS receiver_none_stimulus");
}

} // namespace

int main()
{
    testStimulusMap();
    testDamageMagnitude();
    testElecDirection();
    testNoneStimulus();
    std::puts("PASS BIGTREASURE_RECEIVER");
    return 0;
}
