#pragma once
#include <cmath>
#include <cstdint>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Narrow P2 Fuefuki whistle-interference / squad-control policy (#245).
// Not a P1 Pikmin or Navi state implementation. Source basis:
// native/tools/P2_FUEFUKI_AUDIT.md against projectPiki/pikmin2 632af937.
//
// Ownership model: one exclusive controller per Pikmin. The beetle borrows
// Pikmin through the AI-action slot (ACT_Teki) and never writes captain
// ownership (piki->mNavi). Captain switch and party combine are no-ops on
// beetle-held Pikmin. Release happens only through owner death (Panic,
// whistle-reclaimable) or owner suspension (flying/bittered, Success exit).

enum class P2FuefukiPhase { Idle, Casting };

struct P2FuefukiCommand {
    bool accepted = false;
    bool claim = false;          // start ACT_Teki on the admitted Pikmin
    bool releasePanic = false;   // owner died: transit follower to Panic
    bool releaseSuspend = false; // owner flying/bittered: end follow, emote
    bool reclaim = false;        // captain whistle reclaim of a Panic follower
    bool squadActive = false;    // squad-cadence branch selector
    std::uint32_t pikmin = 0;
    float radiusModifier = 0.0f; // whistle ring growth 0..1
};

// Suspend-release brain destination (issue #245 open item "suspend brain-
// fallback (Formation vs Free)" -- traced, resolved to Free).
//
// Source basis (projectPiki/pikmin2 632af937, read-only under
// pikmin2-research): ActTeki::getNextAIType() returns ACT_Free
// (include/PikiAI.h:1254), so when the flying/bittered exit returns
// ACTEXEC_Success the brain's fallback switch runs
// start(ACT_Free, nullptr) (src/plugProjectKandoU/aiAction.cpp:108-110);
// the ACT_Formation/searchOrima() branch is never reached for a Fuefuki
// follower. The stored piki->mNavi is NOT consulted, and ActFree::init
// clears it (src/plugProjectKandoU/aiFree.cpp:33). A suspended follower
// therefore detaches from every captain and re-attaches only through a
// future captain touch or whistle path -- never automatically.
//
// Ordering caveat: the source force-invokes its situation scan BEFORE the
// fallback (Brain::exec, aiAction.cpp:92-95); a released Pikmin may be
// re-tasked there (notably ACT_Attack on a grounded, bittered beetle that
// just released it, which passes graspSituation_Fast's alive+grounded+
// living-thing test inside mEnemySearchRange). That is a world-side gate
// the lane cannot see engine-free; the lane contract guarantees the
// ownership release and the Free fallback decision, and the host owns the
// pre-fallback situation-scan re-task.
enum P2FuefukiSuspendFallback {
    P2FUEFUKI_SUSPEND_FALLBACK_FREE = 0, // start(ACT_Free)
};

struct P2FuefukiSuspendOut {
    bool accepted = false;
    std::vector<std::uint32_t> released; // claims freed this exit
    P2FuefukiSuspendFallback fallback = P2FUEFUKI_SUSPEND_FALLBACK_FREE;
};

// Shared callback domain: pikmin -> holding owner epoch; 0 = free.
// One table serves every beetle instance so two beetles can never both
// hold the same Pikmin. Invalidate the entire domain before any manager
// slot or owner-pointer reuse; epochs never wrap or repeat.
class P2FuefukiOwnershipTable {
    std::unordered_map<std::uint32_t, std::uint64_t> holders;

public:
    void invalidateDomain() { holders.clear(); }
    bool isHeld(std::uint32_t pikmin) const { return holders.count(pikmin) != 0; }
    bool heldBy(std::uint32_t pikmin, std::uint64_t epoch) const
    {
        auto it = holders.find(pikmin);
        return it != holders.end() && it->second == epoch;
    }
    bool tryClaim(std::uint32_t pikmin, std::uint64_t epoch)
    {
        if (!pikmin || !epoch || holders.count(pikmin)) return false;
        holders[pikmin] = epoch;
        return true;
    }
    void release(std::uint32_t pikmin, std::uint64_t epoch)
    {
        if (heldBy(pikmin, epoch)) holders.erase(pikmin);
    }
    std::vector<std::uint32_t> releaseAll(std::uint64_t epoch)
    {
        std::vector<std::uint32_t> out;
        for (auto it = holders.begin(); it != holders.end();) {
            if (it->second == epoch) {
                out.push_back(it->first);
                it = holders.erase(it);
            } else {
                ++it;
            }
        }
        return out;
    }
};

// One instance per beetle owner. All mutating calls are epoch-qualified;
// a stale epoch (previous manager-slot occupant) is always rejected.
class P2FuefukiInterferencePolicy {
    P2FuefukiOwnershipTable* table = nullptr;
    std::uint64_t epoch = 0;
    bool ownerDead = false;
    P2FuefukiPhase phase = P2FuefukiPhase::Idle;
    float radiusModifier = 0.0f;
    int squadTimer = 0; // simulation ticks, source-faithful per-frame decrement
    std::unordered_set<std::uint32_t> panicReleased;

    bool current(std::uint64_t id) const { return table && id && id == epoch; }

public:
    P2FuefukiPhase getPhase() const { return phase; }
    bool squadActive() const { return squadTimer > 0; }
    float getRadiusModifier() const { return radiusModifier; }
    bool holds(std::uint32_t pikmin) const { return table && table->heldBy(pikmin, epoch); }

    // Bind a strictly increasing, nonzero owner epoch for this callback
    // domain. Rebinding requires a fresh (idle, unclaimed) instance.
    bool bind(P2FuefukiOwnershipTable* domain, std::uint64_t id)
    {
        if (!domain || !id || epoch != 0) return false;
        table  = domain;
        epoch  = id;
        return true;
    }

    // Begin a whistle cast (source StateWhisle init/startWhisle).
    P2FuefukiCommand beginCast(std::uint64_t id)
    {
        P2FuefukiCommand out;
        if (!current(id) || ownerDead || phase != P2FuefukiPhase::Idle) return out;
        phase          = P2FuefukiPhase::Casting;
        radiusModifier = 0.0f;
        out.accepted   = true;
        return out;
    }

    // Grow the ring once per simulation update while casting. Paused calls
    // must be omitted or pass zero delta. Source clamps the modifier at 1.0
    // after one second; effective radius = modifier * mAttackRadius (host
    // supplies the retail parm).
    P2FuefukiCommand tickCast(std::uint64_t id, float delta)
    {
        P2FuefukiCommand out;
        if (!current(id) || phase != P2FuefukiPhase::Casting || !std::isfinite(delta) || delta < 0.0f)
            return out;
        radiusModifier += delta;
        if (radiusModifier > 1.0f) radiusModifier = 1.0f;
        out.accepted       = true;
        out.radiusModifier = radiusModifier;
        return out;
    }

    // Admission-before-mutation (source InteractFueFuki::actPiki): the
    // target must be alive, in a callable state, not stuck to a mouth and
    // not already ACT_Teki-owned by anyone. Exclusivity is enforced by the
    // shared table, so within one frame the first admit in the host's
    // fixed owner ordering wins; a simultaneous second claim is rejected.
    P2FuefukiCommand admit(std::uint64_t id, std::uint32_t pikmin, bool living, bool callableState,
                           bool stuckToMouth, bool alreadyTekiOwned)
    {
        P2FuefukiCommand out;
        if (!current(id) || phase != P2FuefukiPhase::Casting) return out;
        if (!living || !callableState || stuckToMouth || alreadyTekiOwned) return out;
        if (!table->tryClaim(pikmin, epoch)) return out;
        panicReleased.erase(pikmin);
        out.accepted = true;
        out.claim    = true;
        out.pikmin   = pikmin;
        return out;
    }

    // End the whistle cast after the source's fixed cast duration
    // (source finishWhisle / StateWhisle cleanup) while claims persist:
    // followers remain ACT_Teki-owned and keep pinging. The ring resets.
    P2FuefukiCommand endCast(std::uint64_t id)
    {
        P2FuefukiCommand out;
        if (!current(id) || phase != P2FuefukiPhase::Casting) return out;
        phase          = P2FuefukiPhase::Idle;
        radiusModifier = 0.0f;
        out.accepted   = true;
        return out;
    }

    // Each active follower pings its owner once per exec tick (source
    // InteractFuefukiTimerReset sets 5.0). Host cadence decision: the
    // timer is an integer count of fixed simulation ticks, decremented
    // exactly once per tick by tickSquad; it is never scaled by deltaTime.
    // Retail runs at 60 fps, so the 5-tick window is ~83 ms; because ping
    // and decrement rates match, any live follower keeps the squad active.
    P2FuefukiCommand ping(std::uint64_t id, std::uint32_t pikmin)
    {
        P2FuefukiCommand out;
        if (!current(id) || !table->heldBy(pikmin, epoch)) return out;
        squadTimer     = 5;
        out.accepted   = true;
        out.pikmin     = pikmin;
        out.squadActive = true;
        return out;
    }

    // Call exactly once per simulation tick after source exec ordering.
    P2FuefukiCommand tickSquad(std::uint64_t id)
    {
        P2FuefukiCommand out;
        if (!current(id)) return out;
        if (squadTimer > 0) squadTimer--;
        out.accepted    = true;
        out.squadActive = squadTimer > 0;
        return out;
    }

    // Owner flying or bittered (source ActTeki ACTEXEC_Success branches,
    // aiTeki.cpp:83-94 -- both set mToEmote and return Success): followers
    // end the follow action with the emote exit. The release picks the
    // source brain destination -- Free, never Formation (see
    // P2FuefukiSuspendFallback). No captain ownership is written; the
    // Pikmin's mNavi is not consulted and is cleared by ActFree::init.
    P2FuefukiSuspendOut suspend(std::uint64_t id)
    {
        P2FuefukiSuspendOut out;
        if (!current(id)) return out;
        phase          = P2FuefukiPhase::Idle;
        radiusModifier = 0.0f;
        squadTimer     = 0;
        out.accepted   = true;
        out.released   = table->releaseAll(epoch);
        out.fallback   = P2FUEFUKI_SUSPEND_FALLBACK_FREE;
        return out;
    }

    // Owner defeat mid-effect (source ActTeki owner-death branch): every
    // follower transits to Panic and becomes whistle-reclaimable. The
    // claim list is committed to panicReleased before the host runs any
    // Pikmin state callback, so reentrancy cannot lose a follower. The
    // epoch stays bound so reclaimPanic keeps working, but the dead owner
    // cannot cast, admit or ping again; host must cancel() before reuse.
    std::vector<std::uint32_t> ownerDied(std::uint64_t id)
    {
        if (!current(id)) return {};
        ownerDead      = true;
        phase          = P2FuefukiPhase::Idle;
        radiusModifier = 0.0f;
        squadTimer     = 0;
        std::vector<std::uint32_t> released = table->releaseAll(epoch);
        for (std::uint32_t p : released) panicReleased.insert(p);
        return released;
    }

    // Captain whistle reclaim (source InteractFue::actPiki ACT_Teki
    // branch): only a follower in the Panic-released set is callable.
    // Accepted reclaim clears the record; the host then performs the
    // source ownership write (clear action, piki->mNavi = whistling
    // captain, LookAt) — the only captain-ownership mutation in this lane.
    P2FuefukiCommand reclaimPanic(std::uint32_t pikmin)
    {
        P2FuefukiCommand out;
        if (!table || !panicReleased.count(pikmin)) return out;
        panicReleased.erase(pikmin);
        out.accepted = true;
        out.reclaim  = true;
        out.pikmin   = pikmin;
        return out;
    }

    // Captain switch and party combine are always no-ops on beetle-held or
    // Panic-released Pikmin (source: InteractFue combine touches Formation
    // actions only; ACT_Teki is callable only in Panic via reclaimPanic).
    P2FuefukiCommand captainSwitch(std::uint32_t pikmin) const
    {
        P2FuefukiCommand out;
        (void)pikmin;
        return out;
    }
    P2FuefukiCommand partyCombine(std::uint32_t pikmin) const
    {
        P2FuefukiCommand out;
        (void)pikmin;
        return out;
    }

    // Synchronous cancellation before owner teardown, manager-slot reuse,
    // movie/scene exits or external state interruption. Releases this
    // owner's claims without emitting any Pikmin state command — death and
    // suspension releases must go through ownerDied/suspend first; cancel
    // only guarantees no claim survives the teardown.
    void cancel(std::uint64_t id)
    {
        if (!current(id)) return;
        table->releaseAll(epoch);
        panicReleased.clear();
        ownerDead      = false;
        phase          = P2FuefukiPhase::Idle;
        radiusModifier = 0.0f;
        squadTimer     = 0;
    }
};
