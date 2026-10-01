#pragma once
// Own-identity Chappy-family source policy (inst-chappy, #871).
//
// Source of truth (read-only decomp `native/pikmin2-research`):
//   include/Game/enemyInfo.h               EnemyID 2/33/35/43/53/67/76
//   include/Game/Entities/ChappyBase.h     adult FSM, anims, parms (2, 33, 43)
//   include/Game/Entities/KumaChappy.h     Spotty Bulbear FSM/parms (35, 67)
//   include/Game/Entities/KumaKochappy.h   Dwarf Bulbear FSM/parms (76)
//   include/Game/Entities/KingChappy.h     Emperor Bulblax FSM/parms (53)
//   src/plugProjectYamashitaU/chappyState.cpp  adult states
//   src/plugProjectNishimuraU/KumaChappyState.cpp, KumaKochappyState.cpp
//   src/plugProjectMorimuraU/kingChappyState.cpp
//
// Retail values below are the US GPVE01 rev 0 `<prefix>/enemyparm.txt`
// EnemyParmsBase block (fp00 life, fp06 speed, fp12 sight, fp20 range,
// fp21 angle, fp22 hit range, fp24 damage) plus the family proper block
// (ChappyParms fp01 foot / fp02 poison; Kuma fp01 white / fp11 gauge /
// fp12 respawn; King fp01..fp21; Leaf/KumaKo fp01 white). Audited off the
// disc for this lane; see the inst-chappy handoff for the extraction log.
// Vehicles preserve the proven proxy hosts (include/teki.h): P1 Spotty
// Bulborb (TEKI_Swallow 4) for the adults, Spotty Bulbear (TEKI_Swallob
// 32) for Kuma, Dwarf Bulborb (TEKI_Chappy 3) for Leaf, Dwarf Bulbear
// (TEKI_Chappb 31) for KumaKo.
#include <cmath>
#include <cstdint>
#include <istream>
#include <map>
#include <set>
#include <string>

namespace p2chappy {

struct SpeciesParams {
    unsigned source = 0;
    const char* enumName = "";
    const char* english = "";
    int host = -1;
    float health = 1.0f;       // general fp00
    float moveSpeed = 50.0f;   // general fp06
    float sight = 500.0f;      // general fp12
    float attackRange = 75.0f; // general fp20
    float attackAngle = 25.0f; // general fp21 (degrees)
    float attackHitRange = 80.0f; // general fp22
    float attackDamage = 10.0f;   // general fp24
    float poisonDamage = 300.0f;  // proper fp02 / fp01 white
    // Retail enemyparm.txt EnemyParmsBase block (GPVE01): territory fp09, home
    // range fp10, private distance fp11, view angle fp13, search angle fp15,
    // alert time fp29, vigilant life fp30. Sight fp12 doubles as the search
    // distance fp14 (500 for every adult row). The 2026-09-30 owner playtest
    // (Fiery Bulblax) showed the port's hard-coded 300 territory / 50 home
    // against source 400 / 15 made the adults turn for home mid-chase.
    float territory = 400.0f;
    float homeRadius = 15.0f;
    float privateRadius = 70.0f;
    float viewAngle = 90.0f;
    float searchAngle = 90.0f;
    float alertTime = 7.0f;
    float lifeBeforeAlert = 30.0f;
};

// Retail-audited family table in lane order. Hosts preserve the proxy era.
inline const SpeciesParams kSpecies[] = {
    {2, "Chappy", "Red Bulborb", 4, 750.0f, 100.0f, 500.0f, 75.0f, 25.0f, 80.0f, 10.0f, 750.0f, 400.0f, 15.0f, 70.0f, 90.0f, 90.0f, 7.0f, 30.0f},
    {33, "FireChappy", "Fiery Bulblax", 4, 1400.0f, 110.0f, 500.0f, 75.0f, 25.0f, 80.0f, 10.0f, 300.0f, 400.0f, 15.0f, 70.0f, 90.0f, 120.0f, 15.0f, 30.0f},
    {35, "KumaChappy", "Spotty Bulbear", 32, 1200.0f, 100.0f, 500.0f, 75.0f, 25.0f, 80.0f, 10.0f, 400.0f, 400.0f, 50.0f, 70.0f, 90.0f, 90.0f, 15.0f, 50.0f},
    {43, "YellowChappy", "Hairy Bulborb", 4, 650.0f, 90.0f, 500.0f, 75.0f, 25.0f, 80.0f, 10.0f, 650.0f, 400.0f, 15.0f, 70.0f, 90.0f, 90.0f, 7.0f, 30.0f},
    {53, "KingChappy", "Emperor Bulblax", 4, 1300.0f, 45.0f, 500.0f, 130.0f, 30.0f, 80.0f, 5.0f, 200.0f, 300.0f, 30.0f, 70.0f, 130.0f, 120.0f, 15.0f, 30.0f},
    {67, "LeafChappy", "Bulbmin", 3, 300.0f, 50.0f, 300.0f, 40.0f, 30.0f, 50.0f, 10.0f, 500.0f, 400.0f, 50.0f, 70.0f, 90.0f, 90.0f, 15.0f, 50.0f},
    {76, "KumaKochappy", "Dwarf Bulbear", 31, 500.0f, 60.0f, 150.0f, 35.0f, 25.0f, 38.0f, 10.0f, 500.0f, 500.0f, 80.0f, 70.0f, 180.0f, 180.0f, 15.0f, 30.0f},
};

inline const SpeciesParams* speciesForSource(unsigned source)
{
    for (const auto& row : kSpecies) {
        if (row.source == source) return &row;
    }
    return nullptr;
}

inline const SpeciesParams* speciesForEnum(const std::string& name)
{
    for (const auto& row : kSpecies) {
        if (name == row.enumName) return &row;
    }
    return nullptr;
}

// Source adult ChappyBase::StateID order
// (include/Game/Entities/ChappyBase.h:176): Turn(0), Dead(1), Flick(2),
// Walk(3), Attack(4), TurnToHome(5), GoHome(6), Sleep(7).
// Source KumaChappy states (KumaChappy.h): Dead(0), Rebirth(1), Lost(2),
// Attack(3), Flick(4), Turn(5), TurnPath(6), Walk(7), WalkPath(8).
// Source KumaKochappy states: Dead(0), Press(1), Wait(2), Attack(3),
// Flick(4), Walk(5), WalkPath(6).
// Source KingChappy states: Walk(0), Attack(1), Dead(2), Flick(3),
// WarCry(4), Damage(5), Turn(6), Eat(7), Hide(8), HideWait(9), Appear(10),
// Caution(11), Swallow(12).
enum AdultState {
    ADULT_TURN = 0,
    ADULT_DEAD = 1,
    ADULT_FLICK = 2,
    ADULT_WALK = 3,
    ADULT_ATTACK = 4,
    ADULT_TURN_TO_HOME = 5,
    ADULT_GO_HOME = 6,
    ADULT_SLEEP = 7,
    ADULT_COUNT = 8,
};

// Source `chappy/enemyanimmgr.txt` attack.bca events: type-2 frame 10
// (bite + eatPikmin), type-3 frame 33 (swallowPikmin), type-4 frame 40
// (transit). Shared by the Chappy-bank adults (2/33/43).
constexpr int AttackBiteFrame = 10;
constexpr int AttackSwallowFrame = 33;
constexpr int AttackEndFrame = 40;

// Dwarf Bulbear attack events (experimental/PIKMIN2_DWARF_VARIANTS.md:
// attack f8 eat, f88 swallow). Kuma/Leaf/King use their own banks; the
// host motion still selects the clip, so only the dwarf pair is pinned.
constexpr int DwarfAttackEatFrame = 8;
constexpr int DwarfAttackSwallowFrame = 88;

struct Params {
    float health = 750.0f;
};

inline bool parseConfig(std::istream& in, Params& out)
{
    std::string magic;
    if (!(in >> magic) || magic != "P2_CHAPPY_POLICY_1") {
        return false;
    }
    Params params;
    bool seen = false;
    std::string key;
    while (in >> key) {
        if (key != "health" || seen) {
            return false;
        }
        seen = true;
        float value = 0.0f;
        if (!(in >> value) || !std::isfinite(value) || value < 1.0f || value > 100000.0f) {
            return false;
        }
        params.health = value;
    }
    out = params;
    return true;
}

// Source-parameter health registry for the bound Chappy-family actors.
// Stores the retail fp00 per actor so damage/death thresholds use the P2
// value rather than the host P1 life.
class Health {
    std::map<const void*, float> actors;
    std::set<const void*> dead;

public:
    void reset()
    {
        actors.clear();
        dead.clear();
    }
    bool bind(const void* actor, float maxHealth)
    {
        if (!actor || !(maxHealth > 0.0f)) {
            return false;
        }
        return actors.emplace(actor, maxHealth).second;
    }
    void forget(const void* actor)
    {
        actors.erase(actor);
        dead.erase(actor);
    }
    bool contains(const void* actor) const
    {
        return actors.count(actor) != 0;
    }
    bool markDead(const void* actor)
    {
        return actors.count(actor) != 0 && dead.insert(actor).second;
    }
    bool isDead(const void* actor) const
    {
        return dead.count(actor) != 0;
    }
    float life(const void* actor, float fallback) const
    {
        auto it = actors.find(actor);
        return it == actors.end() ? fallback : it->second;
    }
};

// ---- P1 AI-grid culling (#994) ----------------------------------------------
// Creature::update (creature.cpp:678) skips a whole teki update, including
// moveNew, while no captain or Pikmin is in the actor's AI-grid neighbourhood. P2
// enemies are never culled out of motion (culling only skips animation), so an
// awake Bulborb that outpaces the captain (across a pond, say) must keep
// integrating its commanded walk. Owner playtest: the Fiery froze mid-chase with
// velocity set and the FSM flipping Walk/TurnToHome/GoHome in place. The pin is
// CF_AIAlwaysActive (Creature::setInsideView). A sleeping actor is not pinned:
// it only wakes on a touch (ChappyBase::isWakeup), which lights its own grid cell.
// The Emperor keeps its own burrow/appear path and is never pinned here.
enum PinFamily { PinAdult = 0, PinKuma = 1, PinKumako = 2, PinKing = 3 };
inline bool keepUpdatingOffGrid(int family, bool alive, bool asleep)
{
    if (family == PinKing) return false;
    return alive && !asleep;
}

} // namespace p2chappy
