#pragma once

// Isolated residual policy for Catfish (Water Dumple, EnemyID 26). The Catfish
// has no dedicated state file: it forwards onInit/birth to the shared
// KochappyBase FSM (KochappyBase.cpp, kochappyState.cpp) and adds only a
// two-slot mouth (Catfish.cpp:83-92). This translation unit depends on nothing
// but the standard language so the decision logic can be exercised without the
// engine. Source revision 632af93787b9c95b63f0c13be32b161375ce3a96.
//
// Source contract encoded here:
//   * two-slot mouth, radius 20, nearest-first, each creature ingested once
//     (Catfish::Obj::initMouthSlots, Catfish.cpp:83-92; EnemyFunc::eatPikmin,
//     enemyAction.cpp:1107-1140).
//   * StateAttack KEYEVENT_2 runs attackNavi then eatPikmin; KEYEVENT_3 runs
//     swallowPikmin (kochappyState.cpp:1400-1415). Catfish general fp22=50
//     attack hit radius, fp23 default 15 deg, fp24=10 damage.
//   * swallowPikmin kills each mouth sticker and, only for White Pikmin, runs
//     eatWhitePikminCallBack(poison) (enemyAction.cpp:1148-1175). Catfish proper
//     fp02 = 300 poison damage (KochappyBase.h:106).
//   * StateFlick KEYEVENT_2 flicks stick/nearby Pikmin and nearby Navi; KEYEVENT_3
//     resets the non-stone state (kochappyState.cpp:1764-1795). General fp17
//     default 300 knockback, fp18 default 0 damage, fp19 default 120 range.
namespace p2catfish {

// Catfish::Obj::initMouthSlots (Catfish.cpp:85-91).
constexpr int kMouthSlots    = 2;
constexpr float kMouthRadius = 20.0f;

// Catfish general parms (experimental/pikmin2_aquatic_assets.py DISC_PARMS).
constexpr float kAttackHitRadius = 50.0f;         // general fp22
constexpr float kAttackHitAngle  = 0.2617993878f; // general fp23 default 15 deg
constexpr float kAttackDamage    = 10.0f;         // general fp24
constexpr float kFlickRange      = 120.0f;        // general fp19 default
constexpr float kFlickKnockback  = 300.0f;        // general fp17 default
constexpr float kFlickDamage     = 0.0f;          // general fp18 default
constexpr float kPoisonDamage    = 300.0f;        // proper fp02 (KochappyBase.h:106)

// Banked animation key-event codes (pikmin2_aquatic_assets.py MGR_ROWS):
//   attack (17,2) bite, (75,3) swallow; flick (25,2) knockback, (47,3) restore.
constexpr int kEventBite          = 2;
constexpr int kEventSwallow       = 3;
constexpr int kEventFlick         = 2;
constexpr int kEventFlickRestore  = 3;

enum class AttackEvent { None, Bite, Swallow };
enum class FlickEvent { None, Knockback, RestoreNonStone };

inline AttackEvent attackEvent(int code)
{
    switch (code) {
    case kEventBite: return AttackEvent::Bite;
    case kEventSwallow: return AttackEvent::Swallow;
    default: return AttackEvent::None;
    }
}

inline FlickEvent flickEvent(int code)
{
    switch (code) {
    case kEventFlick: return FlickEvent::Knockback;
    case kEventFlickRestore: return FlickEvent::RestoreNonStone;
    default: return FlickEvent::None;
    }
}

// Source attackNavi gate: inside the attack hit radius and hit angle.
inline bool attackNaviHits(float distance, float absAngle)
{
    return distance < kAttackHitRadius && absAngle < kAttackHitAngle;
}

// Source flickNearbyPikmin / flickNearbyNavi gate.
inline bool inFlickRange(float distance)
{
    return distance < kFlickRange;
}

struct Candidate {
    float distance = 0.0f;
    bool eligible = false; // already filtered by the source attack sweep
    bool held = false;     // already held in a mouth slot
};

// Greedy nearest-first fill of the two mouth slots. `chosen` must hold at least
// kMouthSlots entries. Returns the number of new captures. `held` candidates are
// skipped and previously chosen candidates are never chosen twice, so a creature
// is ingested at most once.
inline int selectMouthCaptures(const Candidate* candidates, int count, int* chosen)
{
    int captured = 0;
    while (captured < kMouthSlots) {
        int best = -1;
        for (int i = 0; i < count; ++i) {
            if (!candidates[i].eligible || candidates[i].held) continue;
            bool already = false;
            for (int j = 0; j < captured; ++j) {
                if (chosen[j] == i) { already = true; break; }
            }
            if (already) continue;
            if (best < 0 || candidates[i].distance < candidates[best].distance) best = i;
        }
        if (best < 0) break;
        chosen[captured++] = best;
    }
    return captured;
}

struct SwallowResult {
    bool kill = false;
    bool poison = false;
    float poisonDamage = 0.0f;
};

// Source swallowPikmin: every swallowed Pikmin is killed; a swallowed White also
// poisons the eater with proper fp02. `alreadyConsumed` makes the effect
// exactly-once per creature.
inline SwallowResult swallowResult(bool isWhite, bool alreadyConsumed)
{
    SwallowResult result;
    if (alreadyConsumed) return result;
    result.kill = true;
    result.poison = isWhite;
    result.poisonDamage = isWhite ? kPoisonDamage : 0.0f;
    return result;
}

} // namespace p2catfish
