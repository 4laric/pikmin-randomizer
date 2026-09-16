#include "pc_p2_held_object.h"

namespace {

bool finiteFloat(float v)
{
    return v == v && v != 1.0f / 0.0f && v != -1.0f / 0.0f;
}

const P2HeldObjectRelease kNoRelease{};

} // namespace

P2HeldObjectPool::P2HeldObjectPool()
    : P2HeldObjectPool(kMaxHeld)
{
}

P2HeldObjectPool::P2HeldObjectPool(int capacity)
{
    if (capacity < 1) {
        capacity = 1;
    }
    if (capacity > kMaxHeld) {
        capacity = kMaxHeld;
    }
    mCapacity = capacity;
}

bool P2HeldObjectPool::finite(const P2HeldObjectVec3& v)
{
    return finiteFloat(v.x) && finiteFloat(v.y) && finiteFloat(v.z);
}

bool P2HeldObjectPool::resolve(P2HeldObjectHandle handle, const Record*& out) const
{
    out = nullptr;
    if (handle.generation == 0 || handle.slot >= static_cast<std::uint32_t>(mCapacity)) {
        return false;
    }
    const Record& record = mRecords[handle.slot];
    if (!record.used || record.generation != handle.generation) {
        return false;
    }
    out = &record;
    return true;
}

bool P2HeldObjectPool::resolve(P2HeldObjectHandle handle, Record*& out)
{
    out = nullptr;
    if (handle.generation == 0 || handle.slot >= static_cast<std::uint32_t>(mCapacity)) {
        return false;
    }
    Record& record = mRecords[handle.slot];
    if (!record.used || record.generation != handle.generation) {
        return false;
    }
    out = &record;
    return true;
}

void P2HeldObjectPool::reset()
{
    for (int i = 0; i < mCapacity; ++i) {
        mRecords[i] = Record{};
    }
    ++mEpoch;
    if (mEpoch == 0) {
        mEpoch = 1;
    }
    mSuppressed = 0;
    mReleases = 0;
}

P2HeldObjectHandle P2HeldObjectPool::attach(std::uint64_t carrierToken, std::uint64_t itemToken,
                                            const P2HeldObjectVec3& jointPosition)
{
    P2HeldObjectHandle bad{};
    if (carrierToken == 0 || itemToken == 0 || !finite(jointPosition)) {
        return bad;
    }
    for (int i = 0; i < mCapacity; ++i) {
        const Record& record = mRecords[i];
        if (record.used && record.phase == P2HeldObjectPhase::Attached &&
            record.carrierToken == carrierToken) {
            return bad;
        }
    }
    for (int i = 0; i < mCapacity; ++i) {
        Record& record = mRecords[i];
        if (record.used) {
            continue;
        }
        record.used = true;
        record.generation = mEpoch++;
        if (mEpoch == 0) {
            mEpoch = 1;
        }
        if (record.generation == 0) {
            record.generation = mEpoch++;
        }
        record.phase = P2HeldObjectPhase::Attached;
        record.carrierToken = carrierToken;
        record.itemToken = itemToken;
        record.position = jointPosition;
        record.velocity = P2HeldObjectVec3{};
        record.hasRelease = false;
        record.release = P2HeldObjectRelease{};
        P2HeldObjectHandle handle{};
        handle.slot = static_cast<std::uint32_t>(i);
        handle.generation = record.generation;
        return handle;
    }
    return bad;
}

bool P2HeldObjectPool::isLive(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return false;
    }
    return record->phase == P2HeldObjectPhase::Attached ||
           record->phase == P2HeldObjectPhase::Dropped;
}

bool P2HeldObjectPool::followJoint(P2HeldObjectHandle handle, const P2HeldObjectVec3& jointPosition)
{
    if (!finite(jointPosition)) {
        return false;
    }
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2HeldObjectPhase::Attached) {
        return false;
    }
    record->position = jointPosition;
    return true;
}

bool P2HeldObjectPool::detach(P2HeldObjectHandle handle, const P2HeldObjectVec3& velocity,
                              P2HeldObjectDetachReason reason)
{
    (void)reason;
    if (!finite(velocity)) {
        return false;
    }
    Record* record = nullptr;
    if (!resolve(handle, record)) {
        return false;
    }
    if (record->phase != P2HeldObjectPhase::Attached) {
        ++mSuppressed;
        return false;
    }
    record->phase = P2HeldObjectPhase::Dropped;
    record->velocity = velocity;
    return true;
}

bool P2HeldObjectPool::onCarrierDeath(P2HeldObjectHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2HeldObjectPhase::Attached) {
        return false;
    }
    record->phase = P2HeldObjectPhase::Dropped;
    record->velocity = P2HeldObjectVec3{};
    return true;
}

bool P2HeldObjectPool::onItemLost(P2HeldObjectHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2HeldObjectPhase::Attached) {
        return false;
    }
    record->phase = P2HeldObjectPhase::Released;
    record->hasRelease = true;
    record->release.carrierToken = record->carrierToken;
    record->release.itemToken = record->itemToken;
    record->release.position = record->position;
    record->release.velocity = P2HeldObjectVec3{};
    record->release.needsReward = false;
    record->release.rewardGranted = -1;
    return true;
}

bool P2HeldObjectPool::release(P2HeldObjectHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record)) {
        return false;
    }
    if (record->phase != P2HeldObjectPhase::Dropped) {
        ++mSuppressed;
        return false;
    }
    if (record->hasRelease) {
        ++mSuppressed;
        return false;
    }
    record->phase = P2HeldObjectPhase::Released;
    record->hasRelease = true;
    record->release.carrierToken = record->carrierToken;
    record->release.itemToken = record->itemToken;
    record->release.position = record->position;
    record->release.velocity = record->velocity;
    record->release.needsReward = true;
    record->release.rewardGranted = -1;
    ++mReleases;
    return true;
}

bool P2HeldObjectPool::confirmReward(P2HeldObjectHandle handle, bool granted)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2HeldObjectPhase::Released ||
        !record->hasRelease) {
        return false;
    }
    if (record->release.rewardGranted != -1) {
        ++mSuppressed;
        return false;
    }
    record->release.rewardGranted = granted ? 1 : 0;
    return true;
}

bool P2HeldObjectPool::hasRelease(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return false;
    }
    return record->hasRelease;
}

const P2HeldObjectRelease& P2HeldObjectPool::lastRelease(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record) || !record->hasRelease) {
        return kNoRelease;
    }
    return record->release;
}

void P2HeldObjectPool::clearRelease(P2HeldObjectHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record)) {
        return;
    }
    record->hasRelease = false;
    record->release = P2HeldObjectRelease{};
}

P2HeldObjectPhase P2HeldObjectPool::phase(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return P2HeldObjectPhase::Free;
    }
    return record->phase;
}

std::uint64_t P2HeldObjectPool::carrierToken(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return 0;
    }
    return record->carrierToken;
}

std::uint64_t P2HeldObjectPool::itemToken(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return 0;
    }
    return record->itemToken;
}

P2HeldObjectVec3 P2HeldObjectPool::position(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return P2HeldObjectVec3{};
    }
    return record->position;
}

P2HeldObjectVec3 P2HeldObjectPool::velocity(P2HeldObjectHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) {
        return P2HeldObjectVec3{};
    }
    return record->velocity;
}

int P2HeldObjectPool::capacity() const
{
    return mCapacity;
}

int P2HeldObjectPool::activeCount() const
{
    int count = 0;
    for (int i = 0; i < mCapacity; ++i) {
        if (mRecords[i].used) {
            ++count;
        }
    }
    return count;
}

int P2HeldObjectPool::suppressedCount() const
{
    return mSuppressed;
}

int P2HeldObjectPool::releaseCount() const
{
    return mReleases;
}