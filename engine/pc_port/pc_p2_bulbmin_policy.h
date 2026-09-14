#pragma once
#include <cstdint>
#include <unordered_map>
#include <vector>

// P2 Bulbmin leader/dependent ownership and cave-only recruitment contract
// (#131), lane 11 of docs/PIKMIN2_IMPLEMENTATION_FANOUT.md.
//
// Bulbmin are enemy-spawned Pikmin that a Mother Bulbmin (LeafChappy) births
// into the scene. Wild Bulbmin are not counted as Pikmin, are immune to every
// elemental hazard, follow their mother, and are converted into ordinary
// Pikmin only when a captain whistles them. They never persist through a cave
// exit, and only already-whistled Bulbmin descend to the next floor. The
// mother actor, its FSM and its model stay with the enemy family; this header
// owns the dependent ledger, recruitment and cave-transition boundary.
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0):
//   include/Game/Piki.h          Piki::Kind Bulbmin = 5; PikiInitArg::mLeader
//   include/Game/Entities/LeafChappy.h
//                                (Mother) Bulbmin = KumaChappy::Obj
//   src/plugProjectNishimuraU/LeafChappy.cpp:131-152
//                                birthChildren(): 10 pikiMgr->birth() at
//                                2.5*i+17.5 units, initArg.mLeader = mother
//   src/plugProjectKandoU/piki.cpp:155-156
//                                changeShape(Bulbmin) + setFPFlag(
//                                FPFLAGS_IsWildBulbmin)
//   src/plugProjectKandoU/piki.cpp:231,250-251,788-789
//                                wild Bulbmin are not Pikmin and do not count
//                                toward the alive-Pikmin total
//   src/plugProjectKandoU/interactPiki.cpp:178-179
//                                captain whistle resets IsWildBulbmin
//   src/plugProjectKandoU/interactPiki.cpp:347,453,511,543
//                                Bulbmin immune to Denki/Fire/Bubble/Gas
//   src/plugProjectKandoU/pikiMgr.cpp:134
//                                follows a Teki (isTekiFollowAI) while wild
//   src/plugProjectKandoU/pikiMgr.cpp:722-723,762
//                                exiting a cave never saves Bulbmin; a floor
//                                descent saves only isPikmin() (whistled) ones
//
// Invariants enforced by this contract (see the policy test):
//   1. One mother owns each dependent; a dependent is never born twice.
//   2. Recruitment converts a wild dependent in place; it is still one body
//      and is not duplicated or destroyed.
//   3. The mother's death releases its wild dependents; whistled team members
//      keep their captain ownership and survive it.
//   4. Floor descent keeps only whistled Bulbmin; cave exit removes them all.
//   5. Wild Bulbmin never count toward the Pikmin total.

enum P2BulbminPhase {
    P2BulbminWild = 0,      // follows the mother, not counted as a Pikmin
    P2BulbminRecruited = 1, // whistled; counted as a Pikmin
};

// Source birthChildren() spawns exactly ten dependents per mother.
static const int P2BULBMIN_MAX_DEPENDENTS = 10;

enum P2BulbminCaveTransition {
    P2BulbminDescendFloor = 0, // pikiMgr save filter keeps only recruited
    P2BulbminExitCave = 1,     // save filter drops every Bulbmin
};

// Bulbmin are immune to electricity, fire, water and gas in every phase.
inline bool p2_bulbmin_hazard_immune() { return true; }

struct P2BulbminCommand {
    bool accepted = false;
    std::uint32_t bulbmin = 0;
    int phase = P2BulbminWild;
    bool countsAsPikmin = false;
    bool detachFromLeader = false; // recruitment: host reassigns to a captain
};

struct P2BulbminTransitionOut {
    std::vector<std::uint32_t> kept;    // still in the scene after the move
    std::vector<std::uint32_t> removed; // must be despawned, never saved
    std::size_t recruitedKept = 0;
};

// Shared scene domain: dependent id -> {mother epoch, phase}. Invalidate the
// whole domain before any manager-slot or pointer reuse so a recycled id
// cannot inherit a stale leader.
class P2BulbminFlock {
    struct Record {
        std::uint64_t leaderEpoch = 0;
        int phase = P2BulbminWild;
    };
    std::unordered_map<std::uint32_t, Record> members;

public:
    void invalidateDomain() { members.clear(); }
    bool contains(std::uint32_t bulbmin) const { return members.count(bulbmin) != 0; }
    int phaseOf(std::uint32_t bulbmin) const {
        auto it = members.find(bulbmin);
        return it == members.end() ? -1 : it->second.phase;
    }
    bool ledBy(std::uint32_t bulbmin, std::uint64_t leaderEpoch) const {
        auto it = members.find(bulbmin);
        return it != members.end() && it->second.leaderEpoch == leaderEpoch;
    }
    bool add(std::uint32_t bulbmin, std::uint64_t leaderEpoch) {
        if (!bulbmin || !leaderEpoch || members.count(bulbmin)) return false;
        members[bulbmin] = Record{leaderEpoch, P2BulbminWild};
        return true;
    }
    bool recruit(std::uint32_t bulbmin, std::uint64_t leaderEpoch) {
        auto it = members.find(bulbmin);
        if (it == members.end() || it->second.leaderEpoch != leaderEpoch
            || it->second.phase != P2BulbminWild)
            return false;
        it->second.phase = P2BulbminRecruited;
        return true;
    }
    std::size_t wildCount() const {
        std::size_t n = 0;
        for (const auto& entry : members)
            if (entry.second.phase == P2BulbminWild) ++n;
        return n;
    }
    std::size_t recruitedCount() const {
        std::size_t n = 0;
        for (const auto& entry : members)
            if (entry.second.phase == P2BulbminRecruited) ++n;
        return n;
    }
    std::size_t size() const { return members.size(); }

    // Mother death/removal releases only its wild dependents. Recruited
    // Bulbmin keep their captain ownership and stay in the ledger.
    std::vector<std::uint32_t> releaseWild(std::uint64_t leaderEpoch) {
        std::vector<std::uint32_t> out;
        for (auto it = members.begin(); it != members.end();) {
            if (it->second.leaderEpoch == leaderEpoch
                && it->second.phase == P2BulbminWild) {
                out.push_back(it->first);
                it = members.erase(it);
            } else {
                ++it;
            }
        }
        return out;
    }

    // Scene-wide cave transition. Wild Bulbmin are removed on either move;
    // recruited Bulbmin survive a floor descent but not a full cave exit.
    P2BulbminTransitionOut applyTransition(P2BulbminCaveTransition move) {
        P2BulbminTransitionOut out;
        for (auto it = members.begin(); it != members.end();) {
            const bool wild = it->second.phase == P2BulbminWild;
            const bool remove = move == P2BulbminExitCave
                             || (move == P2BulbminDescendFloor && wild);
            if (remove) {
                out.removed.push_back(it->first);
                it = members.erase(it);
            } else {
                out.kept.push_back(it->first);
                if (!wild) ++out.recruitedKept;
                ++it;
            }
        }
        return out;
    }
};

// One instance per Mother Bulbmin (LeafChappy) actor.
class P2BulbminLeader {
    P2BulbminFlock* flock = nullptr;
    std::uint64_t epoch = 0;
    int dependents = 0;
    bool dead = false;

    bool current(std::uint64_t id) const { return flock && id && id == epoch; }

public:
    bool bind(P2BulbminFlock* domain, std::uint64_t id) {
        if (!domain || !id || epoch != 0) return false;
        flock = domain;
        epoch = id;
        return true;
    }
    bool bound() const { return flock != nullptr; }
    int dependentCount() const { return dependents; }

    // Source LeafChappy::birthChildren. Bounded at ten live dependents.
    P2BulbminCommand birth(std::uint64_t id, std::uint32_t bulbmin) {
        P2BulbminCommand out;
        if (!current(id) || dead) return out;
        if (dependents >= P2BULBMIN_MAX_DEPENDENTS) return out;
        if (!flock->add(bulbmin, epoch)) return out;
        ++dependents;
        out.accepted = true;
        out.bulbmin = bulbmin;
        out.phase = P2BulbminWild;
        return out;
    }

    // Captain whistle (interactPiki.cpp:178-179). The dependent stays one
    // body: it changes phase and the host reassigns it to the whistling
    // captain. A recruited dependent no longer follows the mother.
    P2BulbminCommand whistle(std::uint64_t id, std::uint32_t bulbmin) {
        P2BulbminCommand out;
        if (!current(id) || dead) return out;
        if (!flock->recruit(bulbmin, epoch)) return out;
        out.accepted = true;
        out.bulbmin = bulbmin;
        out.phase = P2BulbminRecruited;
        out.countsAsPikmin = true;
        out.detachFromLeader = true;
        return out;
    }

    // Mother death / removal. Wild dependents are released to the free set;
    // whistled team members keep their captain ownership and are untouched.
    std::vector<std::uint32_t> leaderDied(std::uint64_t id) {
        if (!current(id)) return {};
        dead = true;
        std::vector<std::uint32_t> released = flock->releaseWild(epoch);
        dependents = 0;
        return released;
    }

    // Synchronous cancellation before actor reuse. Releases only this
    // mother's wild dependents.
    void cancel() {
        if (flock) flock->releaseWild(epoch);
        dependents = 0;
        dead = false;
    }
};
