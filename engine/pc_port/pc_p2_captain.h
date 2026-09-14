#pragma once
#include "pc_p2_captain_policy.h"
#include "pc_p2_squad_policy.h"
#include <cmath>
#include <cstdint>

// Lane 12 engine-facing captain / squad ownership host adapter (#130).
//
// pc_p2_captain_policy.h is the stable two-captain contract captor families
// build against. This file is the seam that binds that contract to a concrete
// engine without taking an engine dependency:
//
//   * P2CaptainHostOps is the set of engine facts the adapter needs (captain
//     handle, health, Pikmin identity, Piki::mNavi ownership, squad
//     enumeration). pc_p2_captain.cpp implements it against the live P1
//     Navi / PikiMgr globals; the standalone adapter test binds doubles.
//   * P2CaptainAdapter is the engine-free driver: it owns the ownership table
//     and P2CaptainPolicy, adopts the live squad, and mirrors captain
//     captures and captor-held actors back into the engine callbacks.
//
// Current-port reality (single captain) is deliberate and bounded:
//   * NaviMgr has exactly one Navi (`NaviMgr::getNavi()`), created with
//     `Navi::mNaviID == 0`; there is no NaviMgr::getActiveNavi /
//     getAliveOrima / getDeadOrima / mNaviDeadFlags.
//   * Navi health is the inherited `Creature::mHealth` (Navi.h includes
//     Creature.h; `Navi::mHealth` is Creature's, not a Navi member).
//   * Piki ownership is `Piki::mNavi` (Piki.h:318).
// So this adapter binds slot 0 (P2CaptainA) and leaves slot 1 absent. That is
// not a shortcut: the contract's zero-control guard means capture of the only
// captain and switchActive(1) must be refused, exactly as the source refuses
// to strand the player. A real second captain requires engine changes listed
// in docs/PIKMIN2_CAPTAIN_SQUAD_CONTRACT.md; until then this is slot-0 only.

// Opaque engine handles (Navi*, Piki*). Never dereferenced by the adapter.
using P2CaptainHandle = void*;
using P2PikiHandle = void*;

// Upper bound on one enumeration/adoption pass. The P1 field cap is far lower.
constexpr int P2_CAPTAIN_ADOPT_CAPACITY = 256;

struct P2CaptainHostOps {
    void* context = nullptr;

    // Captain slot -> live captain object, or null when the slot is absent.
    P2CaptainHandle (*captainAt)(void* context, int slot) = nullptr;
    float (*getHealth)(void* context, P2CaptainHandle captain) = nullptr;
    void (*setHealth)(void* context, P2CaptainHandle captain, float health) = nullptr;

    // Stable nonzero actor id for a Pikmin (or carried actor); 0 if unknown.
    std::uint32_t (*actorId)(void* context, P2PikiHandle actor) = nullptr;
    // Current owning captain slot, or P2CaptainInvalid when free/unowned.
    int (*ownerSlot)(void* context, P2PikiHandle actor) = nullptr;
    // Write the actor's owner slot back into the engine (Piki::mNavi).
    void (*setOwnerSlot)(void* context, P2PikiHandle actor, int slot) = nullptr;

    // Enumerate live squad actors for adoption. Returns the count written to
    // `out` (truncated to capacity), or -1 on failure.
    int (*enumerate)(void* context, P2PikiHandle* out, int capacity) = nullptr;

    // Optional engine notifications. These are how the policy's switch/capture
    // selection is routed back into the engine's own active/dead bookkeeping
    // (NaviMgr::setActiveNavi / informOrimaDead). They are nullable so existing
    // engine-double tests keep binding without them.
    void (*notifyActive)(void* context, int slot)   = nullptr;
    void (*notifyKnockout)(void* context, int slot) = nullptr;
};

// One per loaded scene. Bind, setup(), then let captor families drive it.
class P2CaptainAdapter {
    P2CaptainOwnershipTable mTable;
    P2CaptainPolicy mPolicy;
    P2CaptainHostOps mHost;
    bool mBound = false;

    bool liveCaptain(int slot, P2CaptainHandle& out) const
    {
        out = nullptr;
        if (!mHost.captainAt || slot < 0 || slot >= P2CaptainCount) return false;
        out = mHost.captainAt(mHost.context, slot);
        return out != nullptr;
    }

    void notifyActive(int slot)
    {
        if (mHost.notifyActive) mHost.notifyActive(mHost.context, slot);
    }
    void notifyKnockout(int slot)
    {
        if (mHost.notifyKnockout) mHost.notifyKnockout(mHost.context, slot);
    }

public:
    // Requires every callback. A partially-bound adapter is refused rather
    // than silently skipping engine writes.
    bool bind(const P2CaptainHostOps& ops)
    {
        if (mBound || !ops.captainAt || !ops.getHealth || !ops.setHealth || !ops.actorId
            || !ops.ownerSlot || !ops.setOwnerSlot || !ops.enumerate)
            return false;
        mHost  = ops;
        mPolicy = P2CaptainPolicy();
        if (!mPolicy.bind(&mTable)) return false;
        mBound = true;
        return true;
    }

    bool bound() const { return mBound; }
    P2CaptainPolicy& policy() { return mPolicy; }
    const P2CaptainPolicy& policy() const { return mPolicy; }

    // Read-only view of the shared ownership table, for consumers/tests.
    bool ownsActor(std::uint32_t actor) const { return mTable.isOwned(actor); }
    int ownerOfActor(std::uint32_t actor) const { return mTable.ownerOf(actor); }

    // The live shared ownership table, so a sibling lane can claim/release
    // through the same domain (used by the lane-11 Bulbmin whistle handoff).
    // Null until bind(); callers must not retain it past teardown().
    P2CaptainOwnershipTable* ownershipTable() { return mBound ? &mTable : nullptr; }
    const P2CaptainOwnershipTable* ownershipTable() const { return mBound ? &mTable : nullptr; }

    // Register every present captain (slot 0 only on this port) and adopt the
    // squad's existing Piki::mNavi ownership. Returns false when no captain is
    // present. Safe to call once per scene after bind().
    bool setup()
    {
        if (!mBound) return false;
        int presentCount = 0;
        for (int c = 0; c < P2CaptainCount; ++c) {
            P2CaptainHandle handle = nullptr;
            if (liveCaptain(c, handle)) {
                float hp = mHost.getHealth(mHost.context, handle);
                if (!std::isfinite(hp) || hp < 0.0f) return false;
                if (!mPolicy.configure(c, hp, true)) return false;
                ++presentCount;
            } else {
                if (!mPolicy.configure(c, 0.0f, false)) return false;
            }
        }
        if (presentCount == 0) return false;
        adoptSquad();
        return true;
    }

    // Claim every enumerated actor whose current engine owner is a captain.
    // Returns the number adopted, or -1 on enumeration failure.
    int adoptSquad()
    {
        if (!mBound) return -1;
        P2PikiHandle actors[P2_CAPTAIN_ADOPT_CAPACITY];
        int count = mHost.enumerate(mHost.context, actors, P2_CAPTAIN_ADOPT_CAPACITY);
        if (count < 0) return -1;
        int adopted = 0;
        for (int i = 0; i < count; ++i) {
            std::uint32_t id = mHost.actorId(mHost.context, actors[i]);
            if (!id) continue;
            int owner = mHost.ownerSlot(mHost.context, actors[i]);
            if (!P2CaptainOwnershipTable::isCaptain(owner)) continue;
            if (mPolicy.claim(owner, id)) ++adopted;
        }
        return adopted;
    }

    // Push the policy's ownership back into the engine (Piki::mNavi). Used
    // after a captain capture transfers a squad, and by reload/teardown.
    bool syncOwnership()
    {
        if (!mBound) return false;
        P2PikiHandle actors[P2_CAPTAIN_ADOPT_CAPACITY];
        int count = mHost.enumerate(mHost.context, actors, P2_CAPTAIN_ADOPT_CAPACITY);
        if (count < 0) return false;
        for (int i = 0; i < count; ++i) {
            std::uint32_t id = mHost.actorId(mHost.context, actors[i]);
            if (!id) continue;
            int owner = mTable.ownerOf(id);
            mHost.setOwnerSlot(mHost.context, actors[i],
                               P2CaptainOwnershipTable::isCaptain(owner) ? owner : P2CaptainInvalid);
        }
        return true;
    }

    // --- Health (engine is authoritative for the live Navi value) ---

    float health(int captain) const { return mPolicy.health(captain); }

    bool setHealth(int captain, float value)
    {
        if (!mBound || !P2CaptainOwnershipTable::isCaptain(captain) || !std::isfinite(value)
            || value < 0.0f || !mPolicy.present(captain))
            return false;
        P2CaptainHandle handle = nullptr;
        if (liveCaptain(captain, handle)) mHost.setHealth(mHost.context, handle, value);
        return mPolicy.setHealth(captain, value);
    }

    // Pull the live engine health back into the policy without changing phase.
    bool refresh()
    {
        if (!mBound) return false;
        for (int c = 0; c < P2CaptainCount; ++c) {
            P2CaptainHandle handle = nullptr;
            if (!liveCaptain(c, handle)) continue;
            float hp = mHost.getHealth(mHost.context, handle);
            if (!std::isfinite(hp) || hp < 0.0f) return false;
            if (!mPolicy.setHealth(c, hp)) return false;
        }
        return true;
    }

    // --- Captain-level control ---

    int activeCaptain() const { return mPolicy.activeCaptain(); }

    bool switchActive(int target)
    {
        if (!mBound || !mPolicy.switchActive(target)) return false;
        notifyActive(target);
        return true;
    }

    // Captor ingest of a captain. On success the captive's squad is
    // transferred in-policy and mirrored into the engine, and control has moved
    // to the survivor.
    bool captureCaptain(int captain, std::uint64_t captorEpoch)
    {
        if (!mBound || !mPolicy.capture(captain, captorEpoch)) return false;
        syncOwnership();
        notifyActive(mPolicy.activeCaptain());
        return true;
    }

    bool releaseCaptain(int captain, std::uint64_t captorEpoch)
    {
        if (!mBound) return false;
        return mPolicy.releaseCaptured(captain, captorEpoch);
    }

    // Source Navi damage/knockout. Returns true only when the hit knocked the
    // captain out. The downed captain's actors are freed in-policy, mirrored to
    // the engine, and the engine is told the captain is down and which captain
    // now has control. Callers that already applied the damage in the engine
    // should keep the engine authoritative and use refresh()/setHealth();
    // this drives the shared policy and the engine active/dead bookkeeping.
    bool damageCaptain(int captain, float amount)
    {
        if (!mBound || !mPolicy.damage(captain, amount)) return false;
        syncOwnership();
        notifyKnockout(captain);
        notifyActive(mPolicy.activeCaptain());
        return true;
    }

    // --- Per-captain squad split (lane 12 two-captain follow-up) ---

    // Move up to `count` of `from`'s adopted actors to `to` and mirror the new
    // owner into the engine (Piki::mNavi). Returns the moved actor ids.
    std::vector<std::uint32_t> splitSquad(int from, int to, std::size_t count)
    {
        std::vector<std::uint32_t> moved;
        if (!mBound) return moved;
        moved = mPolicy.splitSquad(from, to, count);
        if (!moved.empty()) syncOwnership();
        return moved;
    }

    // Move exactly the named adopted actors; mirrors ownership into the engine.
    std::size_t transferSquad(int from, int to, const std::uint32_t* actors,
                              std::size_t count)
    {
        if (!mBound) return 0;
        std::size_t moved = mPolicy.transferSquad(from, to, actors, count);
        if (moved) syncOwnership();
        return moved;
    }

    // --- Captor-held actors (Pikmin / carried items) ---

    bool captureActor(std::uint64_t captorEpoch, P2PikiHandle actor)
    {
        if (!mBound) return false;
        std::uint32_t id = mHost.actorId(mHost.context, actor);
        if (!id || !mPolicy.captureActor(captorEpoch, id)) return false;
        mHost.setOwnerSlot(mHost.context, actor, P2CaptainInvalid);
        return true;
    }

    bool releaseActor(std::uint64_t captorEpoch, P2PikiHandle actor, int toCaptain)
    {
        if (!mBound) return false;
        std::uint32_t id = mHost.actorId(mHost.context, actor);
        if (!id || !mPolicy.releaseActor(captorEpoch, id, toCaptain)) return false;
        int owner = mTable.ownerOf(id);
        mHost.setOwnerSlot(mHost.context, actor,
                           P2CaptainOwnershipTable::isCaptain(owner) ? owner : P2CaptainInvalid);
        return true;
    }

    // Captor death/interruption: free everything it held and mirror the freed
    // state (whistle-reclaimable, never deleted) into the engine.
    std::vector<std::uint32_t> dropAllCaptured(std::uint64_t captorEpoch)
    {
        std::vector<std::uint32_t> out;
        if (!mBound) return out;
        out = mPolicy.dropAllCaptured(captorEpoch);
        syncOwnership();
        return out;
    }

    std::size_t captiveCount() const { return mPolicy.captiveCount(); }

    // --- Lifecycle ---

    // Scene reload/checkpoint. Clears transient captures, restores each captive
    // to its previous captain and re-reads live health; owned actors are
    // conserved.
    bool reload()
    {
        if (!mBound) return false;
        mPolicy.reload();
        refresh();
        return syncOwnership();
    }

    // Drop the engine binding and free all policy bookkeeping. Does not touch
    // the live Navi/Piki objects (they are owned by the engine). After this the
    // adapter may be bound again with bind().
    void teardown()
    {
        if (!mBound) return;
        mPolicy.cancel();
        mTable.invalidateDomain();
        mPolicy = P2CaptainPolicy();
        mHost  = P2CaptainHostOps();
        mBound = false;
    }
};

// ---------------------------------------------------------------------------
// Engine glue, implemented in pc_p2_captain.cpp against the live P1
// Navi/NaviMgr/PikiMgr. This is opt-in: nothing here runs unless a caller
// invokes setup_from_navi_mgr(). The engine-free adapter test above does not
// reference these symbols, so it does not link pc_p2_captain.cpp.
namespace pc_p2_captain {

// Bind a process-wide adapter to the live naviMgr and adopt the current squad.
// Returns false when there is no live NaviMgr/Navi. Idempotent: a second call
// returns true without re-adopting.
bool setup_from_navi_mgr();

// Drop the live binding (call before scene/manager teardown).
void teardown();

// The live adapter after a successful setup_from_navi_mgr(), else null.
P2CaptainAdapter* adapter();

float health(int captain);
bool set_health(int captain, float value);
bool capture_captain(int captain, std::uint64_t captorEpoch);
bool release_captain(int captain, std::uint64_t captorEpoch);
bool switch_active(int captain);
bool reload();
int adopt_squad();

// Lane 12 second-captain queries (#130). `has_second_captain` is false on the
// single-captain port; `other_captain` is the GET_OTHER_NAVI mapping.
bool has_second_captain();
int other_captain(int captain);

// Captor-held squad actor (Piki*) operations. `piki` is a live Piki*.
bool capture_actor(std::uint64_t captorEpoch, P2PikiHandle piki);
bool release_actor(std::uint64_t captorEpoch, P2PikiHandle piki, int toCaptain);
std::vector<std::uint32_t> drop_captured(std::uint64_t captorEpoch);

// Lane 12 two-captain follow-up (#130): move up to `count` adopted Pikmin from
// `from` to `to`, mirroring Piki::mNavi. Returns the moved actor ids. With one
// captain the policy refuses the split, so this is a no-op in default play.
std::vector<std::uint32_t> split_squad(int from, int to, std::size_t count);

// Drive the inactive captain's follow state from the live Navi positions. This
// is the narrow engine hook called each frame by NaviMgr::update(); it returns
// immediately unless a real second Navi already exists, so single-captain play
// is byte-identical. The decision itself is engine-free (P2SquadFollowPolicy);
// this only marshals positions/velocity into the inactive Navi.
void update_inactive_captain_follow();

// Last phase produced by update_inactive_captain_follow(), for diagnostics and
// the standalone gate. Idle while no second captain exists.
P2FollowPhase inactive_captain_follow_phase();

} // namespace pc_p2_captain
