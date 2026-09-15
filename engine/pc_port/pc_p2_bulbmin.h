#pragma once
#include "pc_p2_bulbmin_policy.h"
#include "pc_p2_captain_policy.h"
#include <cstddef>
#include <cstdint>
#include <istream>
#include <string>
#include <vector>

// P2 Bulbmin engine bridge (#131), lane 11 of
// docs/PIKMIN2_IMPLEMENTATION_FANOUT.md.
//
// The header-only contract in pc_p2_bulbmin_policy.h owns the dependent ledger
// and recruitment/cave rules. This module is the boundary the live engine
// calls into: it parses the opt-in config, binds one Mother Bulbmin
// (LeafChappy) epoch, records the dependents the birth path hands it, converts
// a whistled dependent in place and (when a captain ownership table is bound)
// hands it to the captain/squad path from pc_p2_captain_policy.h.
//
// Opt-in only. With no `p2-bulbmin.txt` and no PIKMIN_P2_BULBMIN environment
// value the engine entrypoints are a no-op, so the module is inert by default.
//
// Source basis (native/pikmin2-research, US GPVE01 revision 0):
//   src/plugProjectNishimuraU/LeafChappy.cpp:131-152
//       birthChildren(): 10 pikiMgr->birth(), initArg.mLeader = mother,
//       positions at 2.5*i+17.5 units behind the mother
//   src/plugProjectKandoU/interactPiki.cpp:178-179
//       captain whistle resets IsWildBulbmin
//   src/plugProjectKandoU/pikiMgr.cpp:722-723,762
//       cave exit drops all Bulbmin, a floor descent keeps only isPikmin()
//   src/plugProjectKandoU/piki.cpp:155-156
//       changeShape(Bulbmin) + setFPFlag(FPFLAGS_IsWildBulbmin)

// Configuration body:
//   P2_BULBMIN_1 <mother_epoch> <dependents> [mother_model]
//   P2_BULBMIN_2 <mother_epoch> <dependents> <mother_model>
// `mother_epoch` is a nonzero decimal id identifying the mother instance;
// `dependents` is the source ten-dependent bound (1..P2BULBMIN_MAX_DEPENDENTS).
// `mother_model` names the visual proxy standing in for the missing
// LeafChappy/KumaChappy model. It is metadata for logs and the mother registry;
// the port never fabricates a rendered LeafChappy. P2_BULBMIN_1 makes the label
// optional (defaults to "kochappy_proxy"); P2_BULBMIN_2 requires it. Unknown
// headers, missing fields, non-numeric tokens, a zero epoch, an out-of-range
// dependent count, a malformed label or trailing data are all rejected.
struct P2BulbminConfig {
    std::uint64_t motherEpoch = 0;
    int maxDependents = P2BULBMIN_MAX_DEPENDENTS;
    std::string motherModel = "kochappy_proxy";
};

bool p2_bulbmin_read(std::istream& in, P2BulbminConfig& out);

// Dedicated Mother Bulbmin registration. There is no LeafChappy/KumaChappy
// actor or `piki_kochappy` model in the port, so a registered mother is a
// labeled proxy host: the existing Chappy-family Kochappy visual bank stands in
// for the missing model. The registry is identity/release bookkeeping only; it
// never pretends a real LeafChappy was spawned or rendered.
struct P2BulbminMotherActor {
    void* host = nullptr;   // engine Creature*/BTeki*; compared, never dereferenced
    std::string model;      // visual proxy label, e.g. "kochappy_proxy"
    bool proxy = true;      // true unless a real LeafChappy actor is ever wired
    bool registered = false;
};

// Engine-free bridge core. The unit test drives this directly; the engine
// translation unit owns one instance and maps live Piki pointers onto ids.
class P2BulbminBridge {
    P2BulbminFlock flock;
    P2BulbminLeader mother;
    P2BulbminMotherActor motherActor;
    P2CaptainOwnershipTable* captains = nullptr;
    P2BulbminConfig config;
    bool active = false;
    int dependents = 0;

public:
    void reset();
    // Returns false for an epoch-zero or over-cap config, leaving it inert.
    bool setup(const P2BulbminConfig& cfg, P2CaptainOwnershipTable* ownership = nullptr);
    void bindCaptains(P2CaptainOwnershipTable* ownership) { captains = ownership; }
    bool enabled() const { return active; }
    const P2BulbminConfig& settings() const { return config; }
    int dependentCount() const { return dependents; }

    // Dedicated mother registration. One mother per bridge: a second, different
    // host is refused. Re-registering the same host updates only the label and
    // returns false so the caller does not re-drive birth. Returns true only
    // when a new mother identity was accepted.
    bool registerMother(void* host, const std::string& model = std::string(),
                        bool proxy = true);
    bool hasMother() const { return motherActor.registered; }
    bool motherIs(void* host) const {
        return motherActor.registered && host && motherActor.host == host;
    }
    const P2BulbminMotherActor& motherActorInfo() const { return motherActor; }
    // Death/removal of the registered mother host: releases only wild
    // dependents and clears the registration. Returns the released count, or -1
    // when `host` is not the registered mother (or no mother is registered).
    int motherDied(void* host);
    void clearMother() { motherActor = P2BulbminMotherActor{}; }

    // Birth entry for the configured mother epoch (source birthChildren one
    // iteration). Refused when inert, already at the configured cap, or the
    // dependent was already born.
    P2BulbminCommand birth(std::uint32_t id);
    // Whistle/recruit entry. Converts the body in place; when an ownership
    // table is bound and `captain` is valid the recruited Piki is claimed by
    // that captain. Pass P2CaptainInvalid to skip the handoff.
    P2BulbminCommand whistle(std::uint32_t id, int captain = P2CaptainInvalid);
    // Mother death releases only wild dependents.
    std::vector<std::uint32_t> leaderDied();
    // Drop one body (host Piki destroyed / slot reuse).
    bool forget(std::uint32_t id);
    // Cave-transition filter (pikiMgr save filter).
    P2BulbminTransitionOut transition(P2BulbminCaveTransition move);
    // Non-mutating drop set for transition(). The live checkpoint computes this
    // before writing the transfer file and commits transition() only after a
    // successful write, so a failed write can retry without leaking bodies.
    std::vector<std::uint32_t> transitionRemoves(P2BulbminCaveTransition move) const {
        return flock.removedOn(move);
    }

    std::size_t size() const { return flock.size(); }
    std::size_t wildCount() const { return flock.wildCount(); }
    std::size_t recruitedCount() const { return flock.recruitedCount(); }
    int phaseOf(std::uint32_t id) const { return flock.phaseOf(id); }
    bool hasCaptains() const { return captains != nullptr; }
};

// Engine-free birth driver. The live hook in pc_p2_bulbmin.cpp binds a spawn
// callback that creates one body through pikiMgr->birth() and registers it in
// the bridge; the unit test binds a double. A callback returns the nonzero
// ledger id it registered (0 when the engine has no free body or the cap is
// reached), so the driver stays a faithful, testable model of the source
// LeafChappy::birthChildren() loop.
using P2BulbminSpawnFn = std::uint32_t (*)(void* context, int index);

class P2BulbminDriver {
    P2BulbminBridge* bridge = nullptr;
    P2BulbminSpawnFn spawn = nullptr;
    void* context = nullptr;
    int born = 0;

public:
    bool bind(P2BulbminBridge* target, P2BulbminSpawnFn spawner, void* spawnContext) {
        if (!target || !target->enabled() || !spawner) return false;
        bridge = target;
        spawn = spawner;
        context = spawnContext;
        born = 0;
        return true;
    }
    bool bound() const { return bridge != nullptr; }
    int bornCount() const { return born; }

    // Birth up to `requested` dependents (default and hard bound: the source
    // ten). Stops at the first callback that returns 0, which is how both the
    // configured cap and a full engine field surface.
    int birthFlock(int requested = P2BULBMIN_MAX_DEPENDENTS) {
        if (!bridge) return 0;
        if (requested < 0) requested = 0;
        if (requested > P2BULBMIN_MAX_DEPENDENTS) requested = P2BULBMIN_MAX_DEPENDENTS;
        int made = 0;
        for (int i = 0; i < requested; ++i) {
            const std::uint32_t id = spawn(context, i);
            if (!id || bridge->phaseOf(id) < 0) break;
            ++made;
        }
        born += made;
        return made;
    }

    P2BulbminCommand whistle(std::uint32_t id, int captain = P2CaptainInvalid) {
        return bridge ? bridge->whistle(id, captain) : P2BulbminCommand{};
    }
    // Detaches the wild flock; the caller mirrors the release into the engine.
    std::vector<std::uint32_t> leaderDied() {
        if (!bridge) return {};
        born = 0;
        return bridge->leaderDied();
    }
    P2BulbminTransitionOut transition(P2BulbminCaveTransition move) {
        return bridge ? bridge->transition(move) : P2BulbminTransitionOut{};
    }
};

inline bool p2_bulbmin_label_valid(const std::string& label) {
    if (label.empty() || label.size() > 32) return false;
    return label.find_first_not_of(
               "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
           == std::string::npos;
}

inline bool p2_bulbmin_read(std::istream& in, P2BulbminConfig& out) {
    out = P2BulbminConfig{};
    std::string header, epoch, dependents, label, extra;
    if (!(in >> header >> epoch >> dependents)) return false;
    const bool requiresLabel = header == "P2_BULBMIN_2";
    if (header != "P2_BULBMIN_1" && !requiresLabel) return false;
    if (in >> label) {
        if (in >> extra) return false; // reject trailing data
        if (!p2_bulbmin_label_valid(label)) return false;
        out.motherModel = label;
    } else if (requiresLabel) {
        return false; // P2_BULBMIN_2 requires the proxy model label
    }
    if (epoch.empty() || epoch.size() > 20
        || epoch.find_first_not_of("0123456789") != std::string::npos)
        return false;
    if (dependents.empty() || dependents.size() > 2
        || dependents.find_first_not_of("0123456789") != std::string::npos)
        return false;
    unsigned long long mother = 0;
    int cap = 0;
    try {
        mother = std::stoull(epoch);
        cap = std::stoi(dependents);
    } catch (...) {
        return false;
    }
    if (mother == 0 || cap < 1 || cap > P2BULBMIN_MAX_DEPENDENTS) return false;
    out.motherEpoch = static_cast<std::uint64_t>(mother);
    out.maxDependents = cap;
    return true;
}

inline void P2BulbminBridge::reset() {
    if (active) mother.cancel();
    flock = P2BulbminFlock{};
    mother = P2BulbminLeader{};
    motherActor = P2BulbminMotherActor{};
    captains = nullptr;
    config = P2BulbminConfig{};
    active = false;
    dependents = 0;
}

inline bool P2BulbminBridge::registerMother(void* host, const std::string& model,
                                            bool proxy) {
    if (!active || !host) return false;
    if (motherActor.registered) {
        // Same host: refresh the label but report "not newly registered" so the
        // caller does not run birthChildren a second time. A different host is
        // refused: this bridge owns exactly one mother.
        if (motherActor.host == host) {
            if (!model.empty()) motherActor.model = model;
            motherActor.proxy = proxy;
        }
        return false;
    }
    motherActor.host = host;
    motherActor.model = model.empty() ? config.motherModel : model;
    motherActor.proxy = proxy;
    motherActor.registered = true;
    return true;
}

inline int P2BulbminBridge::motherDied(void* host) {
    if (!active || !motherActor.registered || motherActor.host != host) return -1;
    motherActor = P2BulbminMotherActor{};
    return static_cast<int>(leaderDied().size());
}

inline bool P2BulbminBridge::setup(const P2BulbminConfig& cfg,
                                   P2CaptainOwnershipTable* ownership) {
    reset();
    if (cfg.motherEpoch == 0 || cfg.maxDependents < 1
        || cfg.maxDependents > P2BULBMIN_MAX_DEPENDENTS)
        return false;
    if (!mother.bind(&flock, cfg.motherEpoch)) return false;
    config = cfg;
    captains = ownership;
    active = true;
    return true;
}

inline P2BulbminCommand P2BulbminBridge::birth(std::uint32_t id) {
    P2BulbminCommand out;
    if (!active || dependents >= config.maxDependents) return out;
    out = mother.birth(config.motherEpoch, id);
    if (out.accepted) ++dependents;
    return out;
}

inline P2BulbminCommand P2BulbminBridge::whistle(std::uint32_t id, int captain) {
    P2BulbminCommand out;
    if (!active) return out;
    out = mother.whistle(config.motherEpoch, id);
    if (out.accepted && captains && P2CaptainOwnershipTable::isCaptain(captain))
        captains->tryClaim(id, captain);
    return out;
}

inline std::vector<std::uint32_t> P2BulbminBridge::leaderDied() {
    if (!active) return {};
    dependents = 0;
    return mother.leaderDied(config.motherEpoch);
}

inline bool P2BulbminBridge::forget(std::uint32_t id) {
    if (!active) return false;
    if (!flock.remove(id, config.motherEpoch)) return false;
    if (dependents > 0) --dependents;
    return true;
}

inline P2BulbminTransitionOut P2BulbminBridge::transition(P2BulbminCaveTransition move) {
    if (!active) return P2BulbminTransitionOut{};
    return flock.applyTransition(move);
}

class Piki;
class Creature;
class Navi;
class BTeki;

// Live engine bridge. No-op unless opted in.
void pc_p2_bulbmin_setup();
void pc_p2_bulbmin_reset();
bool pc_p2_bulbmin_active();

// Birth entry: records a live dependent Piki for the configured mother epoch
// and marks its species. Returns false when inert or refused by the ledger.
bool pc_p2_bulbmin_birth(Piki* bulbmin);
// Source LeafChappy::birthChildren: birth a body through pikiMgr, bind it to
// `leader` and the configured epoch, and place it behind the mother. Returns
// nullptr when there is no live manager/scene.
Piki* pc_p2_bulbmin_birth_dependent(Creature* leader, const struct Vector3f& motherPos,
                                    float faceDir, int index);
// Whistle/recruit entry: converts the body in place and reassigns captain
// ownership at the engine level. Returns false when inert or not a dependent.
bool pc_p2_bulbmin_whistle(Piki* bulbmin);
// Drop a destroyed dependent.
void pc_p2_bulbmin_forget(Piki* piki);
// Cave save filter (source PikiMgr::caveSaveAllPikmins, pikiMgr.cpp:723),
// applied in two steps by pc_p2_cave_checkpoint:
//   * pc_p2_bulbmin_transition_removes(move) computes, non-mutatingly, the live
//     Piki bodies to exclude from the persisted squad. On P2BulbminDescendFloor
//     a wild (unwhistled) dependent is removed and a recruited one kept; on
//     P2BulbminExitCave every tracked Bulbmin is removed. Untracked
//     (injected/restored before this save) Bulbmin are never returned.
//   * pc_p2_bulbmin_transition(move) is the mutating commit, called only after
//     the transfer file has been written successfully, so a failed write can be
//     retried without leaking the removed bodies (they stay tracked).
std::vector<Piki*> pc_p2_bulbmin_transition_removes(P2BulbminCaveTransition move);
std::vector<Piki*> pc_p2_bulbmin_transition(P2BulbminCaveTransition move);
// Optional handoff target for whistle; another lane can bind its captain
// ownership table so recruited Bulbmin join the squad.
void pc_p2_bulbmin_bind_captain_table(P2CaptainOwnershipTable* ownership);

// Opt-in driver entrypoint (source LeafChappy::birthChildren). Births up to
// `requested` dependents (source ten) behind `leader` through pikiMgr->birth()
// and the bridge ledger. No-op returning 0 when inert or no live scene.
int pc_p2_bulbmin_drive_birth(Creature* leader, const struct Vector3f& leaderPos,
                              float faceDir, int requested = P2BULBMIN_MAX_DEPENDENTS);
// Use the existing Chappy-family (Kochappy) registration as the mother
// stand-in: births the source flock once for that actor. Returns dependents
// born (0 when inert, already attached, or no actor). This is the engine double
// for a missing LeafChappy actor; see docs/PIKMIN2_BULBMIN_CONTRACT.md.
int pc_p2_bulbmin_attach_mother(Creature* mother);
// Dedicated Mother Bulbmin registration path: register `host` as the labeled
// mother proxy and, when it is newly registered, drive the source ten-body
// flock behind it. Separate from the Kochappy auto-attach so a caller can
// supply its own identity/model label. `proxy` must stay true while the port
// has no LeafChappy model; a false value only labels a future real actor and
// never fabricates one. Returns the dependents born (0 when inert, already
// registered, or no host).
int pc_p2_bulbmin_attach_mother_ex(Creature* host, const char* model, bool proxy);
// Resolve the Mother Bulbmin stand-in host: the labeled Dwarf Red (Kochappy)
// registry when present, else the first bare Chappy-family generator row every
// room preview writes (scripts/preview_pikmin2_room.py TEKI_Chappy). The bridge
// only compares the pointer and reads position/face direction once, so a
// bank-free host is sufficient. Returns nullptr when no host exists.
BTeki* pc_p2_bulbmin_mother_host();
// Opt-in env registration (PIKMIN_P2_BULBMIN_MOTHER). Registers the resolved
// Chappy-family host under an explicit label. No-op returning 0 when the env
// value is unset, no host resolves, or the bridge is inert.
int pc_p2_bulbmin_attach_dedicated_mother();
// Label of the registered mother proxy, or "none" when unregistered.
const char* pc_p2_bulbmin_mother_model();
bool pc_p2_bulbmin_has_mother();
// Real Navi::callPikis whistle hook: recruits every wild dependent of `navi`
// within `radius`, claiming through the bound captain table when present. `via`
// labels the caller for the P2_BULBMIN_WHISTLE marker (navi.cpp passes
// "navi_callPikis"; a direct hook call defaults to "direct").
int pc_p2_bulbmin_call_pikis(Navi* navi, float radius, const char* via = "direct");
// Mother death/removal: release only wild dependents and detach them from the
// dead leader. Whistled members keep their captain ownership. Returns released.
int pc_p2_bulbmin_leader_died();
// Chappy-family slot reuse/death (TekiMgr forget): release the flock when the
// forgotten actor was the mother stand-in.
void pc_p2_bulbmin_proxy_forget(BTeki* mother);
int pc_p2_bulbmin_dependent_count();

// Per-Piki phase query (source pikiMgr.cpp:723,762). `phase` returns -1 when the
// Piki is not a tracked dependent (an injected/restored Bulbmin counts as
// recruited, i.e. isPikmin()), P2BulbminWild for an unwhistled dependent, and
// P2BulbminRecruited for a whistled one. The live checkpoint uses
// pc_p2_bulbmin_transition_removes/transition (above); this is a read-only query.
int pc_p2_bulbmin_phase(const Piki* piki);
