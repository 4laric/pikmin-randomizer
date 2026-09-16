#pragma once

#include <cstdint>

#include "pc_p2_bombsarai_blast.h"

// Real Bomb payload actor birth/lifecycle provider for the BombOtakara93
// consumer (#573). Lane enemy-bomb-payload-provider, issue #577.
//
// Reuse survey (documented here instead of a second divergent Bomb):
//   * The integrated P1 host teki roster (tekinakata.cpp strategy table:
//     Frog, Iwagen, Iwagon, Chappy, Swallow, Mizigen, Qurione, Palm,
//     Collec, Kinoko, Shell, Napkid, Hollec, Pearl, Rocpe, Chappb,
//     Swallob, Frow, Namazu, P2Demon, ...) has NO Bomb type, so no host
//     manager can birth EnemyID_Bomb today.
//   * Retail P2 Game::Bomb (bomb.cpp/bombState.cpp, Bomb.h) cannot run on
//     the P1 engine (different Creature/AI/param/cell systems).
//   * pc_p2_king_policy.h BombPlacement is an explicitly labelled fixture
//     injection, not an actor.
//   * lane-22 BombOtakara carries a numeric payloadId stub (labelled).
// This provider therefore manages payload LIFECYCLE records bound to
// host-verified carrier tokens and publishes the exact seam where a real
// engine-actor birth plugs in (see P2BombPayloadBirthSeam below): the host
// births through its own manager and hands this pool the carrier token
// plus the otakara-joint position. Real actor birth itself needs a
// shared-owner engine change (teki birth path) and is NOT included here;
// it is recorded as a shared-review request in
// docs/PIKMIN2_BOMB_PAYLOAD_PROVIDER.md. Nothing here claims gate1/3
// runtime closure.
//
// Engine-free boundary: this header and its .cpp compile with -Ipc_port
// only (cstdint plus the shared engine-free bombsarai policy headers).
// Blast volume/attribution logic is REUSED, never duplicated: detonation
// records a P2BombSaraiBlastEvent and the host routes it with the real
// p2_bombsarai_route_blast. This module never enumerates creatures,
// never stimulates InteractBomb, and prints nothing (no fake log
// evidence is possible from here).

// Pinned retail blast defaults for the otakara payload (lane-20 values,
// Bomb.h fp02 default): radius mAttackRadius fp22 90, teki fp01 500,
// navi/piki fp24 10, half-height fp02 50.
struct P2BombPayloadConfig {
    float blastRadius = 90.0f;
    float blastHalfHeight = 50.0f;
    float tekiDamage = 500.0f;
    float naviPikiDamage = 10.0f;
};

// Detonation triggers, mirroring the otakara payload contract
// (OtakaraBase delegates contact/press/death/earthquake to the payload;
// BombOtakara.cpp:42-87).
enum class P2BombPayloadTrigger { Contact, Press, Death, Earthquake };

inline const char* p2_bomb_payload_trigger_name(P2BombPayloadTrigger trigger)
{
    switch (trigger) {
    case P2BombPayloadTrigger::Contact: return "contact";
    case P2BombPayloadTrigger::Press: return "press";
    case P2BombPayloadTrigger::Death: return "death";
    case P2BombPayloadTrigger::Earthquake: return "earthquake";
    }
    return "contact";
}

// Generational handle. generation==0 is never issued and always invalid,
// so reset()/slot-reuse can never resurrect a stale handle.
struct P2BombPayloadHandle {
    std::uint32_t slot = 0;
    std::uint32_t generation = 0;
};

inline bool p2_bomb_payload_handle_valid(P2BombPayloadHandle handle)
{
    return handle.generation != 0;
}

enum class P2BombPayloadPhase { Free, Carried, Lost, Detonated };

// Follows the source otakara-joint carry contract (OtakaraBase.cpp:649-677:
// initBombOtakara captures the Bomb on the `otakara` joint and sets
// mCarrier; bomb-carry states kill the carrier if the payload pointer
// disappears, OtakaraBaseState.cpp:761-763,816-819,880-882).
class P2BombPayloadPool {
public:
    static constexpr int kMaxPayloads = 8;

    P2BombPayloadPool();
    explicit P2BombPayloadPool(int capacity);

    // Interruption/reset/re-entry: releases every record and retires every
    // outstanding handle (epoch advance). No blast is emitted.
    void reset();

    // Birth: binds one payload lifecycle to a host-verified live carrier
    // token at the current otakara-joint position. Fails (invalid handle)
    // on pool exhaustion, a duplicate live carrier token, a zero carrier
    // token, or a non-finite joint position — with no partial state.
    // The host guarantees the carrier token names a real actor; the
    // engine-actor birth seam itself is documented above, not implemented.
    P2BombPayloadHandle birth(std::uint64_t carrierToken,
                              const P2BombSaraiVec3& jointPosition,
                              const P2BombPayloadConfig& config);

    // True only for a handle whose slot+generation still names a Carried
    // record. Detonated/Lost/Free records and epoch-retired handles are
    // not live.
    bool isLive(P2BombPayloadHandle handle) const;

    // Rides the carrier's animated joint (bomb.cpp:23-44: the host moves
    // the constrained bomb with the joint). Carried phase only; rejects
    // non-finite positions with no state change.
    bool followJoint(P2BombPayloadHandle handle, const P2BombSaraiVec3& jointPosition);

    // Payload disappeared while the carrier lives (OtakaraBaseState kill
    // path): releases the record WITHOUT a blast and reports the loss so
    // the host can kill the carrier. Returns false unless Carried.
    bool onPayloadLost(P2BombPayloadHandle handle);

    // Carrier died: death-trigger detonation (exactly-once, same rules as
    // detonate with TriggerDeath).
    bool onCarrierDeath(P2BombPayloadHandle handle, P2BombSaraiCarrierFn carrierFn,
                        void* carrierContext);

    // Real detonation: first call records exactly ONE blast event and
    // releases the carry; any further call for the same record is
    // suppressed (duplicate-detonation can never double-fire). Carrier
    // liveness for attribution is resolved at blast time through the
    // host callback (source mCarrier==nullptr fallback when unconfirmed).
    bool detonate(P2BombPayloadHandle handle, P2BombPayloadTrigger trigger,
                  P2BombSaraiCarrierFn carrierFn, void* carrierContext);

    // A recorded blast is queryable until reset() or slot reuse; the host
    // routes it with p2_bombsarai_route_blast and applies InteractBomb.
    bool hasBlast(P2BombPayloadHandle handle) const;
    const P2BombSaraiBlastEvent& lastBlast(P2BombPayloadHandle handle) const;
    void clearBlast(P2BombPayloadHandle handle);

    P2BombPayloadPhase phase(P2BombPayloadHandle handle) const;
    std::uint64_t carrierToken(P2BombPayloadHandle handle) const;
    P2BombSaraiVec3 position(P2BombPayloadHandle handle) const;

    int capacity() const;
    int activeCount() const;
    int suppressedCount() const;
    int blastCount() const;

private:
    struct Record {
        bool used = false;
        std::uint32_t generation = 0;
        P2BombPayloadPhase phase = P2BombPayloadPhase::Free;
        std::uint64_t carrierToken = 0;
        P2BombSaraiVec3 position;
        P2BombPayloadConfig config;
        bool hasBlast = false;
        P2BombSaraiBlastEvent blast;
    };

    bool resolve(P2BombPayloadHandle handle, const Record*& out) const;
    bool resolve(P2BombPayloadHandle handle, Record*& out);

    int mCapacity = 0;
    std::uint32_t mEpoch = 1;
    Record mRecords[kMaxPayloads];
    int mSuppressed = 0;
    int mBlasts = 0;
};
