#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <unordered_map>
#include <vector>

// P2 captain / captive / squad ownership contract (#130), lane 12 of
// docs/PIKMIN2_IMPLEMENTATION_FANOUT.md.
//
// This is the stable interface captor and squad-consumer families build
// against: Greater Jellyfloat captain ingest (#243), Bumbling Snitchbug /
// Demon forced drop (#215-#242) and Ranging Bloyster captain dependency
// (#174). Captor FSMs and actor-local effects stay with their family modules;
// this header owns only the two-captain identity, health/knockout, held-actor
// ownership and capture/release boundary.
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0):
//   include/Game/Navi.h          Navi::mNaviIndex, mHealth, mInvincibleTimer,
//                                GET_OTHER_NAVI(navi) == 1 - mNaviIndex
//                                NaviMgr::getActiveNavi/getAliveOrima/
//                                getDeadOrima/informOrimaDead, mDeadNavis,
//                                mNaviDeadFlags[2]
//   include/Game/Piki.h          Piki::mNavi                 (_2C4)
//   include/Game/gamePlayData.h  mNaviLifeMax[2]
//   include/Game/NaviState.h     capture/knockout/follow states
//   src/plugProjectNishimuraU/OniKurage.cpp
//                                mSuckedNavis[2], suckNavi(), isFinishNaviSuck()
//   src/plugProjectNishimuraU/Kurage.cpp
//                                flickNearbyNavi() (Lesser Jellyfloat knockback)
//
// Invariants enforced by this contract (see the policy test):
//   1. Exactly one Active captain whenever any present captain is not Down.
//   2. An ownership holder (Pikmin or carried actor) has at most one captain.
//   3. Switch, capture, knockout and scene reload never lose or duplicate an
//      owned actor: every owned actor is either still owned by one captain or
//      explicitly released to the free set, never both.
//   4. Captures are epoch-qualified. A stale captor (previous holder of the
//      same manager slot or pointer) can never release another captor's
//      capture.

enum P2CaptainIndex {
    P2CaptainA = 0, // Olimar
    P2CaptainB = 1, // Louie, or President after substitution
    P2CaptainCount = 2,
    P2CaptainInvalid = -1,
};

// GET_OTHER_NAVI in source.
inline int p2_other_captain(int captain) {
    return (captain == P2CaptainA || captain == P2CaptainB)
        ? (1 - captain)
        : P2CaptainInvalid;
}

inline bool p2_is_captain(int captain) {
    return captain == P2CaptainA || captain == P2CaptainB;
}

enum class P2CaptainPhase {
    Idle,     // present, alive, not the controlled captain
    Active,   // present, alive, controlled
    Captured, // held by a captor actor (OniKurage mSuckedNavis)
    Down,     // knocked out / dead this scene
};

struct P2CaptainSlot {
    P2CaptainPhase phase = P2CaptainPhase::Idle;
    bool present = true; // President substitution can add the second slot
    float health = 0.0f;
    float healthMax = 0.0f;
    std::uint64_t captureEpoch = 0; // nonzero only while Captured
};

// Shared holder table: actor id -> captain index. 0 means free/unowned.
// One table per loaded scene so two captors or two squads can never both own
// the same actor. Invalidate the whole domain before any manager-slot or
// pointer reuse; ownership epochs never wrap or repeat.
class P2CaptainOwnershipTable {
    std::unordered_map<std::uint32_t, int> owner;

public:
    void invalidateDomain() { owner.clear(); }
    bool isOwned(std::uint32_t actor) const { return owner.count(actor) != 0; }
    int ownerOf(std::uint32_t actor) const {
        auto it = owner.find(actor);
        return it == owner.end() ? P2CaptainInvalid : it->second;
    }
    bool tryClaim(std::uint32_t actor, int captain) {
        if (!actor || !isCaptain(captain) || owner.count(actor)) return false;
        owner[actor] = captain;
        return true;
    }
    void release(std::uint32_t actor, int captain) {
        auto it = owner.find(actor);
        if (it != owner.end() && it->second == captain) owner.erase(it);
    }
    std::vector<std::uint32_t> releaseAll(int captain) {
        std::vector<std::uint32_t> out;
        for (auto it = owner.begin(); it != owner.end();) {
            if (it->second == captain) {
                out.push_back(it->first);
                it = owner.erase(it);
            } else {
                ++it;
            }
        }
        return out;
    }
    // Move every actor owned by `from` to `to` without dropping any. If `to`
    // is invalid the actors are freed instead (knockout/stranding).
    std::vector<std::uint32_t> transferAll(int from, int to) {
        std::vector<std::uint32_t> moved;
        for (auto& entry : owner) {
            if (entry.second != from) continue;
            moved.push_back(entry.first);
            if (isCaptain(to)) entry.second = to;
        }
        if (!isCaptain(to)) {
            for (std::uint32_t actor : moved) owner.erase(actor);
        }
        return moved;
    }
    std::size_t ownedCount() const { return owner.size(); }
    std::size_t ownedBy(int captain) const {
        std::size_t n = 0;
        for (const auto& entry : owner)
            if (entry.second == captain) ++n;
        return n;
    }
    // Actors owned by `captain`, ascending by id so a split is deterministic
    // across runs regardless of hash-table iteration order.
    std::vector<std::uint32_t> actorsOwnedBy(int captain) const {
        std::vector<std::uint32_t> out;
        for (const auto& entry : owner)
            if (entry.second == captain) out.push_back(entry.first);
        std::sort(out.begin(), out.end());
        return out;
    }

    static bool isCaptain(int captain) {
        return captain == P2CaptainA || captain == P2CaptainB;
    }
};

// One instance per loaded scene. Bind it to the shared table before use.
class P2CaptainPolicy {
    P2CaptainOwnershipTable* table = nullptr;
    P2CaptainSlot slots[P2CaptainCount];
    int active = P2CaptainInvalid;

    // Captor-held actors (Snitchbug, Demon, Jellyfloat). An actor is either
    // captain-owned or captor-held, never both; `previousOwner` lets a reload
    // restore it without loss.
    struct CaptiveRecord {
        std::uint64_t captorEpoch = 0;
        int previousOwner = P2CaptainInvalid;
    };
    std::unordered_map<std::uint32_t, CaptiveRecord> captives;

    bool aliveIdle(int captain) const {
        if (!p2_is_captain(captain)) return false;
        const P2CaptainSlot& s = slots[captain];
        return s.present && s.phase != P2CaptainPhase::Captured
            && s.phase != P2CaptainPhase::Down;
    }

    // Pick the fallback controlled captain after the active one leaves the
    // field. Prefers a present, alive Idle captain. Returns Invalid only when
    // no captain can be controlled (both Down / absent).
    void selectFallback() {
        if (aliveIdle(active)) return;
        for (int c = 0; c < P2CaptainCount; ++c) {
            if (aliveIdle(c)) {
                for (int o = 0; o < P2CaptainCount; ++o)
                    if (o != c && slots[o].phase == P2CaptainPhase::Active)
                        slots[o].phase = P2CaptainPhase::Idle;
                slots[c].phase = P2CaptainPhase::Active;
                active = c;
                return;
            }
        }
        active = P2CaptainInvalid;
    }

public:
    bool bind(P2CaptainOwnershipTable* domain) {
        if (bound() || !domain) return false;
        table = domain;
        slots[P2CaptainA] = P2CaptainSlot{};
        slots[P2CaptainB] = P2CaptainSlot{};
        active = P2CaptainInvalid;
        return true;
    }
    bool bound() const { return table != nullptr; }

    // Register a captain slot with its source maximum life. `present=false`
    // keeps a slot reserved but not yet in the field (President substitution).
    bool configure(int captain, float healthMax, bool present) {
        if (!bound() || !P2CaptainOwnershipTable::isCaptain(captain)
            || !std::isfinite(healthMax) || healthMax < 0.0f)
            return false;
        slots[captain].healthMax = healthMax;
        slots[captain].health = healthMax;
        slots[captain].present = present;
        slots[captain].phase = present ? P2CaptainPhase::Idle
                                       : P2CaptainPhase::Down;
        slots[captain].captureEpoch = 0;
        if (present && active == P2CaptainInvalid) {
            slots[captain].phase = P2CaptainPhase::Active;
            active = captain;
        }
        return true;
    }

    int activeCaptain() const { return active; }
    P2CaptainPhase phase(int captain) const {
        return P2CaptainOwnershipTable::isCaptain(captain)
            ? slots[captain].phase : P2CaptainPhase::Down;
    }
    bool present(int captain) const {
        return P2CaptainOwnershipTable::isCaptain(captain) && slots[captain].present;
    }
    float health(int captain) const {
        return P2CaptainOwnershipTable::isCaptain(captain) ? slots[captain].health : 0.0f;
    }
    bool controllable(int captain) const { return aliveIdle(captain); }

    // Raw health override for the engine-facing host adapter
    // (pc_p2_captain.h), which is authoritative for the live Navi value. This
    // does not change phase: use damage() for knockout and revive() for
    // coming back. Refuses absent slots and non-finite/negative values.
    bool setHealth(int captain, float health) {
        if (!bound() || !P2CaptainOwnershipTable::isCaptain(captain)
            || !slots[captain].present || !std::isfinite(health) || health < 0.0f)
            return false;
        slots[captain].health = health;
        return true;
    }

    // Source NaviMgr::getActiveNavi switch. Refuses a captain that is absent,
    // captured or down. Owned actors stay with their owners; no transfer and
    // no loss.
    bool switchActive(int target) {
        if (!bound() || !aliveIdle(target) || target == active) return false;
        if (p2_is_captain(active) && slots[active].phase == P2CaptainPhase::Active)
            slots[active].phase = P2CaptainPhase::Idle;
        slots[target].phase = P2CaptainPhase::Active;
        active = target;
        return true;
    }

    // Source Navi damage path. Returns true when this hit knocked the captain
    // out. A Down captain releases its controlled actors to the free set and
    // yields control to the surviving captain.
    bool damage(int captain, float amount) {
        if (!bound() || !aliveIdle(captain) || !std::isfinite(amount) || amount < 0.0f)
            return false;
        slots[captain].health -= amount;
        if (slots[captain].health > 0.0f) return false;
        slots[captain].health = 0.0f;
        slots[captain].phase = P2CaptainPhase::Down;
        table->releaseAll(captain);
        selectFallback();
        return true;
    }

    // Captor ingest (OniKurage::suckNavi). `captorEpoch` identifies the captor
    // instance so a stale holder cannot release this capture. Returns false if
    // the captain is already captured/down or if it is the last controllable
    // captain (source never leaves the player with zero control).
    bool capture(int captain, std::uint64_t captorEpoch) {
        if (!bound() || !aliveIdle(captain) || !captorEpoch) return false;
        int other = p2_other_captain(captain);
        if (!controllable(other)) return false;
        slots[captain].phase = P2CaptainPhase::Captured;
        slots[captain].captureEpoch = captorEpoch;
        // Hand the captive's squad to the surviving controlled captain so it
        // is neither lost nor duplicated; the source reassigns mNavi owners.
        table->transferAll(captain, other);
        if (active == captain) {
            slots[other].phase = P2CaptainPhase::Active;
            active = other;
        }
        return true;
    }

    // Captor death or interruption. Epoch must match the active capture; the
    // released captain returns Idle and does not steal control back.
    bool releaseCaptured(int captain, std::uint64_t captorEpoch) {
        if (!bound() || !P2CaptainOwnershipTable::isCaptain(captain)) return false;
        if (slots[captain].phase != P2CaptainPhase::Captured) return false;
        if (!captorEpoch || slots[captain].captureEpoch != captorEpoch) return false;
        slots[captain].phase = P2CaptainPhase::Idle;
        slots[captain].captureEpoch = 0;
        selectFallback();
        return true;
    }

    // Revive a downed captain (source Onion / day boundary). Restores health
    // and returns to Idle without changing the active captain.
    bool revive(int captain, float health) {
        if (!bound() || !P2CaptainOwnershipTable::isCaptain(captain)) return false;
        if (slots[captain].phase != P2CaptainPhase::Down || !std::isfinite(health)
            || health <= 0.0f)
            return false;
        slots[captain].health = health;
        slots[captain].phase = P2CaptainPhase::Idle;
        selectFallback();
        return true;
    }

    // Scene reload / checkpoint restore. Captures are transient: any Captured
    // captain returns Idle with no ownership change, so a reload cannot
    // duplicate or lose a squad. Down captains stay down (source dead flags).
    void reload() {
        if (!bound()) return;
        for (int c = 0; c < P2CaptainCount; ++c) {
            if (slots[c].phase == P2CaptainPhase::Captured) {
                slots[c].phase = slots[c].present ? P2CaptainPhase::Idle
                                                  : P2CaptainPhase::Down;
                slots[c].captureEpoch = 0;
            }
        }
        // Captor-held actors are transient; restore each to its previous
        // captain (or the active one) so a reload cannot lose a squad.
        for (const auto& entry : captives) {
            int restore = entry.second.previousOwner;
            if (!aliveIdle(restore)) restore = active;
            if (aliveIdle(restore)) table->tryClaim(entry.first, restore);
        }
        captives.clear();
        selectFallback();
    }

    // Claim a Pikmin or carried actor for a captain. Exclusivity is enforced
    // by the shared table, so within one frame the first claim wins.
    bool claim(int captain, std::uint32_t actor) {
        if (!bound() || !aliveIdle(captain)) return false;
        return table->tryClaim(actor, captain);
    }
    void abandon(int captain, std::uint32_t actor) {
        if (bound()) table->release(actor, captain);
    }

    // --- Per-captain squad split (lane 12 two-captain follow-up) ---

    // Move up to `count` of `from`'s actors to `to`, in ascending actor-id order
    // so a split is deterministic. Both captains must be controllable (present,
    // not captured/down) and distinct. Returns the moved actor ids; a `to`
    // captain with no room for a given actor leaves it with `from`.
    std::vector<std::uint32_t> splitSquad(int from, int to, std::size_t count) {
        std::vector<std::uint32_t> moved;
        if (!bound() || from == to || !aliveIdle(from) || !aliveIdle(to))
            return moved;
        std::vector<std::uint32_t> owned = table->actorsOwnedBy(from);
        if (count > owned.size()) count = owned.size();
        moved.reserve(count);
        for (std::size_t i = 0; i < count; ++i) {
            table->release(owned[i], from);
            if (table->tryClaim(owned[i], to)) {
                moved.push_back(owned[i]);
            } else {
                table->tryClaim(owned[i], from); // restore on refusal
            }
        }
        return moved;
    }

    // Move exactly the named actors from `from` to `to` when `from` owns them.
    // Refused for the same reasons as splitSquad(). Returns the moved count.
    std::size_t transferSquad(int from, int to, const std::uint32_t* actors,
                              std::size_t count) {
        if (!bound() || from == to || !aliveIdle(from) || !aliveIdle(to) || !actors)
            return 0;
        std::size_t moved = 0;
        for (std::size_t i = 0; i < count; ++i) {
            if (table->ownerOf(actors[i]) != from) continue;
            table->release(actors[i], from);
            if (table->tryClaim(actors[i], to)) {
                ++moved;
            } else {
                table->tryClaim(actors[i], from); // restore on refusal
            }
        }
        return moved;
    }

    // --- Captor-held actors (families 29/30; captor FSM stays family-owned) ---

    // A captor grabs an actor (Pikmin or carried item) under a nonzero captor
    // epoch. If captain-owned it is removed from that captain; the previous
    // owner is recorded for reload restoration. An already-captive actor is
    // never double-claimed.
    bool captureActor(std::uint64_t captorEpoch, std::uint32_t actor) {
        if (!bound() || !captorEpoch || !actor || captives.count(actor)) return false;
        CaptiveRecord record;
        record.captorEpoch = captorEpoch;
        record.previousOwner = table->ownerOf(actor);
        if (P2CaptainOwnershipTable::isCaptain(record.previousOwner))
            table->release(actor, record.previousOwner);
        captives[actor] = record;
        return true;
    }

    // Captor drop/release. `toCaptain` reattaches to the squad; an invalid or
    // unavailable target restores the previous owner when still controllable,
    // otherwise the actor is left free (whistle-reclaimable), never deleted.
    bool releaseActor(std::uint64_t captorEpoch, std::uint32_t actor, int toCaptain) {
        auto it = captives.find(actor);
        if (it == captives.end() || it->second.captorEpoch != captorEpoch) return false;
        const int previousOwner = it->second.previousOwner;
        captives.erase(it);
        int restore = toCaptain;
        if (!aliveIdle(restore)) restore = previousOwner;
        if (aliveIdle(restore)) return table->tryClaim(actor, restore);
        return true;
    }

    // Captor death/interruption: every actor it held is freed to the ground
    // (whistle-reclaimable). Returns the released actor ids.
    std::vector<std::uint32_t> dropAllCaptured(std::uint64_t captorEpoch) {
        std::vector<std::uint32_t> out;
        if (!bound() || !captorEpoch) return out;
        for (auto it = captives.begin(); it != captives.end();) {
            if (it->second.captorEpoch == captorEpoch) {
                out.push_back(it->first);
                it = captives.erase(it);
            } else {
                ++it;
            }
        }
        return out;
    }

    bool isCaptive(std::uint32_t actor) const { return captives.count(actor) != 0; }
    std::size_t captiveCount() const { return captives.size(); }

    // Synchronous cancellation before scene teardown or manager-slot reuse.
    // Frees this policy's actors and clears transient capture state.
    void cancel() {
        if (!bound()) return;
        for (int c = 0; c < P2CaptainCount; ++c) {
            table->releaseAll(c);
            slots[c].captureEpoch = 0;
        }
        captives.clear();
    }
};
