#pragma once
#include <cmath>

// Engine-free Uji family policy: Female Sheargrub (UjiA, 12), Male Sheargrub
// (UjiB, 13), Shearwig (Tobi, 14). Source: Ujia/Ujib/TobiState.cpp +
// Ujia.h/Ujib.h/Tobi.h StateID enums in native/pikmin2-research
// (plugProjectNishimuraU). Retail general parms from EnemyParmsBase
// (life 100, move 80, territory 200, sight 200); UjiA proper fp01 bridge
// damage 25 (Ujia.h:118). Species enemyparm.txt overrides are preserved on
// disc (experimental/pikmin2_uji_assets.py) but not re-parsed here; the
// per-species defaults below are the retail EnemyParmsBase defaults with the
// documented species tweaks (male/flying toughness, fly speed), all marked
// as port values where they differ from a measured retail number.
//
// Attack semantics (#886 defect 5, checked against the decomp):
//   * UjiA (12) has no creature attack. Its only attack state, Attack1, calls
//     breakTargetBridge at KEYEVENT_2 (UjiaState.cpp:510-538); StateMove just
//     follows the target (UjiaState.cpp:250-284). mBridgeDamage is the
//     InteractBreakBridge power (Ujia.cpp:417, Ujib.cpp:439, Tobi.cpp:546),
//     never creature damage.
//   * UjiB (13) / Tobi (14) enter Attack2 from Move when a Pikmin or captain
//     is attackable (fp20 range, fp21 angle; UjibState.cpp:246-266,
//     TobiState.cpp:247-272). Attack2 KEYEVENT_4 (frame 14) does ONE
//     attackNavi(fp22, fp23, fp24) plus eatPikmin through the kamujnt slot
//     (UjibState.cpp:933-936, TobiState.cpp:683-686); END goes to Eat only
//     with stuck Pikmin (mStuckPikminCount), else Move. Eat KEYEVENT_2
//     (frame 53) swallowPikmin(proper poison) (UjibState.cpp:996-997,
//     TobiState.cpp:746-747). Attack1 is the bridge gnaw for them too and is
//     unreachable on P1 maps (no P2 ItemBridge target is bound).
//   * Tobi Fly ends only at its clip end (TobiState.cpp:561-580).
// Event frames are the retail enemyanimmgr.txt rows recorded by
// experimental/pikmin2_uji_assets.py EXPECTED_EVENTS (attack2 14:4, eat 53:2).
namespace p2uji_policy {

enum Kind { UJIA = 0, UJIB = 1, TOBI = 2 };

enum State {
    UJI_DEAD = 0,
    UJI_STAY = 2,
    UJI_APPEAR = 3,
    UJI_DIVE = 4,
    UJI_MOVE = 5,
    UJI_GOHOME = 9,
    UJI_ATTACK1 = 10,
    UJI_ATTACK2 = 11,
    UJI_EAT = 12,
    UJI_FLY = 13,
};

struct Parms {
    float life = 100.0f;
    float moveSpeed = 80.0f;
    float sight = 200.0f;
    float territory = 200.0f;
    float homeRadius = 100.0f;
    float appearTime = 1.0f;   // port value (source plays the appear motion)
    float attackTime = 1.2f;   // port value (source ends on motion end)
    float attackRange = 70.0f;  // general fp20 max attack range (header default)
    float attackAngle = 15.0f;  // general fp21 max attack angle, degrees (header default)
    float attackRadius = 70.0f; // general fp22 attackNavi radius (header default)
    float hitAngle = 15.0f;     // general fp23 attackNavi angle, degrees (header default)
    float attackDamage = 10.0f; // general fp24 captain damage (header default)
    float poisonDamage = 300.0f; // UjiB proper fp01 / Tobi proper fp11 (header default)
    // InteractBreakBridge power only (no bridge target on P1 maps; unused):
    // UjiA proper fp01 25, UjiB proper fp02 50, Tobi proper fp12 75.
    float bridgeDamage = 25.0f;
    int strikeFrame = 14;  // attack2 KEYEVENT_4
    int swallowFrame = 53; // eat KEYEVENT_2
    float flyTime = 4.0f;       // port value (Tobi airborne window)
    float eatTime = 2.0f;       // port value (UjiB/Tobi Eat carry window)
};

inline Parms parmsFor(Kind kind) {
    Parms p;
    if (kind == UJIB) {
        p.life = 120.0f; // port value: male tougher than female
        p.bridgeDamage = 50.0f;
    } else if (kind == TOBI) {
        p.life = 150.0f;      // port value: flying shearwig tougher
        p.moveSpeed = 120.0f;  // port value: Tobi fly speed
        p.bridgeDamage = 75.0f;
    }
    return p;
}

// Only UjiB and Tobi attack creatures (see the header note).
inline bool attacksCreatures(Kind kind) {
    return kind != UJIA;
}

// Source EnemyBase::isTargetAttackable / EnemyFunc::attackNavi geometry: 3D
// distance strictly inside `range` and |angle to target - heading| within
// `angleDeg` (trig.h isAngleWithin <=; attackNavi uses a strict <, `strict`).
inline bool inCone(float dx, float dy, float dz, float heading, float range, float angleDeg, bool strict = false) {
    if (!(dx * dx + dy * dy + dz * dz < range * range)) return false;
    float a = std::atan2(dx, dz) - heading;
    while (a > 3.14159265f) a -= 6.28318531f;
    while (a < -3.14159265f) a += 6.28318531f;
    const float lim = angleDeg * 3.14159265f / 180.0f;
    return strict ? std::fabs(a) < lim : std::fabs(a) <= lim;
}

inline int sourceIdFor(Kind kind) {
    return kind == UJIA ? 12 : kind == UJIB ? 13 : 14;
}

inline int hostTypeFor(Kind kind) {
    return kind == UJIA ? 18 : kind == UJIB ? 19 : 20; // TEKI_KabekuiA/B/C
}

struct In {
    float health = 100.0f;
    bool targetInSight = false;
    bool targetAttackable = false; // a Pikmin/captain inside the fp20/fp21 cone
    bool stuckPikmin = false;      // mStuckPikminCount > 0 at Attack2 END
    bool farFromHome = false;
};

struct Out {
    bool motionChanged = false;
    bool downEffect = false;
    bool strike = false;  // Attack2 KEYEVENT_4: attackNavi + eatPikmin, once per Attack2
    bool swallow = false; // Eat KEYEVENT_2: swallowPikmin, once per Eat
};

// Header-only FSM: Stay (buried) -> Appear -> Move -> Attack1 (-> Attack2 ->
// Eat for UjiB; Fly loop for Tobi) -> Move; Dive/GoHome when far from home;
// Dead on health 0. Transcribes UjiaState.cpp / UjibState.cpp (+Attack2/Eat)
// / TobiState.cpp (+Fly).
class Fsm {
  public:
    State state = UJI_STAY;
    float stateTime = 0.0f;
    bool strikeFired = false;
    bool swallowFired = false;

    void reset() {
        state = UJI_STAY;
        stateTime = 0.0f;
        strikeFired = false;
        swallowFired = false;
    }

    void enter(State s) {
        state = s;
        stateTime = 0.0f;
        strikeFired = false;
        swallowFired = false;
    }

    // Returns true when the motion clip changes (caller switches bank clip).
    bool tick(const In& in, const Parms& parms, Kind kind, Out& out) {
        out.motionChanged = false;
        out.downEffect = false;
        out.strike = false;
        out.swallow = false;
        if (in.health <= 0.0f && state != UJI_DEAD) {
            enter(UJI_DEAD);
            out.motionChanged = true;
            out.downEffect = true;
            return true;
        }
        if (state == UJI_DEAD) return false;
        stateTime += 1.0f / 30.0f; // fixed-step tick (30 fps retail clock)
        switch (state) {
        case UJI_STAY:
            if (in.targetInSight) {
                state = UJI_APPEAR;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_APPEAR:
            if (stateTime >= parms.appearTime) {
                state = UJI_MOVE;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_MOVE:
            if (in.farFromHome) {
                state = UJI_GOHOME;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            if (in.targetAttackable && attacksCreatures(kind)) {
                enter(UJI_ATTACK2);
                out.motionChanged = true;
                return true;
            }
            if (kind == TOBI && stateTime >= parms.flyTime) {
                state = UJI_FLY;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_GOHOME:
            // Source StateGoHome attacks an attackable target on the way
            // (UjibState.cpp:813-815, TobiState.cpp:503-505).
            if (in.targetAttackable && attacksCreatures(kind)) {
                enter(UJI_ATTACK2);
                out.motionChanged = true;
                return true;
            }
            if (!in.farFromHome) {
                state = UJI_MOVE;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            if (stateTime >= parms.flyTime) {
                state = UJI_DIVE;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_DIVE:
            if (stateTime >= parms.appearTime) {
                state = UJI_STAY;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_ATTACK1:
            // Bridge gnaw only (no bridge target on P1): no creature effect.
            if (stateTime >= parms.attackTime) {
                enter(UJI_MOVE);
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_ATTACK2:
            if (!strikeFired && stateTime * 30.0f >= float(parms.strikeFrame) - 1e-3f) {
                strikeFired = true;
                out.strike = true;
            }
            if (stateTime >= parms.attackTime) {
                enter(in.stuckPikmin ? UJI_EAT : UJI_MOVE);
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_EAT:
            if (!swallowFired && stateTime * 30.0f >= float(parms.swallowFrame) - 1e-3f) {
                swallowFired = true;
                out.swallow = true;
            }
            if (stateTime >= parms.eatTime) {
                state = UJI_MOVE;
                stateTime = 0.0f;
                out.motionChanged = true;
                return true;
            }
            return false;
        case UJI_FLY:
            // Source StateFly ends only at its clip end (TobiState.cpp:578-580).
            if (stateTime >= parms.flyTime) {
                enter(UJI_MOVE);
                out.motionChanged = true;
                return true;
            }
            return false;
        default:
            return false;
        }
    }

    static const char* clipFor(State s, Kind kind) {
        switch (s) {
        case UJI_DEAD: return "dead";
        case UJI_STAY: return "dive";
        case UJI_APPEAR: return "appear";
        case UJI_DIVE: return "dive";
        case UJI_MOVE: return "move";
        case UJI_GOHOME: return "move";
        case UJI_ATTACK1: return "attack1";
        case UJI_ATTACK2: return "attack2";
        case UJI_EAT: return "eat";
        case UJI_FLY: return kind == TOBI ? "fly" : "move";
        default: return "move";
        }
    }
};

} // namespace p2uji_policy
