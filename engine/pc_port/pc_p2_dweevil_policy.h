#pragma once
// Pikmin 2 lane-22 dweevil family policy (#170, child #447).
//
// Pure, engine-free mirror of the already-delivered Python behavior model
// `experimental/pikmin2_elemental_behavior.py` (root branch
// opencode/p2-lane22-elemental @ 7dc1a24) for the five OtakaraBase dweevils
// FireOtakara (59), WaterOtakara (60), GasOtakara (61), ElecOtakara (62) and
// BombOtakara (93), plus the fixed hazards Hiba (20), GasHiba (21) and
// ElecHiba (22) and the blowhog element mapping kept for parity.
//
// Source anchors (decompilation revision
// 632af93787b9c95b63f0c13be32b161375ce3a96, per
// docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md):
//   * shared 14-state FSM              OtakaraBase.h:22-39 / OtakaraBaseState.cpp:14-34
//   * theft search                     OtakaraBase.cpp:395-417
//   * capture on the `otakara` joint   OtakaraBase.cpp:472-524
//   * damage routing                   OtakaraBase.cpp:550-574
//   * fallTreasure exactly-once drop   OtakaraBase.cpp:530-544 / 242-304
//   * item-drop event type 2           OtakaraBaseState.cpp:680-727
//   * per-species stimulus             Fire/Water/Gas/ElecOtakara.cpp:41-61
//   * receiver colour immunity         src/plugProjectKandoU/interactPiki.cpp:334,445,503,531
//
// This header has no actor, pellet, map, damage or effect dependency: it is
// the machine-checkable contract the native sidecar driver and the standalone
// strict policy test consume. Elemental immunity is policy-only here; no
// generic damage/physics path is changed by this lane.
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2dweevil {

// ---------------------------------------------------------------------------
// Identity and shared state machine
// ---------------------------------------------------------------------------

// Source EnemyID values (include/Game/enemyInfo.h:79-84,118-121,152).
enum SpeciesId {
    HibaId      = 20,
    GasHibaId   = 21,
    ElecHibaId  = 22,
    TankId      = 24,
    WtankId     = 25,
    FireId      = 59,
    WaterId     = 60,
    GasId       = 61,
    ElecId      = 62,
    BombId      = 93,
};

// Shared OtakaraBase StateID (OtakaraBase.h:22-39); the five dweevils register
// all fourteen in OtakaraBaseState.cpp:14-34.
enum State {
    Dead       = 0,
    Flick      = 1,
    Wait       = 2,
    Move       = 3,
    Turn       = 4,
    Take       = 5,
    ItemWait   = 6,
    ItemMove   = 7,
    ItemTurn   = 8,
    ItemFlick  = 9,
    ItemDrop   = 10,
    BombWait   = 11,
    BombMove   = 12,
    BombTurn   = 13,
};

// ---------------------------------------------------------------------------
// Emitted stimulus and receiver immunity (audit lines 41-43)
// ---------------------------------------------------------------------------

enum Stimulus { StimNone = 0, StimFire, StimBubble, StimGas, StimDenki };

// Pikmin colour for the receiver table; Bulbmin is excluded by every receiver.
enum Colour { Red = 0, Yellow, Blue, Purple, White, Bulbmin, ColourCount };

enum DropReason { DropDeath = 0, DropStone, DropEarthquake, DropInterruption };
enum DamageRoute { RouteDweevil = 0, RouteTreasure };
enum HazardAction { HazardWait = 0, HazardAttack, HazardDead };

struct DropResult {
    bool dropped;
    bool carryingAfter;
};

inline bool isDweevilSpecies(int species) {
    return species == FireId || species == WaterId || species == GasId
        || species == ElecId || species == BombId;
}

inline bool isFixedHazard(int identity) {
    return identity == HibaId || identity == GasHibaId || identity == ElecHibaId;
}

inline const char* speciesName(int species) {
    switch (species) {
    case FireId: return "FireOtakara";
    case WaterId: return "WaterOtakara";
    case GasId: return "GasOtakara";
    case ElecId: return "ElecOtakara";
    case BombId: return "BombOtakara";
    default: return "Unknown";
    }
}

inline const char* stimulusName(Stimulus stimulus) {
    switch (stimulus) {
    case StimFire: return "InteractFire";
    case StimBubble: return "InteractBubble";
    case StimGas: return "InteractGas";
    case StimDenki: return "InteractDenki";
    case StimNone: return "None";
    }
    return "None";
}

// Per-species interactCreature stimulus. BombOtakara emits none: its carried
// Bomb owns the blast (audit lines 20,30,36).
inline Stimulus stimulusFor(int species) {
    switch (species) {
    case FireId: return StimFire;
    case WaterId: return StimBubble;
    case GasId: return StimGas;
    case ElecId: return StimDenki;
    case BombId: return StimNone;
    default: throw std::runtime_error("not a dweevil species");
    }
}

// Blowhog element mapping (Ftank.cpp:121-125, Wtank.cpp:119-123) kept for the
// lane-22 family parity; the blowhog runtime is out of this slice's scope.
inline Stimulus blowhogStimulus(int species) {
    switch (species) {
    case TankId: return StimFire;
    case WtankId: return StimBubble;
    default: throw std::runtime_error("not a blowhog species");
    }
}

// The receiver, not the emitter, decides immunity. InteractGas additionally
// rejects an already gas-invincible target (interactPiki.cpp:531).
inline bool pikminImmune(Stimulus stimulus, Colour colour, bool gasInvincible = false) {
    if (colour == Bulbmin) return true;
    switch (stimulus) {
    case StimFire: return colour == Red;
    case StimBubble: return colour == Blue;
    case StimGas: return colour == White || gasInvincible;
    case StimDenki: return colour == Yellow;
    case StimNone: return false;
    }
    return false;
}

// Generic invincibility rejects before any elemental check; then colour
// immunity decides. Returns 'accept' (true) or 'reject' (false).
inline bool receiverAccepts(Stimulus stimulus, Colour colour, bool invincible = false,
                            bool gasInvincible = false) {
    if (invincible) return false;
    return !pikminImmune(stimulus, colour, gasInvincible);
}

// ---------------------------------------------------------------------------
// Fixed hazard activation (Hiba/GasHiba Wait -> Attack)
// ---------------------------------------------------------------------------

// Retail disc wait times (US GPVE01 rev 0, <hazard>/enemyparm.txt): Hiba 3.0,
// GasHiba 0.0. Header defaults (2.5/2.5) stay distinct in the Python model.
inline float hazardDiscWait(int hazard) {
    switch (hazard) {
    case HibaId: return 3.0f;
    case GasHibaId: return 0.0f;
    case ElecHibaId: return 1.5f;
    default: throw std::runtime_error("not a fixed hazard");
    }
}

// Wait -> Attack once the wait timer elapses; zero health is Dead. Mirrors
// hazard_activate in the Python model (Hiba.cpp:31-50, GasHiba.cpp:33-53).
inline HazardAction hazardActivate(int hazard, float health, float waitElapsed,
                                   float waitTime = -1.0f) {
    if (!isFixedHazard(hazard)) throw std::runtime_error("not a fixed hazard");
    if (!std::isfinite(health) || !std::isfinite(waitElapsed)) {
        throw std::runtime_error("non-finite hazard input");
    }
    if (waitTime < 0.0f) waitTime = hazardDiscWait(hazard);
    if (!std::isfinite(waitTime)) throw std::runtime_error("non-finite hazard wait");
    if (health <= 0.0f) return HazardDead;
    return waitElapsed >= waitTime ? HazardAttack : HazardWait;
}

// ---------------------------------------------------------------------------
// Treasure theft, capture, damage routing and exactly-once drop
// ---------------------------------------------------------------------------

// Only alive, pickable, uncaptured pellets inside the home territory are
// eligible, and a carrying dweevil cannot take a second (OtakaraBase.cpp:395-417).
inline bool theftDecision(bool alive, bool pickable, bool captured,
                          bool withinTerritory, bool carrying) {
    return alive && pickable && !captured && withinTerritory && !carrying;
}

// Health the captured treasure is given (mOtakaraLife). Non-positive rejected.
inline float captureHealth(float otakaraLife) {
    if (!std::isfinite(otakaraLife) || otakaraLife <= 0.0f) {
        throw std::runtime_error("positive treasure health required");
    }
    return otakaraLife;
}

// Damage while carrying decrements treasure health; otherwise the dweevil
// itself is damaged (OtakaraBase.cpp:550-574).
inline DamageRoute damageRoute(bool carrying) {
    return carrying ? RouteTreasure : RouteDweevil;
}

// Exactly-once forced drop. A death/stone/earthquake/interruption path calls
// fallTreasure once (OtakaraBase.cpp:530-544); a second drop for the same
// capture does nothing, so recovery cannot be duplicated.
inline DropResult drop(bool carrying, bool alreadyDropped, DropReason reason) {
    (void)reason;
    if (!carrying || alreadyDropped) return DropResult{false, false};
    return DropResult{true, false};
}

// ---------------------------------------------------------------------------
// Strict sidecar config (P2_DWEEVIL_NATIVE_1)
// ---------------------------------------------------------------------------
//
// P2_DWEEVIL_NATIVE_1
// <unitCount>
//   <generatorId> <speciesId> <x> <y> <z> <yaw> <otakaraLife>   x unitCount
// <treasureCount>
//   <treasureId> <x> <y> <z> <alive> <pickable> <captured>      x treasureCount
//
// Absent sidecar means inert. A present but malformed sidecar fails closed
// (readConfig returns false and the caller aborts).
struct Unit {
    std::uint32_t generator = 0;
    int species             = 0;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float yaw = 0.0f;
    float otakaraLife = 0.0f;
};

struct Treasure {
    std::uint32_t id = 0;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    bool alive = false;
    bool pickable = false;
    bool captured = false;
};

struct Config {
    std::vector<Unit> units;
    std::vector<Treasure> treasures;
};

inline bool finiteTransform(float x, float y, float z) {
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
        && std::fabs(x) <= 100000.0f && std::fabs(y) <= 100000.0f && std::fabs(z) <= 100000.0f;
}

inline bool readBoolToken(int value) { return value == 0 || value == 1; }

inline bool readConfig(std::istream& in, Config& out) {
    Config config;
    std::string magic;
    if (!(in >> magic) || magic != "P2_DWEEVIL_NATIVE_1") return false;
    int unitCount = 0;
    if (!(in >> unitCount) || unitCount < 1 || unitCount > 8) return false;
    std::set<std::uint32_t> ids;
    for (int i = 0; i < unitCount; ++i) {
        unsigned long long id = 0;
        int species = 0;
        float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f, life = 0.0f;
        if (!(in >> id >> species >> x >> y >> z >> yaw >> life)) return false;
        if (id > 0xffffffffULL || !isDweevilSpecies(species)) return false;
        if (!finiteTransform(x, y, z)) return false;
        if (!std::isfinite(yaw) || std::fabs(yaw) > 360.0f) return false;
        if (!std::isfinite(life) || life <= 0.0f || life > 100000.0f) return false;
        if (!ids.insert(std::uint32_t(id)).second) return false;
        Unit unit;
        unit.generator    = std::uint32_t(id);
        unit.species      = species;
        unit.x            = x;
        unit.y            = y;
        unit.z            = z;
        unit.yaw          = yaw;
        unit.otakaraLife  = life;
        config.units.push_back(unit);
    }
    int treasureCount = 0;
    if (!(in >> treasureCount) || treasureCount < 0 || treasureCount > 8) return false;
    for (int i = 0; i < treasureCount; ++i) {
        unsigned long long id = 0;
        float x = 0.0f, y = 0.0f, z = 0.0f;
        int alive = 0, pickable = 0, captured = 0;
        if (!(in >> id >> x >> y >> z >> alive >> pickable >> captured)) return false;
        if (id > 0xffffffffULL || !ids.insert(std::uint32_t(id)).second) return false;
        if (!finiteTransform(x, y, z)) return false;
        if (!readBoolToken(alive) || !readBoolToken(pickable) || !readBoolToken(captured)) return false;
        Treasure treasure;
        treasure.id       = std::uint32_t(id);
        treasure.x        = x;
        treasure.y        = y;
        treasure.z        = z;
        treasure.alive    = alive != 0;
        treasure.pickable = pickable != 0;
        treasure.captured = captured != 0;
        config.treasures.push_back(treasure);
    }
    std::string trailing;
    if (in >> trailing) return false;
    out = config;
    return true;
}

} // namespace p2dweevil
