#pragma once
// Pikmin 2 lane-22 fixed-hazard policy (#170, child #447).
//
// Pure, engine-free mirror of the fixed-hazard section of
// experimental/pikmin2_elemental_behavior.py (root branch
// opencode/p2-lane22-elemental):
//   Hiba (20, fire geyser), GasHiba (21, gas pipe), ElecHiba (22, wire).
// Receiver immunity and the generic stimulus enum are shared with
// pc_p2_dweevil_policy.h so both sidecars consume one policy.
//
// Source anchors (decompilation revision
// 632af93787b9c95b63f0c13be32b161375ce3a96, per
// docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md):
//   * Hiba Dead/Wait/Attack            HibaState.cpp:14-20,127-159
//   * GasHiba Dead/Wait/Attack         GasHibaState.cpp:13-19,129-169
//   * GasHiba bridge/gate living link  GasHiba.cpp:193-296
//   * ElecHiba Dead/Wait/Sign/Attack   ElecHibaState.cpp:13-20,93-268
//   * ElecHiba +/- separation nodes    ElecHibaMgr.cpp:110-131
//   * ElecHiba team-head damage        ElecHiba.cpp:139-157,752-776
//   * Receiver colour immunity         src/plugProjectKandoU/interactPiki.cpp:334,445,503,531
#include "pc_p2_dweevil_policy.h"
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace p2hiba {

using p2dweevil::Colour;
using p2dweevil::Red;
using p2dweevil::Yellow;
using p2dweevil::Blue;
using p2dweevil::Purple;
using p2dweevil::White;
using p2dweevil::Bulbmin;
using p2dweevil::Stimulus;
using p2dweevil::HazardAction;
using p2dweevil::HazardWait;
using p2dweevil::HazardAttack;
using p2dweevil::HazardDead;
using p2dweevil::StimNone;
using p2dweevil::StimFire;
using p2dweevil::StimBubble;
using p2dweevil::StimGas;
using p2dweevil::StimDenki;
using p2dweevil::HibaId;
using p2dweevil::GasHibaId;
using p2dweevil::ElecHibaId;
using p2dweevil::isFixedHazard;
using p2dweevil::hazardActivate;
using p2dweevil::pikminImmune;
using p2dweevil::receiverAccepts;

// Per-hazard state IDs (Hiba.h:136-141; GasHiba.h:151-156; ElecHiba.h:197-203).
enum HibaState { HibaDead = 0, HibaWait = 1, HibaAttack = 2 };
enum GasHibaState { GasHibaDead = 0, GasHibaWait = 1, GasHibaAttack = 2 };
enum ElecHibaState { ElecHibaDead = 0, ElecHibaWait = 1, ElecHibaSign = 2, ElecHibaAttack = 3 };

// ElecHiba team-head damage routing (ElecHiba.cpp:139-157,752-776).
enum Sided { SidedReject = 0, SidedRouteToHead };
// GasHiba bridge/gate living owner (GasHiba.cpp:204-272).
enum LinkOwner { LinkNone = 0, LinkBridge, LinkGate, LinkBridgeGate };

struct ElecStep {
    ElecHibaState next;
    bool emits;
};

struct HazardTiming {
    float wait;
    float active;
    float attackStart; // GasHiba only
    float warning;     // ElecHiba only
    float stop;
};

// Retail disc proper blocks, US GPVE01 rev 0 <hazard>/enemyparm.txt
// (docs/PIKMIN2_DWEEVIL_ASSETS.md sections 4,153-166).
inline HazardTiming discTiming(int hazardId) {
    switch (hazardId) {
    case HibaId: return HazardTiming{3.0f, 2.5f, 0.0f, 0.0f, 30.0f};
    case GasHibaId: return HazardTiming{0.0f, 3.0f, 0.6f, 0.0f, 30.0f};
    case ElecHibaId: return HazardTiming{1.5f, 2.5f, 0.0f, 1.5f, 30.0f};
    default: throw std::runtime_error("not a fixed hazard");
    }
}

// Build-time header defaults, kept distinct from the disc values above.
inline HazardTiming headerTiming(int hazardId) {
    switch (hazardId) {
    case HibaId: return HazardTiming{2.5f, 2.5f, 0.0f, 0.0f, 10.0f};
    case GasHibaId: return HazardTiming{2.5f, 2.5f, 1.0f, 0.0f, 10.0f};
    case ElecHibaId: return HazardTiming{2.5f, 2.5f, 0.0f, 2.5f, 10.0f};
    default: throw std::runtime_error("not a fixed hazard");
    }
}

// Concrete element the hazard emits to a creature it contacts.
inline Stimulus hazardStimulus(int hazardId) {
    switch (hazardId) {
    case HibaId: return StimFire;
    case GasHibaId: return StimGas;
    case ElecHibaId: return StimDenki;
    default: throw std::runtime_error("not a fixed hazard");
    }
}

// Panic subtype requested by an elemental stimulus (audit line 43).
inline const char* panicFor(Stimulus stimulus) {
    switch (stimulus) {
    case StimFire: return "Fire";
    case StimBubble: return "Bubble";
    case StimGas: return "Gas";
    case StimDenki: return "DenkiDying";
    case StimNone: return "None";
    }
    return "None";
}

// Hiba Attack stimulates every update and finishes on death or active-time
// expiry (HibaState.cpp:127-159).
inline bool hibaEmit(HibaState state, float health, float activeElapsed, float activeTime) {
    if (!std::isfinite(health) || !std::isfinite(activeElapsed) || !std::isfinite(activeTime)) {
        throw std::runtime_error("non-finite Hiba emission input");
    }
    if (health <= 0.0f || state != HibaAttack) return false;
    return activeElapsed < activeTime;
}

// GasHiba Attack stimulates only after mAttackStartTime; its active-time
// finish condition additionally requires a positive mWaitTime
// (GasHibaState.cpp:129-169). Retail disc wait is 0.0, so time alone never
// satisfies the finish condition.
inline bool gashibaEmit(GasHibaState state, float attackElapsed, float activeElapsed,
                        float attackStart, float activeTime, float waitTime) {
    for (float value : {attackElapsed, activeElapsed, attackStart, activeTime, waitTime}) {
        if (!std::isfinite(value)) throw std::runtime_error("non-finite GasHiba emission input");
    }
    if (state != GasHibaAttack) return false;
    if (attackElapsed < attackStart) return false;
    const bool finished = activeElapsed >= activeTime && waitTime > 0.0f;
    return !finished;
}

// Advance the ElecHiba Wait -> Sign -> Attack -> Wait chain
// (ElecHibaState.cpp:93-131,145-198,204-268). Returns (next_state, emits).
inline ElecStep elechibaAdvance(ElecHibaState state, float health, float elapsed,
                                float waitTime, float warningTime, float activeTime,
                                bool counterDone) {
    for (float value : {health, elapsed, waitTime, warningTime, activeTime}) {
        if (!std::isfinite(value)) throw std::runtime_error("non-finite ElecHiba input");
    }
    if (health <= 0.0f) return ElecStep{ElecHibaDead, false};
    if (state == ElecHibaWait) {
        return elapsed >= waitTime ? ElecStep{ElecHibaSign, false} : ElecStep{ElecHibaWait, false};
    }
    if (state == ElecHibaSign) {
        return elapsed >= warningTime ? ElecStep{ElecHibaAttack, true} : ElecStep{ElecHibaSign, false};
    }
    const bool finished = elapsed >= activeTime || counterDone;
    return finished ? ElecStep{ElecHibaWait, false} : ElecStep{ElecHibaAttack, true};
}

// Birth creates the two wire nodes at center -/+ separation / 2
// (ElecHibaMgr.cpp:110-131). Returns (negative node, positive node).
inline std::pair<float, float> elechibaNodePositions(float center, float separation) {
    if (!std::isfinite(center) || !std::isfinite(separation)) {
        throw std::runtime_error("non-finite ElecHiba geometry");
    }
    if (separation < 0.0f) throw std::runtime_error("negative ElecHiba separation");
    const float half = separation / 2.0f;
    return std::pair<float, float>(center - half, center + half);
}

// Normal damage routes to the team head and is rejected in full when the team
// is invulnerable (ElecHiba.cpp:139-157,752-776).
inline Sided elechibaTeamHeadDamage(bool isParent, bool invulnerable) {
    (void)isParent;
    return invulnerable ? SidedReject : SidedRouteToHead;
}

// setInitLivingThing owner for a story-outdoor GasHiba; the pipe can be
// temporarily not living until a nearby bridge or gate changes
// (GasHiba.cpp:204-272). RECONSTRUCTED: the exact gate is not reproduced.
inline LinkOwner gashibaLinkedOwner(bool bridgeLinked, bool gateLinked) {
    if (bridgeLinked && gateLinked) return LinkBridgeGate;
    if (bridgeLinked) return LinkBridge;
    if (gateLinked) return LinkGate;
    return LinkNone;
}

inline const char* linkOwnerName(LinkOwner owner) {
    switch (owner) {
    case LinkNone: return "none";
    case LinkBridge: return "bridge";
    case LinkGate: return "gate";
    case LinkBridgeGate: return "bridge+gate";
    }
    return "none";
}

// Versus attribute discharge mode (ElecHiba.cpp:264-329,307-324).
// RECONSTRUCTED: the versus counter/mode persistence is not pinned.
inline Stimulus elechibaVersusStimulus(const std::string& attribute) {
    if (attribute == "neutral") return StimDenki;
    if (attribute == "red") return StimFire;
    if (attribute == "blue") return StimBubble;
    throw std::runtime_error("unknown ElecHiba attribute");
}

// ---------------------------------------------------------------------------
// Strict sidecar config (P2_HIBA_NATIVE_1)
// ---------------------------------------------------------------------------
//
// P2_HIBA_NATIVE_1
// <hazardCount>                                                        # 1..8
//   <generatorId> <hazardId> <x> <y> <z> <yaw> <health> <waitOverride> <separation> <link> <warningOverride>
//                                                                      x hazardCount
//
// hazardId 20/21/22; waitOverride < 0 uses the disc wait; warningOverride < 0
// uses the disc ElecHiba warning; separation is non-negative and must be 0
// unless hazardId is ElecHiba; link 0..3 is the GasHiba bridge/gate owner and
// must be 0 unless hazardId is GasHiba; warningOverride >= 0 applies only to
// ElecHiba.
struct HazardRow {
    std::uint32_t generator = 0;
    int hazardId = 0;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float yaw = 0.0f;
    float health = 0.0f;
    float waitOverride = -1.0f;
    float separation = 0.0f;
    int link = 0;
    float warningOverride = -1.0f;
};

struct Config {
    std::vector<HazardRow> hazards;
};

inline bool finiteTransform(float x, float y, float z) {
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
        && std::fabs(x) <= 100000.0f && std::fabs(y) <= 100000.0f && std::fabs(z) <= 100000.0f;
}

inline bool readConfig(std::istream& in, Config& out) {
    Config config;
    std::string magic;
    if (!(in >> magic) || magic != "P2_HIBA_NATIVE_1") return false;
    int count = 0;
    if (!(in >> count) || count < 1 || count > 8) return false;
    std::set<std::uint32_t> ids;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        int hazardId = 0, link = 0;
        float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f, health = 0.0f, waitOverride = -1.0f, separation = 0.0f;
        float warningOverride = -1.0f;
        if (!(in >> generator >> hazardId >> x >> y >> z >> yaw >> health >> waitOverride >> separation >> link
              >> warningOverride)) {
            return false;
        }
        if (generator > 0xffffffffULL || !isFixedHazard(hazardId)) return false;
        if (!finiteTransform(x, y, z)) return false;
        if (!std::isfinite(yaw) || std::fabs(yaw) > 360.0f) return false;
        if (!std::isfinite(health) || health <= 0.0f || health > 100000.0f) return false;
        if (!std::isfinite(waitOverride) || std::fabs(waitOverride) > 1000.0f) return false;
        if (!std::isfinite(separation) || separation < 0.0f || separation > 1000.0f) return false;
        if (!std::isfinite(warningOverride) || std::fabs(warningOverride) > 1000.0f) return false;
        if (hazardId != ElecHibaId && separation != 0.0f) return false;
        if (hazardId != ElecHibaId && warningOverride >= 0.0f) return false;
        if (link < 0 || link > 3) return false;
        if (hazardId != GasHibaId && link != 0) return false;
        if (!ids.insert(std::uint32_t(generator)).second) return false;
        HazardRow row;
        row.generator       = std::uint32_t(generator);
        row.hazardId        = hazardId;
        row.x               = x;
        row.y               = y;
        row.z               = z;
        row.yaw             = yaw;
        row.health          = health;
        row.waitOverride    = waitOverride;
        row.separation      = separation;
        row.link            = link;
        row.warningOverride = warningOverride;
        config.hazards.push_back(row);
    }
    std::string trailing;
    if (in >> trailing) return false;
    out = config;
    return true;
}

} // namespace p2hiba
