#include "pc_p2_bomb_mgr_birth.h"

#include <cmath>
#include <cstdio>

// ---- Section 1: engine-free manager core (always compiled) ----

namespace {

bool mgrFiniteVec(const P2BombSaraiVec3& v)
{
    return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z);
}

bool validConfig(const P2BombPayloadConfig& c)
{
    return std::isfinite(c.blastRadius) && c.blastRadius > 0.0f
        && std::isfinite(c.blastHalfHeight) && c.blastHalfHeight > 0.0f
        && std::isfinite(c.tekiDamage) && std::isfinite(c.naviPikiDamage);
}

} // namespace

P2BombMgr::P2BombMgr() : P2BombMgr(kMaxBombs)
{
}

P2BombMgr::P2BombMgr(int capacity)
    : mCapacity(capacity < 1 ? 1 : (capacity > kMaxBombs ? kMaxBombs : capacity))
    , mPool(mCapacity)
{
    for (int i = 0; i < kMaxBombs; ++i) mRegistered[i] = 0;
}

void P2BombMgr::reset()
{
    for (auto& record : mRecords) record = Record{};
    for (int i = 0; i < kMaxBombs; ++i) mRegistered[i] = 0;
    mRegisteredCount = 0;
    mSuppressed = 0;
    mBlasts = 0;
    ++mEpoch;
    if (mEpoch == 0) mEpoch = 1;
    mPool.reset();
    std::printf("P2_BOMB_MGR_RESET epoch=%u\n", mEpoch);
    std::fflush(stdout);
}

void P2BombMgr::registerCarrier(std::uint32_t generator)
{
    if (!generator) return;
    for (int i = 0; i < mRegisteredCount; ++i) {
        if (mRegistered[i] == generator) return;
    }
    if (mRegisteredCount < kMaxBombs) mRegistered[mRegisteredCount++] = generator;
}

void P2BombMgr::unregisterCarrier(std::uint32_t generator)
{
    for (int i = 0; i < mRegisteredCount; ++i) {
        if (mRegistered[i] == generator) {
            mRegistered[i] = mRegistered[--mRegisteredCount];
            return;
        }
    }
}

bool P2BombMgr::isRegistered(std::uint32_t generator) const
{
    for (int i = 0; i < mRegisteredCount; ++i) {
        if (mRegistered[i] == generator) return true;
    }
    return false;
}

bool P2BombMgr::resolve(P2BombMgrHandle handle, const Record*& out) const
{
    if (handle.generation == 0 || handle.slot >= std::uint32_t(mCapacity)) return false;
    const Record& record = mRecords[handle.slot];
    if (!record.used || record.generation != handle.generation) return false;
    out = &record;
    return true;
}

bool P2BombMgr::resolve(P2BombMgrHandle handle, Record*& out)
{
    const Record* found = nullptr;
    if (!resolve(handle, found)) return false;
    out = const_cast<Record*>(found);
    return true;
}

P2BombMgrHandle P2BombMgr::birth(std::uint64_t carrierToken,
                                 const P2BombSaraiVec3& jointPosition,
                                 const P2BombPayloadConfig& config)
{
    const P2BombMgrHandle invalid{};
    if (!carrierToken || carrierToken > 0xffffffffULL) {
        std::printf("P2_BOMB_MGR_REJECT reason=bad_token\n");
        std::fflush(stdout);
        return invalid;
    }
    const auto generator = static_cast<std::uint32_t>(carrierToken);
    if (!isRegistered(generator)) {
        std::printf("P2_BOMB_MGR_REJECT generator=%u reason=unregistered\n", generator);
        std::fflush(stdout);
        return invalid;
    }
    for (const auto& record : mRecords) {
        if (record.used && record.phase == P2BombMgrPhase::Born
            && record.carrierToken == carrierToken) {
            std::printf("P2_BOMB_MGR_REJECT generator=%u reason=duplicate\n", generator);
            std::fflush(stdout);
            return invalid;
        }
    }
    if (!mgrFiniteVec(jointPosition) || !validConfig(config)) {
        std::printf("P2_BOMB_MGR_REJECT generator=%u reason=invalid\n", generator);
        std::fflush(stdout);
        return invalid;
    }
    // Slots free ONLY on reset(): the owned #577 pool keeps Lost/Detonated
    // records queryable until reset, so the manager mirrors that lifetime.
    // (A carrier killed after its payload is lost never re-arms the same
    // record; a new carrier bind or reset() starts the next lifecycle.)
    for (int slot = 0; slot < mCapacity; ++slot) {
        Record& record = mRecords[slot];
        if (record.used) continue;
        const P2BombPayloadHandle payload = mPool.birth(carrierToken, jointPosition, config);
        if (!p2_bomb_payload_handle_valid(payload)) {
            std::printf("P2_BOMB_MGR_REJECT generator=%u reason=pool\n", generator);
            std::fflush(stdout);
            return invalid;
        }
        // Per-slot generation: reusing a Lost/Detonated slot retires the old
        // handle, so a stale handle can never name the new record.
        if (++mSlotGen[slot] == 0) ++mSlotGen[slot];
        record.used = true;
        record.generation = mSlotGen[slot];
        record.phase = P2BombMgrPhase::Born;
        record.carrierToken = carrierToken;
        record.payload = payload;
        record.position = jointPosition;
        std::printf("P2_BOMB_MGR_BIRTH generator=%u source_id=%d slot=%d generation=%u\n",
                    generator, P2_BOMB_MGR_SOURCE_ID, slot, mSlotGen[slot]);
        std::fflush(stdout);
        return P2BombMgrHandle{std::uint32_t(slot), mSlotGen[slot]};
    }
    std::printf("P2_BOMB_MGR_REJECT generator=%u reason=exhausted\n", generator);
    std::fflush(stdout);
    return invalid;
}

bool P2BombMgr::isLive(P2BombMgrHandle handle) const
{
    const Record* record = nullptr;
    return resolve(handle, record) && record->phase == P2BombMgrPhase::Born
        && mPool.isLive(record->payload);
}

P2BombMgrHandle P2BombMgr::findLive(std::uint64_t carrierToken) const
{
    for (int slot = 0; slot < mCapacity; ++slot) {
        const Record& record = mRecords[slot];
        if (record.used && record.phase == P2BombMgrPhase::Born
            && record.carrierToken == carrierToken
            && mPool.isLive(record.payload)) {
            return P2BombMgrHandle{std::uint32_t(slot), record.generation};
        }
    }
    return P2BombMgrHandle{};
}

bool P2BombMgr::followCarrier(P2BombMgrHandle handle, const P2BombSaraiVec3& jointPosition)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2BombMgrPhase::Born) return false;
    if (!mgrFiniteVec(jointPosition)) return false;
    if (!mPool.followJoint(record->payload, jointPosition)) return false;
    record->position = jointPosition;
    return true;
}

bool P2BombMgr::onCarrierGone(P2BombMgrHandle handle)
{
    Record* record = nullptr;
    if (!resolve(handle, record) || record->phase != P2BombMgrPhase::Born) return false;
    mPool.onPayloadLost(record->payload);
    record->phase = P2BombMgrPhase::Lost;
    std::printf("P2_BOMB_MGR_FORGET generator=%u\n", std::uint32_t(record->carrierToken));
    std::fflush(stdout);
    return true;
}

int P2BombMgr::detonate(P2BombMgrHandle handle, P2BombPayloadTrigger trigger,
                        P2BombSaraiCarrierFn carrierFn, void* carrierContext,
                        const P2BombSaraiReceiver* receivers, int receiverCount,
                        P2BombSaraiRoutedHit* out, int outCapacity)
{
    Record* record = nullptr;
    if (!resolve(handle, record)) return -1;
    if (record->phase != P2BombMgrPhase::Born) {
        ++mSuppressed;
        std::printf("P2_BOMB_MGR_DETONATE_SUPPRESSED generator=%u\n",
                    std::uint32_t(record->carrierToken));
        std::fflush(stdout);
        return 0;
    }
    if (!mPool.detonate(record->payload, trigger, carrierFn, carrierContext)) {
        ++mSuppressed;
        std::printf("P2_BOMB_MGR_DETONATE_SUPPRESSED generator=%u\n",
                    std::uint32_t(record->carrierToken));
        std::fflush(stdout);
        return 0;
    }
    record->phase = P2BombMgrPhase::Detonated;
    const P2BombSaraiBlastEvent& blast = mPool.lastBlast(record->payload);
    const int hits = p2_bombsarai_route_blast(blast, receivers, receiverCount, out, outCapacity);
    if (hits >= 0) ++mBlasts;
    std::printf("P2_BOMB_MGR_BLAST_ROUTED generator=%u trigger=%s hits=%d\n",
                std::uint32_t(record->carrierToken),
                p2_bomb_payload_trigger_name(trigger), hits);
    std::fflush(stdout);
    return hits;
}

P2BombPayloadHandle P2BombMgr::payloadHandle(P2BombMgrHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) return P2BombPayloadHandle{};
    return record->payload;
}

P2BombMgrPhase P2BombMgr::phase(P2BombMgrHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) return P2BombMgrPhase::Free;
    return record->phase;
}

std::uint64_t P2BombMgr::carrierToken(P2BombMgrHandle handle) const
{
    const Record* record = nullptr;
    if (!resolve(handle, record)) return 0;
    return record->carrierToken;
}

P2BombSaraiVec3 P2BombMgr::position(P2BombMgrHandle handle) const
{
    const Record* record = nullptr;
    static const P2BombSaraiVec3 origin{};
    if (!resolve(handle, record)) return origin;
    return record->position;
}

int P2BombMgr::capacity() const { return mCapacity; }

int P2BombMgr::activeCount() const
{
    int count = 0;
    for (const auto& record : mRecords) {
        if (record.used && record.phase == P2BombMgrPhase::Born) ++count;
    }
    return count;
}

int P2BombMgr::suppressedCount() const { return mSuppressed; }
int P2BombMgr::blastCount() const { return mBlasts; }
int P2BombMgr::registeredCount() const { return mRegisteredCount; }

#ifndef P2_BOMB_MGR_BIRTH_NO_HOST
// ---- Section 2: host binding (port TekiMgr path; excluded from the
// engine-free standalone build by P2_BOMB_MGR_BIRTH_NO_HOST) ----
#include "teki.h"
#include "Generator.h"
#include "PikiMgr.h"
#include "Piki.h"
#include "NaviMgr.h"
#include "system.h"
#include <fstream>
#include <set>
#include <string>

namespace {

P2BombMgr sManager;
bool sReady = false;
float sLogTimer = 0.0f;

Teki* findCarrierActor(std::uint32_t generator)
{
    if (!tekiMgr) return nullptr;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (actor && actor->mGenerator && actor->mGenerator->_70 == generator) return actor;
    }
    return nullptr;
}

bool carrierLiveCallback(void* context, std::uint64_t token)
{
    (void)context;
    if (!token || token > 0xffffffffULL) return false;
    Teki* actor = findCarrierActor(static_cast<std::uint32_t>(token));
    return actor && actor->isAlive();
}

} // namespace

P2BombMgr& pc_p2_bomb_mgr_birth_manager() { return sManager; }

void pc_p2_bomb_mgr_birth_reset()
{
    sManager.reset();
    sReady = false;
    sLogTimer = 0.0f;
}

void pc_p2_bomb_mgr_birth_setup()
{
    pc_p2_bomb_mgr_birth_reset();
    std::ifstream bindings("p2-bomb-mgr-birth.txt");
    if (!bindings) return; // inert without the sidecar
    std::string word;
    int count = 0;
    if (!(bindings >> word >> count) || word != "P2_BOMB_MGR_BIRTH_1" || count < 1 || count > 8) {
        std::abort();
    }
    for (int i = 0; i < count; ++i) {
        unsigned long id = 0;
        if (!(bindings >> id) || !id || id > 0xffffffffUL) std::abort();
        sManager.registerCarrier(static_cast<std::uint32_t>(id));
    }
    if (bindings >> word) std::abort();
    if (!tekiMgr) return;
    // Reject identity overlap before binding: a carrier id must name exactly
    // one live host actor and no other family may own it.
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        if (!sManager.isRegistered(actor->mGenerator->_70)) continue;
        const unsigned gen = actor->mGenerator->_70;
        const Vector3f pos = actor->getPosition();
        std::printf("P2_BOMB_MGR_BIND generator=%u source_id=%d visual_only=0\n",
                    gen, P2_BOMB_MGR_SOURCE_ID);
        std::printf("P2_ENEMY_READY species=Bomb native_family=BombMgr generator=%u x=%.7f y=%.7f z=%.7f "
                    "health=%.1f behavior=native source_FSM=bomb_wait reward=blast\n",
                    gen, pos.x, pos.y, pos.z, actor->mHealth);
    }
    sReady = true;
}

P2BombMgrHandle pc_p2_bomb_mgr_birth_carrier(unsigned generator)
{
    if (!sReady || !generator) return P2BombMgrHandle{};
    Teki* actor = findCarrierActor(generator);
    if (!actor || !actor->isAlive()) {
        std::printf("P2_BOMB_MGR_REJECT generator=%u reason=no_actor\n", generator);
        std::fflush(stdout);
        return P2BombMgrHandle{};
    }
    const Vector3f pos = actor->getPosition();
    P2BombSaraiVec3 joint;
    joint.x = pos.x;
    joint.y = pos.y;
    joint.z = pos.z;
    P2BombPayloadConfig config;
    return sManager.birth(generator, joint, config);
}

void pc_p2_bomb_mgr_birth_update(BTeki* actor)
{
    // Per-actor entry for the tekibteki update hook (shared contract): follows
    // the live bomb on a registered carrier, releases it when the carrier is
    // gone. No-op for unregistered actors; ordinary P1 play is untouched.
    if (!sReady || !actor || !actor->mGenerator) return;
    const unsigned generator = actor->mGenerator->_70;
    if (!sManager.isRegistered(generator)) return;
    const P2BombMgrHandle handle = sManager.findLive(generator);
    if (!p2_bomb_mgr_handle_valid(handle)) return;
    if (!actor->isAlive()) {
        sManager.onCarrierGone(handle);
        return;
    }
    const Vector3f pos = actor->getPosition();
    P2BombSaraiVec3 joint;
    joint.x = pos.x;
    joint.y = pos.y;
    joint.z = pos.z;
    sManager.followCarrier(handle, joint);
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (dt > 0.0f && dt <= 0.5f) {
        sLogTimer += dt;
        if (sLogTimer >= 1.0f) {
            sLogTimer = 0.0f;
            std::printf("P2_BOMB_MGR_POS generator=%u x=%.2f y=%.2f z=%.2f\n",
                        generator, pos.x, pos.y, pos.z);
            std::fflush(stdout);
        }
    }
}

void pc_p2_bomb_mgr_birth_forget(BTeki* actor)
{
    // Lane-07 seam consumer (tekibteki doKill / TekiMgr reset path): release
    // the bomb whose carrier is being unbound.
    if (!sReady || !actor || !actor->mGenerator) return;
    const P2BombMgrHandle handle = sManager.findLive(actor->mGenerator->_70);
    if (p2_bomb_mgr_handle_valid(handle)) sManager.onCarrierGone(handle);
}

bool pc_p2_bomb_mgr_birth_ready() { return sReady; }
// ---- Section 3: engine-driven birth arm (lane bomb-engine-birth-real-native,
// #691). Construction + spawn through the engine surface: the ONLY entry takes
// a live engine actor, never a raw ID (unlike test-driver or allowlist arms,
// this cannot birth without the engine having spawned a live Teki whose
// generator the sidecar registered). Called from engine idle context; every
// refusal leaves zero state change. Retail engine surface consumed read-only:
// generalEnemyMgr creates Bomb::Mgr / BombOtakara::Mgr per enemy ID
// (pikmin2-research src/plugProjectYamashitaU/generalEnemyMgr.cpp:322-323,
// :421-422 @632af9378); TekiMgr::newTeki + birth() allocate and init live
// actors; TekiInfo::read resolves caveinfo names under EFlag_CanBeSpawned.
bool pc_p2_bomb_engine_birth_poll(Teki* actor)
{
    if (!sReady || !actor || !actor->mGenerator) {
        return false;
    }
    if (!actor->isAlive()) {
        std::printf("P2_BOMB_ENGINE_BIRTH_REFUSE reason=actor_dead\n");
        std::fflush(stdout);
        return false;
    }
    const unsigned gen = actor->mGenerator->_70;
    if (!gen || !sManager.isRegistered(gen)) {
        return false;
    }
    if (p2_bomb_mgr_handle_valid(sManager.findLive(gen))) {
        std::printf("P2_BOMB_ENGINE_BIRTH_REFUSE generator=%u reason=duplicate\n", gen);
        std::fflush(stdout);
        return false;
    }
    const Vector3f pos = actor->getPosition();
    if (!std::isfinite(pos.x) || !std::isfinite(pos.y) || !std::isfinite(pos.z)) {
        std::printf("P2_BOMB_ENGINE_BIRTH_REFUSE generator=%u reason=position\n", gen);
        std::fflush(stdout);
        return false;
    }
    P2BombSaraiVec3 joint;
    joint.x = pos.x;
    joint.y = pos.y;
    joint.z = pos.z;
    P2BombPayloadConfig config;
    const P2BombMgrHandle handle = sManager.birth(
        static_cast<std::uint64_t>(gen), joint, config);
    if (!p2_bomb_mgr_handle_valid(handle)) {
        return false;
    }
    std::printf("P2_BOMB_ENGINE_BIRTH generator=%u source_id=%d slot=%u generation=%u "
                "x=%.3f y=%.3f z=%.3f health=%.1f engine_driven=1\n",
                gen, P2_BOMB_MGR_SOURCE_ID, handle.slot, handle.generation,
                pos.x, pos.y, pos.z, actor->mHealth);
    std::fflush(stdout);
    return true;
}
#endif // P2_BOMB_MGR_BIRTH_NO_HOST
