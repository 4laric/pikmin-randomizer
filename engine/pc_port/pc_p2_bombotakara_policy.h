#pragma once
// Pikmin 2 lane-22 BombOtakara payload policy (#170, child #447).
//
// Pure, engine-free mirror of the BombOtakara section of
// experimental/pikmin2_elemental_behavior.py (root branch
// opencode/p2-lane22-elemental):
//   * shared OtakaraBase 14-state FSM, Bomb-carry states
//     OtakaraBase.h:22-39 / OtakaraBaseState.cpp:14-34,744-907
//   * initBombOtakara requests the separate EnemyID_Bomb payload (36),
//     captures it on the `otakara` joint and sets mCarrier
//     OtakaraBase.cpp:649-677
//   * doFinishWaitingBirthTypeDrop reinitializes the payload
//     OtakaraBase.cpp:321-327
//   * the bomb-carry states kill the carrier if the payload pointer
//     disappears OtakaraBaseState.cpp:761-763,816-819,880-882
//   * stimulateBomb disables culling and calls the payload Bomb's forceBomb
//     after 1.5 s OtakaraBase.cpp:699-707
//   * BombOtakara.cpp:42-87 delegates damage/earthquake to the payload Bomb
//
// The blast/explosion primitive is owned by the projectiles lane (#169). There
// is no shared Bomb/blast interface at this base, so the runtime never invents
// one: it drives the policy and reports the application as BLOCKED.
#include "pc_p2_dweevil_policy.h"
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2bombotakara {

using p2dweevil::State;

// Bomb carry states are the shared OtakaraBase states 11..13.
inline bool isBombCarryState(int state) {
    return state == p2dweevil::BombWait || state == p2dweevil::BombMove || state == p2dweevil::BombTurn;
}

// stimulateBomb -> forceBomb delay (OtakaraBase.cpp:699-707).
inline constexpr float kForceDelaySeconds = 1.5f;

// Payload decision mirrored from bomb_otakara_payload in the Python model.
enum PayloadAction {
    KillCarrier = 0,
    ForceBomb,
    DamagePayload,
    ChasePayload,
};

inline const char* payloadActionName(PayloadAction action) {
    switch (action) {
    case KillCarrier: return "kill_carrier";
    case ForceBomb: return "force_bomb";
    case DamagePayload: return "damage_payload";
    case ChasePayload: return "chase_payload";
    }
    return "chase_payload";
}

inline PayloadAction payloadAction(bool payloadPresent, bool bittered, bool earthquake,
                                   float chaseElapsed) {
    if (!std::isfinite(chaseElapsed)) throw std::runtime_error("non-finite chase elapsed");
    if (!payloadPresent) return KillCarrier;
    if (earthquake) return ForceBomb;
    if (bittered) return DamagePayload;
    if (chaseElapsed >= kForceDelaySeconds) return ForceBomb;
    return ChasePayload;
}

// Detonation triggers. Contact/press and death all delegate to the payload.
enum Trigger {
    TriggerContact = 0,
    TriggerPress,
    TriggerDeath,
    TriggerEarthquake,
};

inline const char* triggerName(Trigger trigger) {
    switch (trigger) {
    case TriggerContact: return "contact";
    case TriggerPress: return "press";
    case TriggerDeath: return "death";
    case TriggerEarthquake: return "earthquake";
    }
    return "contact";
}

// Exactly-once detonation: a death/contact/press path forces the payload once;
// a second trigger for the same payload does nothing, so the blast cannot
// double-fire.
struct DetonationResult {
    bool detonated;
    bool alreadyDetonated;
};

inline DetonationResult detonate(bool payloadPresent, bool alreadyDetonated) {
    if (!payloadPresent || alreadyDetonated) return DetonationResult{false, alreadyDetonated};
    return DetonationResult{true, false};
}

// ---------------------------------------------------------------------------
// Strict sidecar config (P2_BOMBOTAKARA_NATIVE_1)
// ---------------------------------------------------------------------------
//
// P2_BOMBOTAKARA_NATIVE_1
// <unitCount>                                                            # 1..4
//   <generatorId> <x> <y> <z> <yaw> <health> <payloadId> <bx> <by> <bz>
//                                                                        x unitCount
//
// The carrier is born already holding the payload (initBombOtakara captures
// the Bomb on the `otakara` joint); the payload coordinates are the staged
// stub used for the bounded fixture and are labeled as an injection.
struct Unit {
    std::uint32_t generator = 0;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float yaw = 0.0f;
    float health = 0.0f;
    std::uint32_t payloadId = 0;
    float bx = 0.0f;
    float by = 0.0f;
    float bz = 0.0f;
};

struct Config {
    std::vector<Unit> units;
};

inline bool finiteTransform(float x, float y, float z) {
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
        && std::fabs(x) <= 100000.0f && std::fabs(y) <= 100000.0f && std::fabs(z) <= 100000.0f;
}

inline bool readConfig(std::istream& in, Config& out) {
    Config config;
    std::string magic;
    if (!(in >> magic) || magic != "P2_BOMBOTAKARA_NATIVE_1") return false;
    int count = 0;
    if (!(in >> count) || count < 1 || count > 4) return false;
    std::set<std::uint32_t> ids;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0, payloadId = 0;
        float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f, health = 0.0f;
        float bx = 0.0f, by = 0.0f, bz = 0.0f;
        if (!(in >> generator >> x >> y >> z >> yaw >> health >> payloadId >> bx >> by >> bz)) return false;
        if (generator > 0xffffffffULL || payloadId > 0xffffffffULL) return false;
        if (!finiteTransform(x, y, z) || !finiteTransform(bx, by, bz)) return false;
        if (!std::isfinite(yaw) || std::fabs(yaw) > 360.0f) return false;
        if (!std::isfinite(health) || health <= 0.0f || health > 100000.0f) return false;
        if (!ids.insert(std::uint32_t(generator)).second) return false;
        if (!ids.insert(std::uint32_t(payloadId)).second) return false;
        Unit unit;
        unit.generator = std::uint32_t(generator);
        unit.x = x;
        unit.y = y;
        unit.z = z;
        unit.yaw = yaw;
        unit.health = health;
        unit.payloadId = std::uint32_t(payloadId);
        unit.bx = bx;
        unit.by = by;
        unit.bz = bz;
        config.units.push_back(unit);
    }
    std::string trailing;
    if (in >> trailing) return false;
    out = config;
    return true;
}

} // namespace p2bombotakara

// ---------------------------------------------------------------------------
// Muse l61 (#501) natural-observation helpers (additive, engine-free).
// ---------------------------------------------------------------------------
//
// The lane-22 sidecar stages its Bomb stub through p2-bombotakara-native.txt
// plus p2-bombotakara-inject.txt trigger writes; both files are labeled
// injections and can never close a natural gate. The natural BombOtakara93
// closure instead requires, in one run:
//
//   * a real family generator identity chain: P2_OTAKARA_BIND with
//     source_id=93 on a live Teki actor (the integrated lane-22 Otakara
//     runner already binds BombOtakara for identity and reports
//     attack=payload_delegated);
//   * an observed bomb attachment on the source `otakara` joint:
//     P2_BOMBOTAKARA_ATTACH generator=<carrier> payload=<bomb> joint=otakara;
//   * an observed blast routed through the shared lane-20 primitive to live
//     receivers: P2_BOMBOTAKARA_BLAST ... shared_primitive=1 with
//     receivers>=1, hits>=1 and pikmin_hits>=1, followed by real InteractBomb
//     delivery (P2_BOMBOTAKARA_BOMB_HIT accepted=1).
//
// These helpers classify log markers only; they stage nothing, inject no
// health/state/transport, and change no elemental59-62 default.
namespace p2bombotakara_natural {

inline constexpr unsigned kBombOtakaraSourceId = 93;

// Injected-marker substrings: any log containing one of these is reported as
// injected diagnostic evidence, never as a natural PASS.
inline bool isInjectedMarker(const std::string& line) {
    static const char* kMarkers[] = {
        "P2_BOMBOTAKARA_INJECT",
        "p2-bombotakara-inject",
        "injection=1",
        "P2_BOMBOTAKARA_FIXTURE_GUARD_PIKMIN",
        "P2_BOMBOTAKARA_DEATH_INJECT",
        "P2_OTAKARA_DEATH_INJECT",
    };
    for (const char* marker : kMarkers) {
        if (line.find(marker) != std::string::npos) return true;
    }
    return false;
}

// Real family generator identity: nonzero 32-bit generator on the Otakara
// bind line with source_id=93. A globally admitted generated slot is never
// authorized here; the caller supplies the concrete family generator.
inline bool isNaturalIdentityBind(unsigned generator, int sourceId) {
    return generator != 0 && sourceId == int(kBombOtakaraSourceId);
}

// Natural blast routing: the shared primitive ran against live receivers and
// delivered at least one hit, including at least one Pikmin hit via the real
// InteractBomb receiver path. Zero-receiver or zero-hit blasts prove routing
// code ran, not natural combat.
inline bool isNaturalBlastRouting(int receivers, int hits, int pikminHits, bool sharedPrimitive) {
    return sharedPrimitive && receivers >= 1 && hits >= 1 && pikminHits >= 1;
}

} // namespace p2bombotakara_natural
