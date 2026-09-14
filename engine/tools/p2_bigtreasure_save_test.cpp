// Standalone engine-free fixture for the BigTreasure persistence proposal
// (pc_port/pc_p2_bigtreasure_save.h/.cpp), lane 32 #246/#175. It exercises the
// versioned fixed-size record, fail-closed restore and the resolution of the
// audit's persistence gap (weapon HP, dropped-weapon cargo and boss state).
// Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_save_test.cpp pc_port/pc_p2_bigtreasure_save.cpp pc_port/pc_p2_bigtreasure.cpp pc_port/pc_p2_bigtreasure_fsm.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o output/p2_bigtreasure_save_test.exe

#include "pc_p2_bigtreasure_save.h"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>

namespace {

using p2_bigtreasure_save::kHeaderSize;
using p2_bigtreasure_save::kPayloadSize;
using p2_bigtreasure_save::kRecordSize;
using p2_bigtreasure_save::kSchemaVersion;

bool near(float a, float b)
{
    return std::fabs(a - b) <= 1.0e-5f;
}

bool sameVec(const P2BigTreasureVec3& a, const P2BigTreasureVec3& b)
{
    return near(a.x, b.x) && near(a.y, b.y) && near(a.z, b.z);
}

bool sameData(const P2BigTreasureSaveData& a, const P2BigTreasureSaveData& b)
{
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        if (a.weaponAttached[i] != b.weaponAttached[i]) return false;
        if (!near(a.weaponHealth[i], b.weaponHealth[i])) return false;
        if (a.poolStarted[i] != b.poolStarted[i]) return false;
        if (a.poolInFlight[i] != b.poolInFlight[i]) return false;
        if (a.cargo.weaponDropped[i] != b.cargo.weaponDropped[i]) return false;
        if (!sameVec(a.cargo.weaponVelocity[i], b.cargo.weaponVelocity[i])) return false;
    }
    if (a.louieAttached != b.louieAttached) return false;
    if (a.phase != b.phase) return false;
    if (a.chosenWeapon != b.chosenWeapon) return false;
    if (a.awaitingWeaponPick != b.awaitingWeaponPick) return false;
    if (a.pendingNext != b.pendingNext) return false;
    if (a.waitingForIK != b.waitingForIK) return false;
    if (!near(a.stateTimer, b.stateTimer)) return false;
    if (a.elecMaxNodes != b.elecMaxNodes) return false;
    if (a.cargo.louieDropped != b.cargo.louieDropped) return false;
    if (!sameVec(a.cargo.louieVelocity, b.cargo.louieVelocity)) return false;
    return true;
}

P2BigTreasureSaveData fullLoadout()
{
    P2BigTreasureSaveData data;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        data.weaponAttached[i] = true;
        data.weaponHealth[i]   = P2BigTreasureOwnership::kWeaponMaxHealth;
    }
    data.louieAttached = true;
    data.elecMaxNodes  = 15;
    return data;
}

// Drives the real engine-free FSM to PreAttack and feeds a host weapon pick, so
// the captured `chosenWeapon`/`awaitingWeaponPick` come from live policy state
// rather than a hand-built snapshot.
void arriveAtChosenPreAttack(P2BigTreasureFsm& fsm, int chosen)
{
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureFsmOutput out;

    P2BigTreasureFsmInput in;
    in.hasTarget      = true;
    in.bootDemoPlayed = true;
    in.health         = P2BigTreasureOwnership::kWeaponMaxHealth;
    int guard = 0;
    while (fsm.state() != P2BT_Land && guard++ < 400) {
        fsm.update(in, out);
    }
    assert(fsm.state() == P2BT_Land);

    in = P2BigTreasureFsmInput{};
    in.animEnd       = true;
    in.hasAnyWeapon  = true;
    in.health        = P2BigTreasureOwnership::kWeaponMaxHealth;
    fsm.update(in, out);
    assert(fsm.state() == P2BT_ItemWalk);

    in = P2BigTreasureFsmInput{};
    in.attackLimitTime = true;
    in.hasAnyWeapon    = true;
    in.health          = P2BigTreasureOwnership::kWeaponMaxHealth;
    fsm.update(in, out);

    in = P2BigTreasureFsmInput{};
    in.finishIKMotion = true;
    in.health         = P2BigTreasureOwnership::kWeaponMaxHealth;
    fsm.update(in, out);
    assert(fsm.state() == P2BT_PreAttack);
    assert(fsm.chosenWeapon() == -1); // awaiting the host pick

    in = P2BigTreasureFsmInput{};
    in.chosenWeapon                 = chosen;
    in.weaponAttached[chosen]       = true;
    in.hasAnyWeapon                 = true;
    in.health                       = P2BigTreasureOwnership::kWeaponMaxHealth;
    fsm.update(in, out);
    assert(fsm.chosenWeapon() == chosen);
}

void testLayoutStability()
{
    static_assert(kRecordSize == 116, "frozen record size");
    static_assert(kPayloadSize == 100, "frozen payload size");
    static_assert(kSchemaVersion == 1, "frozen schema version");
    static_assert(p2_bigtreasure_save::kMagic == 0x54423250u, "frozen magic");

    const P2BigTreasureSaveData data = fullLoadout();
    std::uint8_t record[kRecordSize] = {};
    std::size_t size = 0;
    assert(p2_bigtreasure_save_encode(data, record, sizeof(record), &size));
    assert(size == kRecordSize);
    assert(record[0] == 'P' && record[1] == '2' && record[2] == 'B' && record[3] == 'T');
    assert(record[4] == 1 && record[5] == 0);          // version LE
    assert(record[6] == 116 && record[7] == 0);        // record size LE
    assert(record[8] == 100 && record[9] == 0);        // payload size LE
    assert(record[10] == 0 && record[11] == 0);

    // Capacity/null guards.
    assert(!p2_bigtreasure_save_encode(data, record, kRecordSize - 1, &size));
    assert(!p2_bigtreasure_save_encode(data, nullptr, sizeof(record), &size));
    assert(!p2_bigtreasure_save_encode(data, record, sizeof(record), nullptr));
    std::puts("PASS save_layout_stability");
}

void testFullLoadoutRoundTrip()
{
    P2BigTreasureOwnership ownership;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) ownership.attachWeapon(i);
    ownership.attachLouie();
    P2BigTreasureFsm fsm;
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools pools;
    P2BigTreasureDroppedCargo cargo;

    P2BigTreasureSaveData before;
    p2_bigtreasure_save_capture_state(ownership, fsm, pools, cargo, before);

    std::uint8_t record[kRecordSize] = {};
    std::size_t size = 0;
    assert(p2_bigtreasure_save_capture(ownership, fsm, pools, cargo, record, sizeof(record),
                                       &size));
    assert(size == kRecordSize);

    P2BigTreasureSaveData decoded;
    assert(p2_bigtreasure_save_decode(record, size, decoded));
    assert(sameData(before, decoded));

    P2BigTreasureOwnership restoredOwnership;
    P2BigTreasureFsm restoredFsm;
    restoredFsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools restoredPools;
    P2BigTreasureDroppedCargo restoredCargo;
    assert(p2_bigtreasure_save_restore(record, size, restoredOwnership, restoredFsm,
                                       restoredPools, restoredCargo));
    assert(restoredOwnership.weaponCount() == 4);
    assert(restoredOwnership.louieAttached());
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        assert(near(restoredOwnership.weaponHealth(i), P2BigTreasureOwnership::kWeaponMaxHealth));
    }
    assert(restoredFsm.state() == P2BT_Stay);

    P2BigTreasureSaveData after;
    p2_bigtreasure_save_capture_state(restoredOwnership, restoredFsm, restoredPools, restoredCargo,
                                      after);
    assert(sameData(before, after));
    std::puts("PASS save_full_loadout_roundtrip");
}

void testKnockOffCargoLedger()
{
    P2BigTreasureOwnership ownership;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) ownership.attachWeapon(i);
    ownership.attachLouie();
    assert(ownership.addWeaponDamage(P2BTWEAPON_Fire, P2BigTreasureOwnership::kWeaponMaxHealth,
                                     false));
    P2BigTreasureDropEvent drops[P2BTWEAPON_Count + 1] = {};
    assert(ownership.update(drops, P2BTWEAPON_Count + 1) == 1);
    assert(drops[0].weapon == P2BTWEAPON_Fire);
    assert(!drops[0].isLouie);
    assert(near(drops[0].velocity.y, P2BigTreasureOwnership::kKnockOffPopY));

    P2BigTreasureDroppedCargo cargo;
    cargo.weaponDropped[P2BTWEAPON_Fire] = true;
    cargo.weaponVelocity[P2BTWEAPON_Fire] = drops[0].velocity;

    P2BigTreasureFsm fsm;
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools pools;

    std::uint8_t record[kRecordSize] = {};
    std::size_t size = 0;
    assert(p2_bigtreasure_save_capture(ownership, fsm, pools, cargo, record, sizeof(record),
                                       &size));

    P2BigTreasureOwnership restoredOwnership;
    P2BigTreasureFsm restoredFsm;
    restoredFsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools restoredPools;
    P2BigTreasureDroppedCargo restoredCargo;
    assert(p2_bigtreasure_save_restore(record, size, restoredOwnership, restoredFsm,
                                       restoredPools, restoredCargo));

    // The knocked-off weapon is not re-captured and its reward ledger survives.
    assert(restoredOwnership.weaponCount() == 3);
    assert(!restoredOwnership.isWeaponAttached(P2BTWEAPON_Fire));
    assert(restoredCargo.weaponDropped[P2BTWEAPON_Fire]);
    assert(!restoredCargo.weaponDropped[P2BTWEAPON_Elec]);
    assert(sameVec(restoredCargo.weaponVelocity[P2BTWEAPON_Fire], drops[0].velocity));
    assert(!restoredOwnership.isBodyExposed());

    // A dropped and re-attached pellet is contradictory and must be rejected.
    P2BigTreasureSaveData inconsistent;
    p2_bigtreasure_save_capture_state(restoredOwnership, restoredFsm, restoredPools, restoredCargo,
                                      inconsistent);
    inconsistent.weaponAttached[P2BTWEAPON_Fire] = true;
    inconsistent.weaponHealth[P2BTWEAPON_Fire] = P2BigTreasureOwnership::kWeaponMaxHealth;
    assert(!p2_bigtreasure_save_validate(inconsistent));

    // Louie release is tracked independently.
    P2BigTreasureDroppedCargo louieCargo;
    louieCargo.louieDropped = true;
    louieCargo.louieVelocity = P2BigTreasureVec3{ 0.0f, P2BigTreasureOwnership::kLouiePopY, 0.0f };
    P2BigTreasureOwnership louieOwnership;
    assert(louieOwnership.releaseLouie(nullptr) == false); // not attached yet
    P2BigTreasureSaveData louieData = fullLoadout();
    louieData.louieAttached = false;
    louieData.cargo = louieCargo;
    assert(p2_bigtreasure_save_validate(louieData));
    P2BigTreasureSaveData badLouie = louieData;
    badLouie.louieAttached = true; // both attached and dropped
    assert(!p2_bigtreasure_save_validate(badLouie));
    std::puts("PASS save_knockoff_cargo_ledger");
}

void testFsmFieldsRoundTrip()
{
    P2BigTreasureSaveData data = fullLoadout();
    data.phase              = P2BT_PreAttack;
    data.chosenWeapon       = -1;
    data.awaitingWeaponPick = true;
    data.pendingNext        = P2BT_Walk;
    data.waitingForIK       = true;
    data.stateTimer         = 1.5f;
    assert(p2_bigtreasure_save_validate(data));

    P2BigTreasureOwnership ownership;
    P2BigTreasureFsm fsm;
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools pools;
    P2BigTreasureDroppedCargo cargo;
    assert(p2_bigtreasure_save_apply_state(data, ownership, fsm, pools, cargo));
    assert(fsm.state() == P2BT_PreAttack);
    assert(fsm.chosenWeapon() == -1);

    P2BigTreasureSaveData after;
    p2_bigtreasure_save_capture_state(ownership, fsm, pools, cargo, after);
    assert(after.phase == P2BT_PreAttack);
    assert(after.chosenWeapon == -1);
    assert(after.awaitingWeaponPick);
    assert(after.pendingNext == P2BT_Walk);
    assert(after.waitingForIK);
    assert(near(after.stateTimer, 1.5f));

    // Drive the real FSM to a chosen weapon and re-capture.
    P2BigTreasureFsm attacking;
    arriveAtChosenPreAttack(attacking, P2BTWEAPON_Gas);
    P2BigTreasureSaveData chosen;
    p2_bigtreasure_save_capture_state(ownership, attacking, pools, cargo, chosen);
    assert(chosen.chosenWeapon == P2BTWEAPON_Gas);
    assert(!chosen.awaitingWeaponPick);
    assert(chosen.phase == P2BT_PreAttack);

    // The natural death path persists as the Dead phase.
    P2BigTreasureFsm dead;
    dead.reset(P2BigTreasureFsmParms{});
    P2BigTreasureFsmInput kill;
    kill.killed = true;
    P2BigTreasureFsmOutput killOut;
    dead.update(kill, killOut);
    assert(dead.state() == P2BT_Dead);
    P2BigTreasureSaveData deadData;
    p2_bigtreasure_save_capture_state(ownership, dead, pools, cargo, deadData);
    assert(deadData.phase == P2BT_Dead);
    std::puts("PASS save_fsm_fields_roundtrip");
}

void testAttackPoolLedgerRoundTrip()
{
    P2BigTreasureAttackPools pools;
    assert(pools.start(P2BTWEAPON_Elec));
    assert(pools.emit(P2BTWEAPON_Elec));
    assert(pools.emit(P2BTWEAPON_Elec));
    assert(pools.emit(P2BTWEAPON_Elec));
    assert(pools.start(P2BTWEAPON_Water));
    assert(pools.emit(P2BTWEAPON_Water));
    assert(pools.emit(P2BTWEAPON_Water));
    assert(pools.start(P2BTWEAPON_Fire));
    assert(pools.setElecMaxDischarge(16));

    P2BigTreasureOwnership ownership;
    P2BigTreasureFsm fsm;
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureDroppedCargo cargo;

    std::uint8_t record[kRecordSize] = {};
    std::size_t size = 0;
    assert(p2_bigtreasure_save_capture(ownership, fsm, pools, cargo, record, sizeof(record),
                                       &size));

    P2BigTreasureOwnership restoredOwnership;
    P2BigTreasureFsm restoredFsm;
    restoredFsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools restoredPools;
    P2BigTreasureDroppedCargo restoredCargo;
    assert(p2_bigtreasure_save_restore(record, size, restoredOwnership, restoredFsm,
                                       restoredPools, restoredCargo));
    assert(restoredPools.isStarted(P2BTWEAPON_Elec));
    assert(restoredPools.isStarted(P2BTWEAPON_Water));
    assert(restoredPools.isStarted(P2BTWEAPON_Fire));
    assert(!restoredPools.isStarted(P2BTWEAPON_Gas));
    assert(restoredPools.inFlight(P2BTWEAPON_Elec) == 3);
    assert(restoredPools.inFlight(P2BTWEAPON_Water) == 2);
    assert(restoredPools.inFlight(P2BTWEAPON_Fire) == 0);

    P2BigTreasureSaveData after;
    p2_bigtreasure_save_capture_state(restoredOwnership, restoredFsm, restoredPools, restoredCargo,
                                      after);
    assert(after.elecMaxNodes == 16);
    assert(after.poolInFlight[P2BTWEAPON_Elec] == 3);
    assert(after.poolInFlight[P2BTWEAPON_Water] == 2);
    std::puts("PASS save_attack_pool_ledger_roundtrip");
}

void testRejections()
{
    const P2BigTreasureSaveData good = fullLoadout();
    std::uint8_t record[kRecordSize] = {};
    std::size_t size = 0;
    assert(p2_bigtreasure_save_encode(good, record, sizeof(record), &size));

    P2BigTreasureOwnership ownership;
    P2BigTreasureFsm fsm;
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools pools;
    P2BigTreasureDroppedCargo cargo;

    // Wrong magic.
    {
        std::uint8_t copy[kRecordSize];
        std::memcpy(copy, record, kRecordSize);
        copy[0] = static_cast<std::uint8_t>(copy[0] ^ 0xFFu);
        assert(!p2_bigtreasure_save_restore(copy, kRecordSize, ownership, fsm, pools, cargo));
    }
    // Wrong version.
    {
        std::uint8_t copy[kRecordSize];
        std::memcpy(copy, record, kRecordSize);
        copy[4] = 2;
        copy[5] = 0;
        assert(!p2_bigtreasure_save_restore(copy, kRecordSize, ownership, fsm, pools, cargo));
    }
    // Wrong header record size.
    {
        std::uint8_t copy[kRecordSize];
        std::memcpy(copy, record, kRecordSize);
        copy[6] = 0;
        assert(!p2_bigtreasure_save_restore(copy, kRecordSize, ownership, fsm, pools, cargo));
    }
    // Truncated and oversized.
    assert(!p2_bigtreasure_save_restore(record, kRecordSize - 1, ownership, fsm, pools, cargo));
    assert(!p2_bigtreasure_save_restore(record, kRecordSize + 1, ownership, fsm, pools, cargo));
    assert(!p2_bigtreasure_save_restore(nullptr, kRecordSize, ownership, fsm, pools, cargo));
    // Corrupt checksum (payload byte flipped, CRC untouched).
    {
        std::uint8_t copy[kRecordSize];
        std::memcpy(copy, record, kRecordSize);
        copy[kHeaderSize + 2] = static_cast<std::uint8_t>(copy[kHeaderSize + 2] ^ 0x01u);
        assert(!p2_bigtreasure_save_restore(copy, kRecordSize, ownership, fsm, pools, cargo));
    }

    // These encode fine (encode does not range-check) but restore rejects.
    auto rejects = [&](const P2BigTreasureSaveData& data) {
        std::uint8_t bad[kRecordSize] = {};
        std::size_t badSize = 0;
        assert(p2_bigtreasure_save_encode(data, bad, sizeof(bad), &badSize));
        assert(!p2_bigtreasure_save_restore(bad, badSize, ownership, fsm, pools, cargo));
    };
    {
        P2BigTreasureSaveData data = good;
        data.weaponHealth[0] = std::numeric_limits<float>::quiet_NaN();
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.weaponHealth[0] = 6000.5f;
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.weaponHealth[0] = -1.0f;
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.elecMaxNodes = 17; // 1 + 17 > 17
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.poolInFlight[P2BTWEAPON_Fire] = 9; // capacity 8
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.phase = static_cast<P2BigTreasurePhase>(99);
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.chosenWeapon = 4;
        rejects(data);
    }
    {
        P2BigTreasureSaveData data = good;
        data.weaponAttached[P2BTWEAPON_Elec] = false; // detached with health 6000
        rejects(data);
    }
    std::puts("PASS save_rejections");
}

void testNoPartialMutationOnReject()
{
    P2BigTreasureOwnership ownership;
    ownership.attachWeapon(P2BTWEAPON_Elec);
    ownership.attachLouie();
    P2BigTreasureFsm fsm;
    fsm.reset(P2BigTreasureFsmParms{});
    P2BigTreasureAttackPools pools;
    assert(pools.start(P2BTWEAPON_Fire));
    assert(pools.emit(P2BTWEAPON_Fire));
    assert(pools.emit(P2BTWEAPON_Fire));
    P2BigTreasureDroppedCargo cargo;

    P2BigTreasureSaveData before;
    p2_bigtreasure_save_capture_state(ownership, fsm, pools, cargo, before);

    // Reject via bad checksum.
    std::uint8_t record[kRecordSize] = {};
    std::size_t size = 0;
    assert(p2_bigtreasure_save_encode(before, record, sizeof(record), &size));
    record[kHeaderSize + 4] = static_cast<std::uint8_t>(record[kHeaderSize + 4] ^ 0x80u);
    assert(!p2_bigtreasure_save_restore(record, size, ownership, fsm, pools, cargo));

    P2BigTreasureSaveData afterChecksum;
    p2_bigtreasure_save_capture_state(ownership, fsm, pools, cargo, afterChecksum);
    assert(sameData(before, afterChecksum));
    assert(ownership.weaponCount() == 1);
    assert(ownership.isWeaponAttached(P2BTWEAPON_Elec));
    assert(pools.isStarted(P2BTWEAPON_Fire));
    assert(pools.inFlight(P2BTWEAPON_Fire) == 2);

    // Reject via a valid checksum but an out-of-range value.
    P2BigTreasureSaveData outOfRange = before;
    outOfRange.poolInFlight[P2BTWEAPON_Fire] = 9;
    std::uint8_t bad[kRecordSize] = {};
    std::size_t badSize = 0;
    assert(p2_bigtreasure_save_encode(outOfRange, bad, sizeof(bad), &badSize));
    assert(p2_bigtreasure_save_crc32(bad, kRecordSize - 4)
           == (static_cast<std::uint32_t>(bad[kRecordSize - 4])
               | (static_cast<std::uint32_t>(bad[kRecordSize - 3]) << 8)
               | (static_cast<std::uint32_t>(bad[kRecordSize - 2]) << 16)
               | (static_cast<std::uint32_t>(bad[kRecordSize - 1]) << 24)));
    assert(!p2_bigtreasure_save_restore(bad, badSize, ownership, fsm, pools, cargo));

    P2BigTreasureSaveData afterRange;
    p2_bigtreasure_save_capture_state(ownership, fsm, pools, cargo, afterRange);
    assert(sameData(before, afterRange));
    std::puts("PASS save_no_partial_mutation_on_reject");
}

void testInvariantEnforced()
{
    P2BigTreasureSaveData data = fullLoadout();
    assert(p2_bigtreasure_save_validate(data));

    data.elecMaxNodes = 16;
    assert(p2_bigtreasure_save_validate(data)); // 1 + 16 == 17 allowed
    data.elecMaxNodes = 17;
    assert(!p2_bigtreasure_save_validate(data));
    data.elecMaxNodes = -1;
    assert(!p2_bigtreasure_save_validate(data));

    data.elecMaxNodes = 15;
    data.weaponHealth[P2BTWEAPON_Fire] = 6000.0f;
    assert(p2_bigtreasure_save_validate(data));
    data.weaponHealth[P2BTWEAPON_Fire] = 6000.5f;
    assert(!p2_bigtreasure_save_validate(data));
    data.weaponHealth[P2BTWEAPON_Fire] = 3000.0f;
    assert(p2_bigtreasure_save_validate(data));

    data.weaponHealth[P2BTWEAPON_Fire] = 6000.0f;
    data.poolInFlight[P2BTWEAPON_Fire] = 8;
    assert(p2_bigtreasure_save_validate(data));
    data.poolInFlight[P2BTWEAPON_Fire] = 9;
    assert(!p2_bigtreasure_save_validate(data));
    data.poolInFlight[P2BTWEAPON_Fire] = 0;

    data.phase = static_cast<P2BigTreasurePhase>(12);
    assert(!p2_bigtreasure_save_validate(data));
    data.phase = P2BT_Attack;
    assert(p2_bigtreasure_save_validate(data));
    std::puts("PASS save_invariant_enforced");
}

} // namespace

int main()
{
    testLayoutStability();
    testFullLoadoutRoundTrip();
    testKnockOffCargoLedger();
    testFsmFieldsRoundTrip();
    testAttackPoolLedgerRoundTrip();
    testRejections();
    testNoPartialMutationOnReject();
    testInvariantEnforced();
    std::puts("PASS BIGTREASURE_SAVE");
    return 0;
}
