#include "pc_p2_bomb_payload_actor.h"

#include <cmath>

namespace {

bool finiteVec(const P2BombSaraiVec3& value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z)
        && std::fabs(value.x) <= 100000.0f && std::fabs(value.y) <= 100000.0f
        && std::fabs(value.z) <= 100000.0f;
}

bool finiteBlastConfig(const P2BombPayloadConfig& config)
{
    return std::isfinite(config.blastRadius) && config.blastRadius > 0.0f
        && std::isfinite(config.blastHalfHeight) && config.blastHalfHeight >= 0.0f
        && std::isfinite(config.tekiDamage) && config.tekiDamage >= 0.0f
        && std::isfinite(config.naviPikiDamage) && config.naviPikiDamage >= 0.0f;
}

} // namespace

P2BombPayloadPool::P2BombPayloadPool() : mCapacity(0) {}

P2BombPayloadPool::P2BombPayloadPool(int capacity)
    : mCapacity(capacity > 0 ? capacity : 0)
{
}

void P2BombPayloadPool::reset()
{
    // Retire every outstanding handle: bump the epoch and mark all slots
    // free. Generations are re-seeded from the new epoch on next birth, so
    // no pre-reset handle can ever resolve again.
    ++mEpoch;
    if (mEpoch == 0) mEpoch = 1;
    for (int i = 0; i < kMaxPayloads; ++i) {
        mRecords[i] = Record{};
    }
    mSuppressed = 0;
    mBlasts = 0;
}

bool P2BombPayloadPool::resolve(P2BombPayloadHandle handle, const Record*& out) const
{
    if (handle.generation == 0 || handle.slot >= static_cast<std::uint32_t>(kMaxPayloads)) {
        return false;
    }
    const Record& record = mRecords[handle.slot];
    if (!record.used || record.generation != handle.generation) {
        return false;
    }
    out = &record;
    return true;
}

bool P2BombPayloadPool::resolve(P2BombPayloadHandle handle, Record*& out)
{
    const Record* read = nullptr;
    if (!resolve(handle, read)) {
        return false;
    }
    out = const_cast<Record*>(read);
    return true;
}

P2BombPayloadHandle P2BombPayloadPool::birth(std::uint64_t carrierToken,
                                             const P2BombSaraiVec3& jointPosition,
                                             const P2BombPayloadConfig& config)
{
    if (carrierToken == 0 || !finiteVec(jointPosition) || !finiteBlastConfig(config)) {
        return P2BombPayloadHandle{};
    }
    int live = 0;
    for (int i = 0; i < kMaxPayloads; ++i) {
        if (!mRecords[i].used) {
            continue;
        }
        ++live;
        // One payload per live carrier (OtakaraBase single mCarrier guard).
        if (mRecords[i].phase == P2BombPayloadPhase::Carried
            && mRecords[i].carrierToken == carrierToken) {
            return P2BombPayloadHandle{};
        }
    }
    if (live >= mCapacity) {
        return P2BombPayloadHandle{};
    }
    for (int i = 0; i < kMaxPayloads; ++i) {
        Record& record = mRecords[i];
        if (record.used) {
            continue;
        }
        record.used = true;
        // Generation folds in the epoch so cross-reset reuse can never
        // collide with a retired handle, even on counter wrap.
        std::uint32_t next = record.generation + mEpoch;
        if (next == 0) {
            next = mEpoch != 0 ? mEpoch : 1;
        }
        record.generation = next;
        record.phase = P2BombPayloadPhase::Carried;
        record.carrierToken = carrierToken;
        record.position = jointPosition;
        record.config = config;
        record.hasBlast = false;
        record.blast = P2BombSaraiBlastEvent{};
        return P2BombPayloadHandle{static_cast<std::uint32_t>(i), record.generation};
    }
    return P2BombPayloadHandle{};
}

bool P2BombPayloadPool::isLive(P2BombPayloadHandle handle) const
{
    const Record* record = nullptr;
    return resolve(handle, record) && record->phase == P2BombPayloadPhase::Carried;
}

bool P2BombPayloadPool::followJoint(P2BombPayloadHandle handle,
                                    const P2BombSaraiVec3& jointPosition)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2BombPayloadPhase::Carried) {
        return false;
    }
    if (!finiteVec(jointPosition)) {
        return false;
    }
    record->position = jointPosition;
    return true;
}

bool P2BombPayloadPool::onPayloadLost(P2BombPayloadHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2BombPayloadPhase::Carried) {
        return false;
    }
    // No blast: the payload is gone, not detonated. The host kills the
    // carrier (OtakaraBaseState bomb-carry guard); the record is released
    // so the carrier token can be re-armed by a later birth.
    record->phase = P2BombPayloadPhase::Lost;
    return true;
}

bool P2BombPayloadPool::onCarrierDeath(P2BombPayloadHandle handle,
                                       P2BombSaraiCarrierFn carrierFn, void* carrierContext)
{
    return detonate(handle, P2BombPayloadTrigger::Death, carrierFn, carrierContext);
}

bool P2BombPayloadPool::detonate(P2BombPayloadHandle handle, P2BombPayloadTrigger trigger,
                                 P2BombSaraiCarrierFn carrierFn, void* carrierContext)
{
    (void)trigger;
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2BombPayloadPhase::Carried) {
        ++mSuppressed;
        return false;
    }
    if (record->hasBlast) {
        ++mSuppressed;
        return false;
    }
    const bool valid = carrierFn != nullptr && carrierFn(carrierContext, record->carrierToken);
    P2BombSaraiBlastEvent blast;
    blast.center = record->position;
    blast.radius = record->config.blastRadius;
    blast.halfHeight = record->config.blastHalfHeight;
    blast.tekiDamage = record->config.tekiDamage;
    blast.naviPikiDamage = record->config.naviPikiDamage;
    blast.carrierToken = record->carrierToken;
    blast.hasCarrier = record->carrierToken != 0;
    blast.carrierValid = valid;
    record->blast = blast;
    record->hasBlast = true;
    record->phase = P2BombPayloadPhase::Detonated;
    ++mBlasts;
    return true;
}

bool P2BombPayloadPool::hasBlast(P2BombPayloadHandle handle) const
{
    const Record* record = nullptr;
    return resolve(handle, record) && record->hasBlast;
}

const P2BombSaraiBlastEvent& P2BombPayloadPool::lastBlast(P2BombPayloadHandle handle) const
{
    static const P2BombSaraiBlastEvent kEmpty;
    const Record* record = nullptr;
    if (!resolve(handle, record) || !record->hasBlast) {
        return kEmpty;
    }
    return record->blast;
}

void P2BombPayloadPool::clearBlast(P2BombPayloadHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record)) {
        return;
    }
    record->hasBlast = false;
    record->blast = P2BombSaraiBlastEvent{};
}

P2BombPayloadPhase P2BombPayloadPool::phase(P2BombPayloadHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return P2BombPayloadPhase::Free;
    }
    return record->phase;
}

std::uint64_t P2BombPayloadPool::carrierToken(P2BombPayloadHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return 0;
    }
    return record->carrierToken;
}

P2BombSaraiVec3 P2BombPayloadPool::position(P2BombPayloadHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return P2BombSaraiVec3{};
    }
    return record->position;
}

int P2BombPayloadPool::capacity() const
{
    return mCapacity;
}

int P2BombPayloadPool::activeCount() const
{
    int count = 0;
    for (int i = 0; i < kMaxPayloads; ++i) {
        if (mRecords[i].used && mRecords[i].phase == P2BombPayloadPhase::Carried) {
            ++count;
        }
    }
    return count;
}

int P2BombPayloadPool::suppressedCount() const
{
    return mSuppressed;
}

int P2BombPayloadPool::blastCount() const
{
    return mBlasts;
}
