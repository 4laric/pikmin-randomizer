#include "pc_p2_bigtreasure_save.h"

#include <cmath>
#include <cstring>

namespace {

constexpr int kFsmStateCount = 12;
constexpr std::uint8_t kWeaponMask = 0x0Fu;

bool validPhase(int phase)
{
    return phase >= 0 && phase < kFsmStateCount;
}

int poolCapacity(int element)
{
    switch (element) {
    case P2BTWEAPON_Fire: return P2BigTreasureAttackPools::kFireCapacity;
    case P2BTWEAPON_Gas: return P2BigTreasureAttackPools::kGasCapacity;
    case P2BTWEAPON_Water: return P2BigTreasureAttackPools::kWaterCapacity;
    case P2BTWEAPON_Elec: return P2BigTreasureAttackPools::kElecCapacity;
    default: return 0;
    }
}

bool finiteVec(const P2BigTreasureVec3& v)
{
    return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z);
}

bool zeroVec(const P2BigTreasureVec3& v)
{
    return v.x == 0.0f && v.y == 0.0f && v.z == 0.0f;
}

std::uint32_t floatBits(float value)
{
    std::uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

float bitsFloat(std::uint32_t bits)
{
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

void putU8(std::uint8_t* out, std::uint8_t value)
{
    out[0] = value;
}

std::uint8_t getU8(const std::uint8_t* in)
{
    return in[0];
}

void putU16(std::uint8_t* out, std::uint16_t value)
{
    out[0] = static_cast<std::uint8_t>(value & 0xFFu);
    out[1] = static_cast<std::uint8_t>((value >> 8) & 0xFFu);
}

std::uint16_t getU16(const std::uint8_t* in)
{
    return static_cast<std::uint16_t>(in[0]) | static_cast<std::uint16_t>(in[1] << 8);
}

void putU32(std::uint8_t* out, std::uint32_t value)
{
    out[0] = static_cast<std::uint8_t>(value & 0xFFu);
    out[1] = static_cast<std::uint8_t>((value >> 8) & 0xFFu);
    out[2] = static_cast<std::uint8_t>((value >> 16) & 0xFFu);
    out[3] = static_cast<std::uint8_t>((value >> 24) & 0xFFu);
}

std::uint32_t getU32(const std::uint8_t* in)
{
    return static_cast<std::uint32_t>(in[0]) | (static_cast<std::uint32_t>(in[1]) << 8)
           | (static_cast<std::uint32_t>(in[2]) << 16) | (static_cast<std::uint32_t>(in[3]) << 24);
}

void putF32(std::uint8_t* out, float value)
{
    putU32(out, floatBits(value));
}

float getF32(const std::uint8_t* in)
{
    return bitsFloat(getU32(in));
}

void putVec3(std::uint8_t* out, const P2BigTreasureVec3& value)
{
    putF32(out + 0, value.x);
    putF32(out + 4, value.y);
    putF32(out + 8, value.z);
}

P2BigTreasureVec3 getVec3(const std::uint8_t* in)
{
    P2BigTreasureVec3 value;
    value.x = getF32(in + 0);
    value.y = getF32(in + 4);
    value.z = getF32(in + 8);
    return value;
}

std::uint8_t weaponMask(const bool (&flags)[P2BTWEAPON_Count])
{
    std::uint8_t mask = 0;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        if (flags[i]) {
            mask = static_cast<std::uint8_t>(mask | (1u << i));
        }
    }
    return mask;
}

} // namespace

// Friend bridge: only this translation unit can see the private policy state.
// Every mutation goes through apply_state, which validates first.
struct P2BigTreasureSaveAccess {
    static void capture(const P2BigTreasureOwnership& ownership, const P2BigTreasureFsm& fsm,
                        const P2BigTreasureAttackPools& pools, P2BigTreasureSaveData& out)
    {
        for (int i = 0; i < P2BTWEAPON_Count; ++i) {
            out.weaponAttached[i] = ownership.mAttached[i];
            out.weaponHealth[i]   = ownership.mHealth[i];
        }
        out.louieAttached = ownership.mLouieAttached;

        out.phase              = fsm.mState;
        out.chosenWeapon       = fsm.mChosenWeapon;
        out.awaitingWeaponPick = fsm.mAwaitingWeaponPick;
        out.pendingNext        = fsm.mPendingNext;
        out.waitingForIK       = fsm.mWaitingForIK;
        out.stateTimer         = fsm.mStateTimer;

        for (int i = 0; i < P2BTWEAPON_Count; ++i) {
            out.poolStarted[i]  = pools.mStarted[i];
            out.poolInFlight[i] = pools.mInFlight[i];
        }
        out.elecMaxNodes = pools.mElecMaxNodes;
    }

    static void apply(const P2BigTreasureSaveData& data, P2BigTreasureOwnership& ownership,
                      P2BigTreasureFsm& fsm, P2BigTreasureAttackPools& pools)
    {
        for (int i = 0; i < P2BTWEAPON_Count; ++i) {
            ownership.mAttached[i] = data.weaponAttached[i];
            ownership.mHealth[i]   = data.weaponHealth[i];
        }
        ownership.mLouieAttached = data.louieAttached;

        fsm.mState              = data.phase;
        fsm.mChosenWeapon       = data.chosenWeapon;
        fsm.mAwaitingWeaponPick = data.awaitingWeaponPick;
        fsm.mPendingNext        = data.pendingNext;
        fsm.mWaitingForIK       = data.waitingForIK;
        fsm.mStateTimer         = data.stateTimer;

        for (int i = 0; i < P2BTWEAPON_Count; ++i) {
            pools.mStarted[i]  = data.poolStarted[i];
            pools.mInFlight[i] = data.poolInFlight[i];
        }
        pools.mElecMaxNodes = data.elecMaxNodes;
    }
};

void p2_bigtreasure_save_capture_state(const P2BigTreasureOwnership& ownership,
                                       const P2BigTreasureFsm& fsm,
                                       const P2BigTreasureAttackPools& pools,
                                       const P2BigTreasureDroppedCargo& cargo,
                                       P2BigTreasureSaveData& out)
{
    out = P2BigTreasureSaveData{};
    P2BigTreasureSaveAccess::capture(ownership, fsm, pools, out);
    out.cargo = cargo;
    // A weapon that is not loose cargo has no pop velocity to persist.
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        if (!out.cargo.weaponDropped[i]) {
            out.cargo.weaponVelocity[i] = P2BigTreasureVec3{};
        }
    }
    if (!out.cargo.louieDropped) {
        out.cargo.louieVelocity = P2BigTreasureVec3{};
    }
}

bool p2_bigtreasure_save_validate(const P2BigTreasureSaveData& data)
{
    if (!validPhase(static_cast<int>(data.phase))
        || !validPhase(static_cast<int>(data.pendingNext))) {
        return false;
    }
    if (data.chosenWeapon < -1 || data.chosenWeapon >= P2BTWEAPON_Count) {
        return false;
    }
    if (!std::isfinite(data.stateTimer)) {
        return false;
    }
    if (data.elecMaxNodes < 0
        || p2_bigtreasure_save::kElecAnchorNodes + data.elecMaxNodes
               > p2_bigtreasure_save::kElecPoolCapacity) {
        return false;
    }
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        if (!std::isfinite(data.weaponHealth[i])) {
            return false;
        }
        if (data.weaponHealth[i] < 0.0f
            || data.weaponHealth[i] > P2BigTreasureOwnership::kWeaponMaxHealth) {
            return false;
        }
        // Detached weapons are always reset to zero health on release.
        if (!data.weaponAttached[i] && data.weaponHealth[i] != 0.0f) {
            return false;
        }
        // A pellet cannot simultaneously be captured and loose cargo.
        if (data.weaponAttached[i] && data.cargo.weaponDropped[i]) {
            return false;
        }
        if (data.poolInFlight[i] < 0 || data.poolInFlight[i] > poolCapacity(i)) {
            return false;
        }
        if (!finiteVec(data.cargo.weaponVelocity[i])) {
            return false;
        }
        if (!data.cargo.weaponDropped[i] && !zeroVec(data.cargo.weaponVelocity[i])) {
            return false;
        }
    }
    if (data.chosenWeapon >= 0 && !data.weaponAttached[data.chosenWeapon]) {
        return false;
    }
    if (data.louieAttached && data.cargo.louieDropped) {
        return false;
    }
    if (!finiteVec(data.cargo.louieVelocity)) {
        return false;
    }
    if (!data.cargo.louieDropped && !zeroVec(data.cargo.louieVelocity)) {
        return false;
    }
    return true;
}

bool p2_bigtreasure_save_apply_state(const P2BigTreasureSaveData& data,
                                     P2BigTreasureOwnership& ownership,
                                     P2BigTreasureFsm& fsm,
                                     P2BigTreasureAttackPools& pools,
                                     P2BigTreasureDroppedCargo& cargo)
{
    if (!p2_bigtreasure_save_validate(data)) {
        return false;
    }
    P2BigTreasureSaveAccess::apply(data, ownership, fsm, pools);
    cargo = data.cargo;
    return true;
}

bool p2_bigtreasure_save_encode(const P2BigTreasureSaveData& data, std::uint8_t* out,
                                std::size_t outCapacity, std::size_t* outSize)
{
    if (!out || !outSize || outCapacity < p2_bigtreasure_save::kRecordSize) {
        return false;
    }
    std::memset(out, 0, p2_bigtreasure_save::kRecordSize);
    putU32(out + p2_bigtreasure_save::kHeaderOffsetMagic, p2_bigtreasure_save::kMagic);
    putU16(out + p2_bigtreasure_save::kHeaderOffsetVersion,
           p2_bigtreasure_save::kSchemaVersion);
    putU16(out + p2_bigtreasure_save::kHeaderOffsetRecordSize,
           static_cast<std::uint16_t>(p2_bigtreasure_save::kRecordSize));
    putU32(out + p2_bigtreasure_save::kHeaderOffsetPayloadSize,
           static_cast<std::uint32_t>(p2_bigtreasure_save::kPayloadSize));

    std::uint8_t* payload = out + p2_bigtreasure_save::kHeaderSize;
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetAttachedMask,
          weaponMask(data.weaponAttached));
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetLouieAttached,
          data.louieAttached ? 1u : 0u);
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        putF32(payload + p2_bigtreasure_save::kPayloadOffsetWeaponHealth + 4 * i,
               data.weaponHealth[i]);
    }
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetPhase,
          static_cast<std::uint8_t>(data.phase));
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetChosenWeapon,
          static_cast<std::uint8_t>(static_cast<std::int8_t>(data.chosenWeapon)));
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetAwaitingPick,
          data.awaitingWeaponPick ? 1u : 0u);
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetPendingNext,
          static_cast<std::uint8_t>(data.pendingNext));
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetWaitingForIK,
          data.waitingForIK ? 1u : 0u);
    putF32(payload + p2_bigtreasure_save::kPayloadOffsetStateTimer, data.stateTimer);

    putU8(payload + p2_bigtreasure_save::kPayloadOffsetPoolStartedMask,
          weaponMask(data.poolStarted));
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        putU8(payload + p2_bigtreasure_save::kPayloadOffsetPoolInFlight + i,
              static_cast<std::uint8_t>(data.poolInFlight[i]));
    }
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetElecMaxNodes,
          static_cast<std::uint8_t>(data.elecMaxNodes));

    putU8(payload + p2_bigtreasure_save::kPayloadOffsetDroppedMask,
          weaponMask(data.cargo.weaponDropped));
    putU8(payload + p2_bigtreasure_save::kPayloadOffsetLouieDropped,
          data.cargo.louieDropped ? 1u : 0u);
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        putVec3(payload + p2_bigtreasure_save::kPayloadOffsetWeaponDropVel + 12 * i,
                data.cargo.weaponVelocity[i]);
    }
    putVec3(payload + p2_bigtreasure_save::kPayloadOffsetLouieDropVel,
            data.cargo.louieVelocity);

    putU32(out + p2_bigtreasure_save::kRecordSize - p2_bigtreasure_save::kChecksumSize,
           p2_bigtreasure_save_crc32(out, p2_bigtreasure_save::kRecordSize
                                              - p2_bigtreasure_save::kChecksumSize));
    *outSize = p2_bigtreasure_save::kRecordSize;
    return true;
}

bool p2_bigtreasure_save_decode(const std::uint8_t* data, std::size_t size,
                                P2BigTreasureSaveData& out)
{
    if (!data || size != p2_bigtreasure_save::kRecordSize) {
        return false;
    }
    if (getU32(data + p2_bigtreasure_save::kHeaderOffsetMagic)
        != p2_bigtreasure_save::kMagic) {
        return false;
    }
    if (getU16(data + p2_bigtreasure_save::kHeaderOffsetVersion)
        != p2_bigtreasure_save::kSchemaVersion) {
        return false;
    }
    if (getU16(data + p2_bigtreasure_save::kHeaderOffsetRecordSize)
        != p2_bigtreasure_save::kRecordSize) {
        return false;
    }
    if (getU32(data + p2_bigtreasure_save::kHeaderOffsetPayloadSize)
        != p2_bigtreasure_save::kPayloadSize) {
        return false;
    }
    const std::uint32_t stored =
        getU32(data + p2_bigtreasure_save::kRecordSize - p2_bigtreasure_save::kChecksumSize);
    if (stored != p2_bigtreasure_save_crc32(data, p2_bigtreasure_save::kRecordSize
                                                      - p2_bigtreasure_save::kChecksumSize)) {
        return false;
    }

    const std::uint8_t* payload = data + p2_bigtreasure_save::kHeaderSize;
    // Reserved bytes are written as zero and must stay zero (fail-closed).
    if (getU8(payload + p2_bigtreasure_save::kPayloadOffsetReserved0) != 0
        || getU8(payload + p2_bigtreasure_save::kPayloadOffsetPoolReserved0) != 0
        || getU8(payload + p2_bigtreasure_save::kPayloadOffsetPoolReserved1) != 0
        || getU8(payload + p2_bigtreasure_save::kPayloadOffsetCargoReserved) != 0
        || getU8(payload + p2_bigtreasure_save::kPayloadOffsetCargoReserved + 1) != 0) {
        return false;
    }

    P2BigTreasureSaveData parsed;
    const std::uint8_t attachedMask =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetAttachedMask);
    if (attachedMask & static_cast<std::uint8_t>(~kWeaponMask)) {
        return false;
    }
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        parsed.weaponAttached[i] = (attachedMask & (1u << i)) != 0;
    }
    const std::uint8_t louieAttached =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetLouieAttached);
    if (louieAttached > 1u) {
        return false;
    }
    parsed.louieAttached = louieAttached != 0;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        parsed.weaponHealth[i] =
            getF32(payload + p2_bigtreasure_save::kPayloadOffsetWeaponHealth + 4 * i);
    }

    const std::uint8_t phase = getU8(payload + p2_bigtreasure_save::kPayloadOffsetPhase);
    if (!validPhase(phase)) {
        return false;
    }
    parsed.phase = static_cast<P2BigTreasurePhase>(phase);
    const std::int8_t chosen = static_cast<std::int8_t>(
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetChosenWeapon));
    if (chosen < -1 || chosen >= P2BTWEAPON_Count) {
        return false;
    }
    parsed.chosenWeapon = chosen;
    const std::uint8_t awaiting =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetAwaitingPick);
    if (awaiting > 1u) {
        return false;
    }
    parsed.awaitingWeaponPick = awaiting != 0;
    const std::uint8_t pending =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetPendingNext);
    if (!validPhase(pending)) {
        return false;
    }
    parsed.pendingNext = static_cast<P2BigTreasurePhase>(pending);
    const std::uint8_t waiting =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetWaitingForIK);
    if (waiting > 1u) {
        return false;
    }
    parsed.waitingForIK = waiting != 0;
    parsed.stateTimer = getF32(payload + p2_bigtreasure_save::kPayloadOffsetStateTimer);

    const std::uint8_t startedMask =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetPoolStartedMask);
    if (startedMask & static_cast<std::uint8_t>(~kWeaponMask)) {
        return false;
    }
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        parsed.poolStarted[i] = (startedMask & (1u << i)) != 0;
        parsed.poolInFlight[i] =
            getU8(payload + p2_bigtreasure_save::kPayloadOffsetPoolInFlight + i);
    }
    parsed.elecMaxNodes =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetElecMaxNodes);

    const std::uint8_t droppedMask =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetDroppedMask);
    if (droppedMask & static_cast<std::uint8_t>(~kWeaponMask)) {
        return false;
    }
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        parsed.cargo.weaponDropped[i] = (droppedMask & (1u << i)) != 0;
    }
    const std::uint8_t louieDropped =
        getU8(payload + p2_bigtreasure_save::kPayloadOffsetLouieDropped);
    if (louieDropped > 1u) {
        return false;
    }
    parsed.cargo.louieDropped = louieDropped != 0;
    for (int i = 0; i < P2BTWEAPON_Count; ++i) {
        parsed.cargo.weaponVelocity[i] = getVec3(
            payload + p2_bigtreasure_save::kPayloadOffsetWeaponDropVel + 12 * i);
    }
    parsed.cargo.louieVelocity =
        getVec3(payload + p2_bigtreasure_save::kPayloadOffsetLouieDropVel);

    if (!p2_bigtreasure_save_validate(parsed)) {
        return false;
    }
    out = parsed;
    return true;
}

bool p2_bigtreasure_save_capture(const P2BigTreasureOwnership& ownership,
                                 const P2BigTreasureFsm& fsm,
                                 const P2BigTreasureAttackPools& pools,
                                 const P2BigTreasureDroppedCargo& cargo,
                                 std::uint8_t* out, std::size_t outCapacity,
                                 std::size_t* outSize)
{
    P2BigTreasureSaveData data;
    p2_bigtreasure_save_capture_state(ownership, fsm, pools, cargo, data);
    return p2_bigtreasure_save_encode(data, out, outCapacity, outSize);
}

bool p2_bigtreasure_save_restore(const std::uint8_t* data, std::size_t size,
                                 P2BigTreasureOwnership& ownership,
                                 P2BigTreasureFsm& fsm,
                                 P2BigTreasureAttackPools& pools,
                                 P2BigTreasureDroppedCargo& cargo)
{
    P2BigTreasureSaveData dataSnapshot;
    if (!p2_bigtreasure_save_decode(data, size, dataSnapshot)) {
        return false;
    }
    return p2_bigtreasure_save_apply_state(dataSnapshot, ownership, fsm, pools, cargo);
}

std::uint32_t p2_bigtreasure_save_crc32(const std::uint8_t* data, std::size_t size)
{
    std::uint32_t crc = 0xFFFFFFFFu;
    for (std::size_t i = 0; i < size; ++i) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; ++bit) {
            const std::uint32_t mask = 0u - (crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}
