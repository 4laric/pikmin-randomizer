#pragma once

#include "pc_p2_bigtreasure_attacks.h"
#include "pc_p2_bigtreasure_fsm.h"

#include <cstddef>
#include <cstdint>

// ---------------------------------------------------------------------------
// Pikmin 2 Titan Dweevil (BigTreasure) persistence policy -- lane 32, #246/#175
//
// Engine-free, versioned, fixed-size, endian-stable serialization of the
// lane-owned BigTreasure state. This closes the audit's persistence gap
// (PIKMIN2_BIGTREASURE_AUDIT.md, open question Q4: "no BigTreasure
// doSave/serialization override found ... weapon HP, knocked-off weapon cargo
// state and boss state across cave-floor/day transitions are unresolved").
//
// *** LANE PROPOSAL ONLY -- NOT WIRED INTO THE GAME SAVE PATH ***
// This module is deliberately standalone: it touches no engine save file, no
// RandomAccessStream, no shared save block and no hook. It is submitted for
// the lane 06/01 shared-save review before any integration. The root save
// format, block offset, ordering and checksum coverage are owned by the shared
// save contract; this record is only the lane's proposed per-actor payload.
//
// What is serialized (the three audit-flagged surfaces):
//   * Ownership: 4 weapon attached flags + per-weapon HP + Louie attached.
//   * FSM: phase, chosen weapon, pending-next phase, awaiting-pick flag,
//     waiting-for-IK flag and the state timer.
//   * Attack-pool ledger: per-element started flags, in-flight counts and the
//     elec max-discharge count.
//   * "Dropped weapon cargo" ledger: which weapons (and Louie) were released
//     as loose cargo, with their pop velocity, so a restore neither re-captures
//     a dropped pellet nor duplicates its delivery reward.
//
// Fail-closed by construction: `decode`/`restore` reject wrong magic, wrong
// schema version, truncated/oversized input, a bad CRC-32, non-finite floats,
// out-of-range values and every invariant violation below. Restore stages the
// parsed state in a local snapshot and only mutates the live objects after the
// whole record validates, so a rejected restore performs no partial mutation.
//
// Range conventions: floats are IEEE-754 bit patterns in little-endian order,
// so the same bytes decode on any host endianness. The schema is frozen by
// `kSchemaVersion`; bump it for any layout change.

namespace p2_bigtreasure_save {

// File header: magic + schema version + sizes. All integers little-endian.
constexpr std::size_t kHeaderOffsetMagic       = 0;  // 4 bytes
constexpr std::size_t kHeaderOffsetVersion     = 4;  // 2 bytes
constexpr std::size_t kHeaderOffsetRecordSize  = 6;  // 2 bytes
constexpr std::size_t kHeaderOffsetPayloadSize = 8;  // 4 bytes
constexpr std::size_t kHeaderSize              = 12;

// Payload field offsets, relative to the start of the payload.
constexpr std::size_t kPayloadOffsetAttachedMask     = 0;   // u8 bitmask
constexpr std::size_t kPayloadOffsetLouieAttached    = 1;   // u8 0/1
constexpr std::size_t kPayloadOffsetWeaponHealth     = 2;   // 4 x f32
constexpr std::size_t kPayloadOffsetPhase            = 18;  // enum byte
constexpr std::size_t kPayloadOffsetChosenWeapon     = 19;  // i8, -1 = none
constexpr std::size_t kPayloadOffsetAwaitingPick     = 20;  // u8 0/1
constexpr std::size_t kPayloadOffsetPendingNext      = 21;  // enum byte
constexpr std::size_t kPayloadOffsetWaitingForIK     = 22;  // u8 0/1
constexpr std::size_t kPayloadOffsetReserved0        = 23;  // u8, 0
constexpr std::size_t kPayloadOffsetStateTimer       = 24;  // f32
constexpr std::size_t kPayloadOffsetPoolStartedMask  = 28;  // u8 bitmask
constexpr std::size_t kPayloadOffsetPoolReserved0    = 29;  // u8, 0
constexpr std::size_t kPayloadOffsetPoolInFlight     = 30;  // 4 x u8
constexpr std::size_t kPayloadOffsetElecMaxNodes     = 34;  // u8
constexpr std::size_t kPayloadOffsetPoolReserved1    = 35;  // u8, 0
constexpr std::size_t kPayloadOffsetDroppedMask      = 36;  // u8 bitmask
constexpr std::size_t kPayloadOffsetLouieDropped     = 37;  // u8 0/1
constexpr std::size_t kPayloadOffsetCargoReserved    = 38;  // 2 x u8, 0
constexpr std::size_t kPayloadOffsetWeaponDropVel    = 40;  // 4 x vec3 (f32 x3)
constexpr std::size_t kPayloadOffsetLouieDropVel     = 88;  // vec3
constexpr std::size_t kPayloadSize                   = 100;

constexpr std::size_t kChecksumSize = 4; // CRC-32 over header+payload
constexpr std::size_t kRecordSize   = kHeaderSize + kPayloadSize + kChecksumSize;

// 'P','2','B','T' in file order (little-endian u32 0x54423250).
constexpr std::uint32_t kMagic         = 0x54423250u;
constexpr std::uint16_t kSchemaVersion = 1;

// Hard invariant from the source elec chain setup (BigTreasureAttack.cpp:1074,
// :2712-2747): one invisible anchor node plus maxDischarge visible nodes must
// fit the 17-node pool.
constexpr int kElecAnchorNodes = 1;
constexpr int kElecPoolCapacity = P2BigTreasureAttackPools::kElecCapacity;

} // namespace p2_bigtreasure_save

// Dropped-weapon cargo ledger. Weapons released by `update` (HP knock-off) or
// by defeat are loose cargo from that point on: their reward is already being
// paid out by the generic pellet path, so a restored game must not re-capture
// them or grant the reward twice. `weaponDropped[i]`/`louieDropped` record that
// release; the velocity is the source pop the pellet inherited.
struct P2BigTreasureDroppedCargo {
    bool weaponDropped[P2BTWEAPON_Count] = {};
    bool louieDropped = false;
    P2BigTreasureVec3 weaponVelocity[P2BTWEAPON_Count] = {};
    P2BigTreasureVec3 louieVelocity = {};
};

// Logical snapshot of every field the lane persists. Plain data so fixtures can
// build exact states and inspect restored ones without touching internals.
struct P2BigTreasureSaveData {
    // Ownership
    bool weaponAttached[P2BTWEAPON_Count] = {};
    float weaponHealth[P2BTWEAPON_Count] = {};
    bool louieAttached = false;

    // FSM (P2BigTreasureFsm private state)
    P2BigTreasurePhase phase = P2BT_Dead;
    int chosenWeapon = -1; // -1 = BIGATTACK_NULL / awaiting pick
    bool awaitingWeaponPick = false;
    P2BigTreasurePhase pendingNext = P2BT_Dead;
    bool waitingForIK = false;
    float stateTimer = 0.0f;

    // Attack-pool ledger
    bool poolStarted[P2BTWEAPON_Count] = {};
    int poolInFlight[P2BTWEAPON_Count] = {};
    int elecMaxNodes = 0;

    // Dropped weapon cargo
    P2BigTreasureDroppedCargo cargo;
};

// Explicit invariant check. Returns true only when every field is in range and
// cross-field invariants hold:
//   * phases are registered states (0..11); chosen weapon is -1 or 0..3;
//   * healths are finite and within [0, kWeaponMaxHealth] (6000); a detached
//     weapon has exactly zero health;
//   * a weapon cannot be attached and dropped at the same time;
//   * in-flight counts are within their per-element pool capacities
//     (fire 8, gas 200, water 16, elec 17);
//   * the elec discharge count satisfies 1 + maxDischarge <= 17;
//   * a chosen weapon is attached, state timer and velocities are finite.
// `apply_state`/`decode`/`restore` all run this before touching any object.
bool p2_bigtreasure_save_validate(const P2BigTreasureSaveData& data);

// Reads the live policy objects into `out`. Normalizes cargo velocities for
// entries that are not marked dropped to exactly zero.
void p2_bigtreasure_save_capture_state(const P2BigTreasureOwnership& ownership,
                                       const P2BigTreasureFsm& fsm,
                                       const P2BigTreasureAttackPools& pools,
                                       const P2BigTreasureDroppedCargo& cargo,
                                       P2BigTreasureSaveData& out);

// Validates `data` and only then writes every policy object. On failure the
// inputs are left untouched (no partial mutation) and false is returned.
bool p2_bigtreasure_save_apply_state(const P2BigTreasureSaveData& data,
                                     P2BigTreasureOwnership& ownership,
                                     P2BigTreasureFsm& fsm,
                                     P2BigTreasureAttackPools& pools,
                                     P2BigTreasureDroppedCargo& cargo);

// Serializes `data` to the fixed-size little-endian record. `encode` does not
// range-check the payload (that is the restore side's job) so fixtures can
// deliberately serialize out-of-range/NaN values; it only fails when the
// output buffer is too small or `outSize`/`out` are null. Always writes exactly
// p2_bigtreasure_save::kRecordSize bytes.
bool p2_bigtreasure_save_encode(const P2BigTreasureSaveData& data,
                                std::uint8_t* out, std::size_t outCapacity,
                                std::size_t* outSize);

// Parses and fully validates a record. Fail-closed: returns false on wrong
// magic, wrong version, wrong size, bad CRC-32, reserved bytes set, non-finite
// values, out-of-range values or any invariant violation. `out` is untouched
// on failure.
bool p2_bigtreasure_save_decode(const std::uint8_t* data, std::size_t size,
                                P2BigTreasureSaveData& out);

// Primary capture/restore: live policy objects <-> record bytes.
bool p2_bigtreasure_save_capture(const P2BigTreasureOwnership& ownership,
                                 const P2BigTreasureFsm& fsm,
                                 const P2BigTreasureAttackPools& pools,
                                 const P2BigTreasureDroppedCargo& cargo,
                                 std::uint8_t* out, std::size_t outCapacity,
                                 std::size_t* outSize);

bool p2_bigtreasure_save_restore(const std::uint8_t* data, std::size_t size,
                                 P2BigTreasureOwnership& ownership,
                                 P2BigTreasureFsm& fsm,
                                 P2BigTreasureAttackPools& pools,
                                 P2BigTreasureDroppedCargo& cargo);

// CRC-32 (IEEE 802.3, reflected, poly 0xEDB88320) over the given bytes. Exposed
// so a fixture can repair the checksum after tampering with a record to test
// the value-range checks separately from the checksum check.
std::uint32_t p2_bigtreasure_save_crc32(const std::uint8_t* data, std::size_t size);

// Friend bridge granting the free functions above access to the private policy
// members. Defined in pc_p2_bigtreasure_save.cpp; never exposed in a header.
struct P2BigTreasureSaveAccess;
