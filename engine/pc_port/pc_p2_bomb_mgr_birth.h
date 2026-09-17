#pragma once

#include <cstdint>

#include "pc_p2_bomb_payload_actor.h"

// Port Bomb::Mgr birth seam for EnemyID_Bomb payloads (issue #616, provider
// lane; consumer #573). SINGLE manager: this module OWNS one #577
// P2BombPayloadPool as its lifecycle engine and adds the birth seam the #577
// handoff explicitly excluded. Nothing here duplicates the pool, the blast
// policy (pc_p2_bombsarai_blast.h) or lane-22's numeric payloadId stub (which
// this manager replaces with live bomb-actor records).
//
// Source anchors (read-only decomp @632af937, never reimplemented here):
//   * Game::Bomb::Mgr (bombMgr.cpp:10-35) is an EnemyMgrBase whose
//     getEnemyTypeID() is EnemyID_Bomb (36) and whose birth() delegates to
//     the base manager birth.
//   * Game::Bomb::Obj::getEnemyTypeID() is EnemyID_Bomb (Bomb.h:82-85).
//   * OtakaraBase initBombOtakara captures the Bomb on the `otakara` joint
//     and the bomb-carry states kill the carrier if the payload disappears.
//   * BombOtakara.cpp:42-87 delegates contact/press/death/earthquake to the
//     payload Bomb; bombState.cpp:140-198 is the blast volume/attribution.
// Host facts (P1 engine, TEKI_TypeCount == 35, no TEKI_Bomb): a host Bomb body
// cannot be birthed through the P1 teki roster, so the port Bomb::Mgr births
// real tracked Bomb entities (source_id=36) bound to LIVE host carrier actors
// at the otakara-joint position. A born record is a live actor handle with a
// jointly-followed position and #577 lifecycle ? never a numeric stub and
// never an injected marker: every P2_BOMB_MGR_* line below is printed from a
// production manager path.
//
// Engine-free boundary: Section 1 (manager core) compiles with -Ipc_port
// only; define P2_BOMB_MGR_BIRTH_NO_HOST to exclude Section 2 (host binding)
// and prove the boundary by building the standalone test. Section 2 mirrors
// the family seam shape (setup/update/forget/reset) for the #186 shared-hook
// contract; the replacement-main fixture drives it directly.

// Retail source identity birthed through this manager.
constexpr int P2_BOMB_MGR_SOURCE_ID = 36;

// Generational born-actor handle. generation==0 is never issued, so reset()
// slot-reuse can never resurrect a stale handle (same discipline as #577).
struct P2BombMgrHandle {
    std::uint32_t slot = 0;
    std::uint32_t generation = 0;
};

inline bool p2_bomb_mgr_handle_valid(P2BombMgrHandle handle)
{
    return handle.generation != 0;
}

enum class P2BombMgrPhase { Free, Born, Lost, Detonated };

// ---- Section 1: engine-free manager core ----

class P2BombMgr {
public:
    static constexpr int kMaxBombs = 8;

    P2BombMgr();
    explicit P2BombMgr(int capacity);

    // Interruption/reset/re-entry: releases every born record, retires every
    // outstanding handle (epoch advance) and resets the owned #577 pool. No
    // blast is emitted. Emits P2_BOMB_MGR_RESET.
    void reset();

    // Carrier registration (sidecar generators). Duplicate registration is
    // idempotent; unregistration of an unknown id is a no-op.
    void registerCarrier(std::uint32_t generator);
    void unregisterCarrier(std::uint32_t generator);
    bool isRegistered(std::uint32_t generator) const;

    // Birth: binds one Bomb actor to a REGISTERED live carrier token at the
    // current otakara-joint position and hands the payload lifecycle to the
    // owned #577 pool. Fails (invalid handle + P2_BOMB_MGR_REJECT) on an
    // unregistered id, a duplicate live birth for the same carrier, a zero
    // carrier token, or a non-finite joint position ? with no partial state.
    // Success emits P2_BOMB_MGR_BIRTH (the natural birth marker).
    P2BombMgrHandle birth(std::uint64_t carrierToken,
                          const P2BombSaraiVec3& jointPosition,
                          const P2BombPayloadConfig& config);

    // True only for a handle whose slot+generation still names a Born record.
    bool isLive(P2BombMgrHandle handle) const;

    // Live born-actor handle for a carrier token, or an invalid handle when
    // no Born record names it. Query only; never creates lifecycle state.
    P2BombMgrHandle findLive(std::uint64_t carrierToken) const;

    // Rides the carrier's otakara joint. Born phase only; rejects non-finite
    // positions with no state change. Emits nothing (positions are logged by
    // the host tick, not per call).
    bool followCarrier(P2BombMgrHandle handle, const P2BombSaraiVec3& jointPosition);

    // Carrier died or vanished while the bomb lives: releases the record
    // WITHOUT a blast (source carrier-kill path) so the id can be re-armed
    // by a later birth. Returns false unless Born. Emits P2_BOMB_MGR_FORGET.
    bool onCarrierGone(P2BombMgrHandle handle);

    // Detonation through the owned pool (exactly-once; duplicates suppressed
    // and counted) then routes the recorded blast with the REAL
    // p2_bombsarai_route_blast against the caller-supplied live receivers.
    // Returns hits written, or -1 on invalid input. Emits
    // P2_BOMB_MGR_BLAST_ROUTED with the hit count and attribution.
    int detonate(P2BombMgrHandle handle, P2BombPayloadTrigger trigger,
                 P2BombSaraiCarrierFn carrierFn, void* carrierContext,
                 const P2BombSaraiReceiver* receivers, int receiverCount,
                 P2BombSaraiRoutedHit* out, int outCapacity);

    // #577 payload handle for the consumer handoff (#573 reads blast state
    // through the pool API, never through manager internals).
    P2BombPayloadHandle payloadHandle(P2BombMgrHandle handle) const;

    P2BombMgrPhase phase(P2BombMgrHandle handle) const;
    std::uint64_t carrierToken(P2BombMgrHandle handle) const;
    P2BombSaraiVec3 position(P2BombMgrHandle handle) const;

    int capacity() const;
    int activeCount() const;
    int suppressedCount() const;
    int blastCount() const;
    int registeredCount() const;

// ---- Section 2: host binding declarations (defined in the .cpp unless
// P2_BOMB_MGR_BIRTH_NO_HOST is set; forward declaration only, so this header
// stays engine-free). These mirror the family seam shape for the #186
// shared-hook contract: tekibteki BTeki::update, doKill/TekiMgr forget path,
// and stage reset. The replacement-main fixture drives them directly.
class BTeki;
P2BombMgr& pc_p2_bomb_mgr_birth_manager();
void pc_p2_bomb_mgr_birth_reset();
void pc_p2_bomb_mgr_birth_setup();
P2BombMgrHandle pc_p2_bomb_mgr_birth_carrier(unsigned generator);
void pc_p2_bomb_mgr_birth_update(BTeki* actor);
void pc_p2_bomb_mgr_birth_forget(BTeki* actor);
bool pc_p2_bomb_mgr_birth_ready();
// ---- Section 3: engine-driven birth arm declarations (lane
// bomb-engine-birth-real-native, #691; defined in the .cpp unless
// P2_BOMB_MGR_BIRTH_NO_HOST is set). Unlike the raw-ID arm, this entry takes
// ONLY a live engine actor: birth is impossible without the engine having
// spawned a live Teki whose generator the sidecar registered. Called from
// engine idle context (never from test drivers); refuses with no state
// change otherwise. Returns true iff a birth record was produced this call.
class Teki;
bool pc_p2_bomb_engine_birth_poll(Teki* actor);

private:
    struct Record {
        bool used = false;
        std::uint32_t generation = 0;
        P2BombMgrPhase phase = P2BombMgrPhase::Free;
        std::uint64_t carrierToken = 0;
        P2BombPayloadHandle payload{};
        P2BombSaraiVec3 position;
    };

    bool resolve(P2BombMgrHandle handle, const Record*& out) const;
    bool resolve(P2BombMgrHandle handle, Record*& out);

    int mCapacity = 0;
    std::uint32_t mEpoch = 1;
    Record mRecords[kMaxBombs];
    std::uint32_t mSlotGen[kMaxBombs] = {};
    std::uint32_t mRegistered[kMaxBombs];
    int mRegisteredCount = 0;
    int mSuppressed = 0;
    int mBlasts = 0;
    P2BombPayloadPool mPool;
};
