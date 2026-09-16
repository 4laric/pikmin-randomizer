#pragma once

#include <cstdint>

// Generic engine-free held-object/drop/carry provider for treasure
// consumers (issue #614, lane provider-held-object-api).
//
// Mirrors the proven #577 bomb-payload pattern: a generational-handle pool
// with an engine-free lifecycle core and a thin host seam. The core manages
// attach/follow/detach/release/reset with exactly-once accounting. Reward
// credit is NEVER granted here: on release the provider records a
// P2HeldObjectRelease naming the carrier/item tokens, and the HOST grants
// it through the EXISTING delivery/receipt host
// (pc_p2_receipt_host_grant / pc_p2_delivery_host_deliver), reporting the
// outcome back with confirmReward. No second ledger and no divergent
// treasure implementation exist in this module.
//
// Reuse survey (documented here instead of a second divergent carry):
//   * The only carry code in the tree is cave-specific
//     (muse-cave50 pc_p2_cave_carry.*) or family receipt fixtures
//     (#578 Sokkuri79, #585 ElecBug28); neither is a generic provider.
//   * Retail Game::Pellet carry runs on the P2 engine and cannot run here.
//   * Family FSMs own receiver/vulnerability behavior; this pool owns only
//     the hold/follow/drop/release lifecycle records bound to
//     host-verified carrier tokens.
// Real actor pickup/drop animation itself needs engine/family changes and
// is NOT included here; family consumers keep their own FSMs, and any
// shared touch needs explicit owner review (see
// docs/PIKMIN2_HELD_OBJECT_PROVIDER.md). Nothing here claims gameplay
// acceptance.
//
// Engine-free boundary: this header and its .cpp compile with -Ipc_port
// only (cstdint). This module never enumerates creatures, never touches
// files or ledgers, and prints nothing (no fake log evidence is possible
// from here).

struct P2HeldObjectVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

// Generational handle. generation==0 is never issued and always invalid,
// so reset()/slot-reuse can never resurrect a stale handle.
struct P2HeldObjectHandle {
    std::uint32_t slot = 0;
    std::uint32_t generation = 0;
};

inline bool p2_held_object_handle_valid(P2HeldObjectHandle handle)
{
    return handle.generation != 0;
}

enum class P2HeldObjectPhase { Free, Attached, Dropped, Released };

// How a carry ended, for host routing (mirrors the detach/drop vocabulary
// consumers already use; none of these grant reward by themselves).
enum class P2HeldObjectDetachReason { Dropped, Thrown, CarrierDied, ItemLost };

inline const char* p2_held_object_detach_reason_name(P2HeldObjectDetachReason reason)
{
    switch (reason) {
    case P2HeldObjectDetachReason::Dropped: return "dropped";
    case P2HeldObjectDetachReason::Thrown: return "thrown";
    case P2HeldObjectDetachReason::CarrierDied: return "carrier-died";
    case P2HeldObjectDetachReason::ItemLost: return "item-lost";
    }
    return "dropped";
}

// One released carry, for the host to credit through the existing receipt
// host. needsReward is true only for a natural delivery release; the host
// maps (carrierToken, itemToken) to receipt keys
// (seed, reward "treasure:<item>", slot <carrier>, encounter "held-release")
// and records the grant outcome with confirmReward.
struct P2HeldObjectRelease {
    std::uint64_t carrierToken = 0;
    std::uint64_t itemToken = 0;
    P2HeldObjectVec3 position;
    P2HeldObjectVec3 velocity;
    bool needsReward = false;
    // Tri-state host confirmation: -1 unset, 0 denied/error, 1 granted.
    int rewardGranted = -1;
};

class P2HeldObjectPool {
public:
    static constexpr int kMaxHeld = 8;

    P2HeldObjectPool();
    explicit P2HeldObjectPool(int capacity);

    // Interruption/reset/re-entry: releases every record and retires every
    // outstanding handle (epoch advance). No release is recorded.
    void reset();

    // Attach: binds one held-object lifecycle to a host-verified live
    // carrier token and item token at the current joint position. Fails
    // (invalid handle) on pool exhaustion, a duplicate live carrier token,
    // a zero carrier/item token, or a non-finite joint position - with no
    // partial state. The host guarantees both tokens name real objects.
    P2HeldObjectHandle attach(std::uint64_t carrierToken, std::uint64_t itemToken,
                              const P2HeldObjectVec3& jointPosition);

    // True only for a handle whose slot+generation still names a live
    // (Attached or Dropped) record. Released/Free records and
    // epoch-retired handles are not live.
    bool isLive(P2HeldObjectHandle handle) const;

    // Rides the carrier's animated joint while Attached; Dropped records
    // keep their rest position. Rejects non-finite positions with no state
    // change; returns false unless Attached.
    bool followJoint(P2HeldObjectHandle handle, const P2HeldObjectVec3& jointPosition);

    // Detach/drop while Attached: records the drop velocity and moves to
    // Dropped. Exactly-once: a second detach for the same record fails and
    // is counted as suppressed. Returns false unless Attached.
    bool detach(P2HeldObjectHandle handle, const P2HeldObjectVec3& velocity,
                P2HeldObjectDetachReason reason);

    // Carrier died while Attached: the item drops in place (zero velocity)
    // with reason CarrierDied. Returns false unless Attached.
    bool onCarrierDeath(P2HeldObjectHandle handle);

    // Item vanished while the carrier lives: releases the record WITHOUT
    // reward (needsReward=false). Returns false unless Attached.
    bool onItemLost(P2HeldObjectHandle handle);

    // Delivery release while Dropped: records exactly ONE release event
    // (needsReward=true) for host credit. Exactly-once: a second release
    // for the same record fails and is counted as suppressed. Returns
    // false unless Dropped.
    bool release(P2HeldObjectHandle handle);

    // Host reports its existing-receipt-host grant outcome for a Released
    // record. Single-set: the first confirmation wins; later ones fail and
    // are counted as suppressed. Returns false unless Released.
    bool confirmReward(P2HeldObjectHandle handle, bool granted);

    // A recorded release is queryable until reset() or slot reuse.
    bool hasRelease(P2HeldObjectHandle handle) const;
    const P2HeldObjectRelease& lastRelease(P2HeldObjectHandle handle) const;
    void clearRelease(P2HeldObjectHandle handle);

    P2HeldObjectPhase phase(P2HeldObjectHandle handle) const;
    std::uint64_t carrierToken(P2HeldObjectHandle handle) const;
    std::uint64_t itemToken(P2HeldObjectHandle handle) const;
    P2HeldObjectVec3 position(P2HeldObjectHandle handle) const;
    P2HeldObjectVec3 velocity(P2HeldObjectHandle handle) const;

    int capacity() const;
    int activeCount() const;
    int suppressedCount() const;
    int releaseCount() const;

private:
    struct Record {
        bool used = false;
        std::uint32_t generation = 0;
        P2HeldObjectPhase phase = P2HeldObjectPhase::Free;
        std::uint64_t carrierToken = 0;
        std::uint64_t itemToken = 0;
        P2HeldObjectVec3 position;
        P2HeldObjectVec3 velocity;
        bool hasRelease = false;
        P2HeldObjectRelease release;
    };

    bool resolve(P2HeldObjectHandle handle, const Record*& out) const;
    bool resolve(P2HeldObjectHandle handle, Record*& out);

    static bool finite(const P2HeldObjectVec3& v);

    int mCapacity = 0;
    std::uint32_t mEpoch = 1;
    Record mRecords[kMaxHeld];
    int mSuppressed = 0;
    int mReleases = 0;
};